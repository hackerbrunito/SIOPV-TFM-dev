"""Async-to-sync streaming bridge for LangGraph pipeline events.

Converts LangGraph's ``astream_events`` async iterator into a synchronous
generator that Streamlit can consume during a single script execution.
Uses a dedicated thread with its own asyncio event loop and a thread-safe
queue to pass structured ``PipelineEvent`` objects back to the caller.

Architecture
------------
::

    [Streamlit main thread]          [Background thread]
           │                               │
           │  queue.get() ◄────────────── queue.put(event)
           │      │                        │
           ▼      ▼                        ▼
      yield event                   astream_events(v2)

This pattern is the established async-to-sync bridge recommended for
Streamlit + LangGraph integration (March 2026).
"""

from __future__ import annotations

import asyncio
import queue
import threading
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from siopv.application.orchestration.graph import (
    PipelineGraphBuilder,
    PipelinePorts,
    _validate_path,
)
from siopv.application.orchestration.state import PipelineState, create_initial_state
from siopv.domain.constants import (
    PIPELINE_NODE_SEQUENCE,
    PIPELINE_STREAM_QUEUE_POLL_SECONDS,
)

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Event data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    """Structured event emitted during pipeline streaming.

    Attributes:
        event_type: Category of the event.
        node_name: Pipeline node that produced this event, or ``None`` for
            pipeline-level events.
        timestamp: UTC timestamp when the event was captured.
        data: Arbitrary payload — node input on start, state update on end.
        step: LangGraph step counter (``langgraph_step`` metadata).
    """

    event_type: Literal[
        "node_start",
        "node_end",
        "node_error",
        "pipeline_start",
        "pipeline_end",
        "pipeline_error",
    ]
    node_name: str | None
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    step: int | None = None


# Sentinel object for signalling end-of-stream
_STREAM_END: object = object()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def stream_pipeline_events(
    report_path: str | Path,
    ports: PipelinePorts,
    *,
    user_id: str | None = None,
    project_id: str | None = None,
    system_execution: bool = False,
    thread_id: str | None = None,
    stream_timeout_seconds: int = 600,
) -> Generator[PipelineEvent, None, PipelineState | None]:
    """Run the SIOPV pipeline and yield structured events as nodes execute.

    This is a **synchronous generator** suitable for direct consumption inside
    a Streamlit script run.  Internally it spawns a background thread with a
    dedicated asyncio event loop that drives ``astream_events(version="v2")``.

    Args:
        report_path: Path to the Trivy JSON report.
        ports: Fully wired ``PipelinePorts`` (use ``build_pipeline_ports``).
        user_id: Optional user ID for authorization.
        project_id: Optional project ID for authorization context.
        system_execution: If True, allows anonymous execution without user_id.
        thread_id: Optional checkpoint thread ID (defaults to a new UUID).
        stream_timeout_seconds: Maximum seconds to wait for the next event
            before raising ``TimeoutError``.

    Yields:
        ``PipelineEvent`` instances in chronological order.

    Returns:
        The final ``PipelineState`` after the generator is exhausted, or
        ``None`` if the pipeline errored before completion.

    Raises:
        TimeoutError: If no event arrives within ``stream_timeout_seconds``.
        Exception: Re-raises any unhandled exception from the pipeline thread.
    """
    effective_thread_id = thread_id or str(uuid.uuid4())

    initial_state = create_initial_state(
        report_path=str(report_path),
        thread_id=effective_thread_id,
        user_id=user_id,
        project_id=project_id,
        system_execution=system_execution,
    )

    config: RunnableConfig = {"configurable": {"thread_id": effective_thread_id}}

    event_queue: queue.Queue[PipelineEvent | object] = queue.Queue()
    final_state_holder: list[PipelineState] = []
    error_holder: list[BaseException] = []

    thread = _launch_stream_thread(
        ports, initial_state, config, event_queue, final_state_holder, error_holder
    )

    logger.info(
        "pipeline_streaming_started",
        thread_id=effective_thread_id,
        report_path=str(report_path),
    )

    # --- Yield events from queue ---
    yield from _drain_event_queue(event_queue, stream_timeout_seconds)

    thread.join(timeout=PIPELINE_STREAM_QUEUE_POLL_SECONDS)

    if error_holder:
        raise error_holder[0]

    return final_state_holder[0] if final_state_holder else None


def _launch_stream_thread(
    ports: PipelinePorts,
    initial_state: PipelineState,
    config: RunnableConfig,
    event_queue: queue.Queue[PipelineEvent | object],
    final_state_holder: list[PipelineState],
    error_holder: list[BaseException],
) -> threading.Thread:
    """Spawn a daemon thread that runs the pipeline async event loop.

    Args:
        ports: Pipeline port dependencies.
        initial_state: Initial pipeline state.
        config: LangGraph runnable config.
        event_queue: Thread-safe queue for emitting events.
        final_state_holder: Mutable list to capture final state.
        error_holder: Mutable list to capture exceptions.

    Returns:
        The started ``threading.Thread``.
    """

    async def _run_stream() -> None:
        builder = PipelineGraphBuilder(ports)
        builder.build()
        await _run_with_checkpointer(
            builder, ports, initial_state, config, event_queue, final_state_holder
        )

    def _thread_target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_stream())
        except Exception as exc:
            error_holder.append(exc)
            event_queue.put(
                PipelineEvent(
                    event_type="pipeline_error",
                    node_name=None,
                    timestamp=datetime.now(UTC),
                    data={"error": str(exc), "error_type": type(exc).__name__},
                )
            )
        finally:
            event_queue.put(_STREAM_END)
            loop.close()

    thread = threading.Thread(target=_thread_target, daemon=True, name="siopv-stream")
    thread.start()
    return thread


