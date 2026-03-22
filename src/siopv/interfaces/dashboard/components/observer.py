"""Pipeline observer for detecting and tracking SIOPV pipeline executions.

Polls the LangGraph checkpoint database to discover active and completed
pipeline threads.  Used by the dashboard to passively observe pipelines
triggered by the webhook (or any other entry point) without requiring
the dashboard to start the pipeline itself.

The observer reads checkpoint snapshots via ``graph.get_state()`` and
``graph.get_state_history()`` to reconstruct which nodes have executed,
what data they produced, and whether the pipeline is still running.

Architecture
------------
::

    [Webhook / CLI]          [SQLite checkpoint DB]          [Streamlit Dashboard]
          │                         │                               │
     run_pipeline() ──writes──►  checkpoints  ◄──reads──  observer.py
          │                         │                               │
          ▼                         ▼                               ▼
    Pipeline executes      State saved per node          Poll & reconstruct
                                                          node progress
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from siopv.domain.constants import PIPELINE_NODE_SEQUENCE

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.graph.state import CompiledStateGraph

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PipelineRunInfo:
    """Summary of a single pipeline execution discovered via checkpoints.

    Attributes:
        thread_id: Unique identifier for this pipeline run.
        created_at: When the first checkpoint was created.
        is_running: Whether the pipeline still has pending nodes.
        is_interrupted: Whether the pipeline is waiting for human review.
        completed_nodes: Set of node names that have finished executing.
        pending_nodes: Tuple of node names scheduled to execute next.
        current_state: Latest pipeline state from the checkpoint.
        step_count: Number of super-steps executed so far.
        vulnerability_count: Number of vulnerabilities parsed (if available).
        classification_count: Number of classifications produced (if available).
        escalated_count: Number of escalated CVEs (if available).
        error_count: Number of errors encountered (if available).
    """

    thread_id: str
    created_at: str | None = None
    is_running: bool = False
    is_interrupted: bool = False
    completed_nodes: set[str] = field(default_factory=set)
    pending_nodes: tuple[str, ...] = ()
    current_state: dict[str, Any] = field(default_factory=dict)
    step_count: int = 0
    vulnerability_count: int = 0
    classification_count: int = 0
    escalated_count: int = 0
    error_count: int = 0


# ---------------------------------------------------------------------------
# Observer functions
# ---------------------------------------------------------------------------


def discover_pipeline_threads(
    conn: sqlite3.Connection,
) -> list[str]:
    """Query the checkpoint database for all distinct pipeline thread IDs.

    Args:
        conn: SQLite connection to the checkpoint database (WAL mode).

    Returns:
        List of thread_id strings, most recent first.
    """
    cursor = conn.execute(
        "SELECT DISTINCT thread_id FROM checkpoints "
        "WHERE checkpoint_ns = '' "
        "ORDER BY thread_id DESC"
    )
    return [row[0] for row in cursor.fetchall()]


def get_pipeline_run_info(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    thread_id: str,
) -> PipelineRunInfo | None:
    """Reconstruct pipeline execution state from checkpoint data.

    Reads the latest checkpoint for the given thread and inspects:
    - ``snapshot.next`` to determine if the pipeline is still running
    - ``snapshot.tasks`` to check for HITL interrupts
    - ``snapshot.values`` for the accumulated state data
    - ``snapshot.metadata`` for step count and completed writes

    Args:
        graph: Compiled pipeline graph with checkpointer attached.
        thread_id: The pipeline thread to inspect.

    Returns:
        ``PipelineRunInfo`` with reconstructed execution state,
        or ``None`` if the thread has no checkpoints.
    """
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = graph.get_state(config)
    except Exception:
        logger.exception("observer_get_state_failed", thread_id=thread_id)
        return None

    if snapshot is None:
        return None

    state = snapshot.values or {}
    metadata = snapshot.metadata or {}

    # Determine completed nodes from state history
    completed = _extract_completed_nodes(graph, config)

    # Check if pipeline is still running (has pending nodes)
    pending = snapshot.next or ()
    is_running = len(pending) > 0

    # Check for HITL interrupts
    is_interrupted = False
    if snapshot.tasks:
        is_interrupted = any(hasattr(t, "interrupts") and t.interrupts for t in snapshot.tasks)

    return PipelineRunInfo(
        thread_id=thread_id,
        created_at=snapshot.created_at,
        is_running=is_running and not is_interrupted,
        is_interrupted=is_interrupted,
        completed_nodes=completed,
        pending_nodes=tuple(pending),
        current_state=dict(state),
        step_count=metadata.get("step", 0),
        vulnerability_count=len(state.get("vulnerabilities", [])),
        classification_count=len(state.get("classifications", {})),
        escalated_count=len(state.get("escalated_cves", [])),
        error_count=len(state.get("errors", [])),
    )


def get_active_runs(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    conn: sqlite3.Connection,
) -> list[PipelineRunInfo]:
    """Find all currently running pipeline executions.

    Args:
        graph: Compiled graph with checkpointer.
        conn: SQLite connection.

    Returns:
        List of ``PipelineRunInfo`` for threads that are still executing.
    """
    thread_ids = discover_pipeline_threads(conn)
    active: list[PipelineRunInfo] = []

    for tid in thread_ids:
        info = get_pipeline_run_info(graph, tid)
        if info is not None and info.is_running:
            active.append(info)

    return active


def get_completed_runs(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
) -> list[PipelineRunInfo]:
    """Find completed pipeline executions for historical view.

    Args:
        graph: Compiled graph with checkpointer.
        conn: SQLite connection.
        limit: Maximum number of completed runs to return.

    Returns:
        List of ``PipelineRunInfo`` for threads that have finished,
        ordered by creation time (most recent first).
    """
    thread_ids = discover_pipeline_threads(conn)
    completed: list[PipelineRunInfo] = []

    for tid in thread_ids:
        if len(completed) >= limit:
            break
        info = get_pipeline_run_info(graph, tid)
        if info is not None and not info.is_running and not info.is_interrupted:
            completed.append(info)

    return completed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_completed_nodes(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    config: RunnableConfig,
) -> set[str]:
    """Extract the set of completed node names from checkpoint history.

    Walks the state history backwards and collects node names from the
    ``writes`` metadata field of each checkpoint.

    Args:
        graph: Compiled graph with checkpointer.
        config: Config with thread_id for history lookup.

    Returns:
        Set of node names that have completed execution.
    """
    completed: set[str] = set()
    pipeline_node_set = frozenset(PIPELINE_NODE_SEQUENCE)

    try:
        for state_snapshot in graph.get_state_history(config):
            writes = (state_snapshot.metadata or {}).get("writes", {})
            if isinstance(writes, dict):
                for node_name in writes:
                    if node_name in pipeline_node_set:
                        completed.add(node_name)
    except Exception:
        logger.exception("observer_history_failed")

    return completed


__all__ = [
    "PipelineRunInfo",
    "discover_pipeline_threads",
    "get_active_runs",
    "get_completed_runs",
    "get_pipeline_run_info",
]