async def _run_with_checkpointer(
    builder: PipelineGraphBuilder,
    ports: PipelinePorts,
    initial_state: PipelineState,
    config: RunnableConfig,
    event_queue: queue.Queue[PipelineEvent | object],
    final_state_holder: list[PipelineState],
) -> None:
    """Compile graph with optional checkpointer and run event streaming."""
    checkpoint_db_path = ports.checkpoint_db_path
    if checkpoint_db_path is not None:
        validated_path = _validate_path(
            Path(checkpoint_db_path),
            allowed_extensions={".db", ".sqlite", ".sqlite3"},
        )
        async with AsyncSqliteSaver.from_conn_string(str(validated_path)) as checkpointer:
            graph = builder.compile(with_checkpointer=False)
            graph.checkpointer = checkpointer
            await _consume_events(graph, initial_state, config, event_queue, final_state_holder)
    else:
        graph = builder.compile(with_checkpointer=False)
        await _consume_events(graph, initial_state, config, event_queue, final_state_holder)


def _drain_event_queue(
    event_queue: queue.Queue[PipelineEvent | object],
    timeout_seconds: int,
) -> Generator[PipelineEvent, None, None]:
    """Drain events from the queue until the sentinel is received.

    Args:
        event_queue: Thread-safe queue of pipeline events.
        timeout_seconds: Max seconds to wait for each event.

    Yields:
        ``PipelineEvent`` instances.
    """
    while True:
        try:
            item = event_queue.get(timeout=timeout_seconds)
        except queue.Empty:
            msg = (
                f"Pipeline streaming timed out after {timeout_seconds}s without receiving an event"
            )
            raise TimeoutError(msg) from None

        if item is _STREAM_END:
            break
        if isinstance(item, PipelineEvent):
            yield item


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PIPELINE_NODE_SET: frozenset[str] = frozenset(PIPELINE_NODE_SEQUENCE)


async def _consume_events(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    initial_state: PipelineState,
    config: RunnableConfig,
    event_queue: queue.Queue[PipelineEvent | object],
    final_state_holder: list[PipelineState],
) -> None:
    """Consume ``astream_events`` and push parsed events to the queue."""
    event_queue.put(
        PipelineEvent(
            event_type="pipeline_start",
            node_name=None,
            timestamp=datetime.now(UTC),
        )
    )

    last_state: dict[str, Any] = {}

    async for raw_event in graph.astream_events(initial_state, config, version="v2"):
        # astream_events yields StandardStreamEvent | CustomStreamEvent;
        # both are dict-like — cast for type safety
        event_dict: dict[str, Any] = dict(raw_event)
        parsed = _parse_langgraph_event(event_dict)
        if parsed is not None:
            event_queue.put(parsed)

            # Track the latest state update from node_end events
            if parsed.event_type == "node_end" and parsed.data:
                last_state.update(parsed.data)

    # Capture final state
    if last_state:
        final_state_holder.append(last_state)  # type: ignore[arg-type]

    event_queue.put(
        PipelineEvent(
            event_type="pipeline_end",
            node_name=None,
            timestamp=datetime.now(UTC),
            data=last_state,
        )
    )


def _parse_langgraph_event(raw_event: dict[str, Any]) -> PipelineEvent | None:
    """Parse a raw ``astream_events`` v2 event into a ``PipelineEvent``.

    Filters for node-level chain start/end events only, discarding sub-chain
    events (LLM calls, tool invocations, etc.) that occur *within* a node.

    Args:
        raw_event: Raw event dict from ``astream_events(version="v2")``.

    Returns:
        A ``PipelineEvent`` if this is a relevant node-level event, else ``None``.
    """
    event_kind: str = raw_event.get("event", "")
    metadata: dict[str, Any] = raw_event.get("metadata", {})
    node_name: str | None = metadata.get("langgraph_node")

    # Only process events from known pipeline nodes
    if node_name is None or node_name not in _PIPELINE_NODE_SET:
        return None

    # Filter to node-level events: event["name"] must match the node name
    # to exclude sub-chain events running inside the node.
    event_name: str = raw_event.get("name", "")
    if event_name != node_name:
        return None

    step: int | None = metadata.get("langgraph_step")
    now = datetime.now(UTC)

    if event_kind == "on_chain_start":
        return PipelineEvent(
            event_type="node_start",
            node_name=node_name,
            timestamp=now,
            data=_safe_extract(raw_event, "input"),
            step=step,
        )

    if event_kind == "on_chain_end":
        return PipelineEvent(
            event_type="node_end",
            node_name=node_name,
            timestamp=now,
            data=_safe_extract(raw_event, "output"),
            step=step,
        )

    return None


def _safe_extract(raw_event: dict[str, Any], key: str) -> dict[str, Any]:
    """Safely extract nested data from a raw event.

    Args:
        raw_event: The raw event dict.
        key: Key to extract from ``event["data"]``.

    Returns:
        Extracted dict or empty dict if extraction fails.
    """
    try:
        data = raw_event.get("data", {})
        value = data.get(key, {})
    except (AttributeError, TypeError):
        return {}
    else:
        if isinstance(value, dict):
            return value
        return {"value": value}


__all__ = [
    "PipelineEvent",
    "stream_pipeline_events",
]
