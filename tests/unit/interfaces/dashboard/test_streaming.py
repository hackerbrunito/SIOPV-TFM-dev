"""Unit tests for the pipeline streaming bridge module."""

from __future__ import annotations

import queue
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from siopv.domain.constants import PIPELINE_NODE_SEQUENCE
from siopv.interfaces.dashboard.streaming import (
    _PIPELINE_NODE_SET,
    _STREAM_END,
    PipelineEvent,
    _drain_event_queue,
    _parse_langgraph_event,
    _safe_extract,
)

# ---------------------------------------------------------------------------
# PipelineEvent dataclass
# ---------------------------------------------------------------------------


class TestPipelineEvent:
    """Tests for PipelineEvent data model."""

    def test_create_node_start_event(self) -> None:
        now = datetime.now(UTC)
        event = PipelineEvent(
            event_type="node_start",
            node_name="ingest",
            timestamp=now,
            step=1,
        )
        assert event.event_type == "node_start"
        assert event.node_name == "ingest"
        assert event.timestamp == now
        assert event.step == 1
        assert event.data == {}

    def test_create_event_with_data(self) -> None:
        event = PipelineEvent(
            event_type="node_end",
            node_name="classify",
            timestamp=datetime.now(UTC),
            data={"classifications": {"CVE-2024-1234": {}}},
            step=5,
        )
        assert event.data["classifications"] == {"CVE-2024-1234": {}}

    def test_event_is_frozen(self) -> None:
        event = PipelineEvent(
            event_type="pipeline_start",
            node_name=None,
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            event.event_type = "pipeline_end"  # type: ignore[misc]

    def test_pipeline_error_event(self) -> None:
        event = PipelineEvent(
            event_type="pipeline_error",
            node_name=None,
            timestamp=datetime.now(UTC),
            data={"error": "Connection refused", "error_type": "ConnectionError"},
        )
        assert event.event_type == "pipeline_error"
        assert event.data["error_type"] == "ConnectionError"


# ---------------------------------------------------------------------------
# _parse_langgraph_event
# ---------------------------------------------------------------------------


class TestParseLanggraphEvent:
    """Tests for parsing raw astream_events v2 events."""

    def test_parse_node_start_event(self) -> None:
        raw = {
            "event": "on_chain_start",
            "name": "ingest",
            "metadata": {"langgraph_node": "ingest", "langgraph_step": 2},
            "data": {"input": {"report_path": "/tmp/report.json"}},
        }
        result = _parse_langgraph_event(raw)
        assert result is not None
        assert result.event_type == "node_start"
        assert result.node_name == "ingest"
        assert result.step == 2

    def test_parse_node_end_event(self) -> None:
        raw = {
            "event": "on_chain_end",
            "name": "classify",
            "metadata": {"langgraph_node": "classify", "langgraph_step": 5},
            "data": {"output": {"classifications": {"CVE-1": {}}}},
        }
        result = _parse_langgraph_event(raw)
        assert result is not None
        assert result.event_type == "node_end"
        assert result.node_name == "classify"
        assert "classifications" in result.data

    def test_ignore_unknown_node(self) -> None:
        raw = {
            "event": "on_chain_start",
            "name": "unknown_node",
            "metadata": {"langgraph_node": "unknown_node", "langgraph_step": 1},
            "data": {},
        }
        result = _parse_langgraph_event(raw)
        assert result is None

    def test_ignore_sub_chain_event(self) -> None:
        """Events where name != langgraph_node are sub-chain events."""
        raw = {
            "event": "on_chain_start",
            "name": "ChatAnthropic",
            "metadata": {"langgraph_node": "classify", "langgraph_step": 5},
            "data": {},
        }
        result = _parse_langgraph_event(raw)
        assert result is None

    def test_ignore_event_without_node_metadata(self) -> None:
        raw = {
            "event": "on_chain_start",
            "name": "LangGraph",
            "metadata": {},
            "data": {},
        }
        result = _parse_langgraph_event(raw)
        assert result is None

    def test_ignore_non_chain_events(self) -> None:
        raw = {
            "event": "on_chat_model_start",
            "name": "enrich",
            "metadata": {"langgraph_node": "enrich", "langgraph_step": 4},
            "data": {},
        }
        result = _parse_langgraph_event(raw)
        assert result is None

    def test_all_pipeline_nodes_recognized(self) -> None:
        for node_name in PIPELINE_NODE_SEQUENCE:
            assert node_name in _PIPELINE_NODE_SET

    def test_parse_authorize_start(self) -> None:
        raw = {
            "event": "on_chain_start",
            "name": "authorize",
            "metadata": {"langgraph_node": "authorize", "langgraph_step": 1},
            "data": {"input": {"user_id": "test-user"}},
        }
        result = _parse_langgraph_event(raw)
        assert result is not None
        assert result.node_name == "authorize"

    def test_parse_output_end(self) -> None:
        raw = {
            "event": "on_chain_end",
            "name": "output",
            "metadata": {"langgraph_node": "output", "langgraph_step": 7},
            "data": {"output": {"output_pdf_path": "/tmp/report.pdf"}},
        }
        result = _parse_langgraph_event(raw)
        assert result is not None
        assert result.event_type == "node_end"
        assert result.data.get("output_pdf_path") == "/tmp/report.pdf"


# ---------------------------------------------------------------------------
# _safe_extract
# ---------------------------------------------------------------------------


class TestSafeExtract:
    """Tests for _safe_extract helper."""

    def test_extract_dict_value(self) -> None:
        raw = {"data": {"input": {"key": "value"}}}
        result = _safe_extract(raw, "input")
        assert result == {"key": "value"}

    def test_extract_non_dict_value(self) -> None:
        raw = {"data": {"output": "string_value"}}
        result = _safe_extract(raw, "output")
        assert result == {"value": "string_value"}

    def test_extract_missing_key(self) -> None:
        raw = {"data": {}}
        result = _safe_extract(raw, "nonexistent")
        assert result == {}

    def test_extract_from_empty_event(self) -> None:
        raw: dict[str, Any] = {}
        result = _safe_extract(raw, "input")
        assert result == {}

    def test_extract_handles_none_data(self) -> None:
        raw = {"data": None}
        result = _safe_extract(raw, "input")
        assert result == {}


# ---------------------------------------------------------------------------
# _drain_event_queue
# ---------------------------------------------------------------------------


class TestDrainEventQueue:
    """Tests for the queue drain generator."""

    def test_drain_yields_events(self) -> None:
        q: queue.Queue[PipelineEvent | object] = queue.Queue()
        event = PipelineEvent(
            event_type="node_start",
            node_name="ingest",
            timestamp=datetime.now(UTC),
        )
        q.put(event)
        q.put(_STREAM_END)

        events = list(_drain_event_queue(q, timeout_seconds=5))
        assert len(events) == 1
        assert events[0].node_name == "ingest"

    def test_drain_stops_at_sentinel(self) -> None:
        q: queue.Queue[PipelineEvent | object] = queue.Queue()
        q.put(
            PipelineEvent(
                event_type="pipeline_start",
                node_name=None,
                timestamp=datetime.now(UTC),
            )
        )
        q.put(_STREAM_END)
        q.put(
            PipelineEvent(
                event_type="pipeline_end",
                node_name=None,
                timestamp=datetime.now(UTC),
            )
        )

        events = list(_drain_event_queue(q, timeout_seconds=5))
        # Should only get the event before sentinel
        assert len(events) == 1

    def test_drain_raises_timeout(self) -> None:
        q: queue.Queue[PipelineEvent | object] = queue.Queue()
        # Empty queue with very short timeout
        with pytest.raises(TimeoutError, match="timed out"):
            list(_drain_event_queue(q, timeout_seconds=0))

    def test_drain_multiple_events(self) -> None:
        q: queue.Queue[PipelineEvent | object] = queue.Queue()
        now = datetime.now(UTC)
        for name in ("authorize", "ingest", "dlp"):
            q.put(
                PipelineEvent(
                    event_type="node_start",
                    node_name=name,
                    timestamp=now,
                )
            )
        q.put(_STREAM_END)

        events = list(_drain_event_queue(q, timeout_seconds=5))
        assert len(events) == 3
        assert [e.node_name for e in events] == ["authorize", "ingest", "dlp"]

    def test_drain_ignores_non_event_items(self) -> None:
        q: queue.Queue[PipelineEvent | object] = queue.Queue()
        q.put("not_an_event")  # type: ignore[arg-type]
        q.put(
            PipelineEvent(
                event_type="pipeline_start",
                node_name=None,
                timestamp=datetime.now(UTC),
            )
        )
        q.put(_STREAM_END)

        events = list(_drain_event_queue(q, timeout_seconds=5))
        # String is not a PipelineEvent, should be skipped
        assert len(events) == 1


# ---------------------------------------------------------------------------
# _PIPELINE_NODE_SET consistency
# ---------------------------------------------------------------------------


class TestPipelineNodeSet:
    """Verify node set matches sequence constant."""

    def test_node_set_matches_sequence(self) -> None:
        assert frozenset(PIPELINE_NODE_SEQUENCE) == _PIPELINE_NODE_SET

    def test_expected_node_count(self) -> None:
        assert len(_PIPELINE_NODE_SET) == 7

    def test_all_expected_nodes_present(self) -> None:
        expected = {"authorize", "ingest", "dlp", "enrich", "classify", "escalate", "output"}
        assert expected == _PIPELINE_NODE_SET


# ---------------------------------------------------------------------------
# stream_pipeline_events (integration-level with mocked graph)
# ---------------------------------------------------------------------------


class TestStreamPipelineEvents:
    """Tests for the full stream_pipeline_events generator."""

    def test_stream_emits_pipeline_start_and_end(self) -> None:
        """Verify that the stream emits pipeline_start and pipeline_end events."""
        from siopv.interfaces.dashboard.streaming import (
            _consume_events,
        )

        # Create a mock graph that yields known events
        mock_graph = AsyncMock()
        mock_graph.astream_events = _make_async_event_generator(
            [
                {
                    "event": "on_chain_start",
                    "name": "authorize",
                    "metadata": {"langgraph_node": "authorize", "langgraph_step": 1},
                    "data": {"input": {}},
                },
                {
                    "event": "on_chain_end",
                    "name": "authorize",
                    "metadata": {"langgraph_node": "authorize", "langgraph_step": 1},
                    "data": {"output": {"authorization_allowed": True}},
                },
            ]
        )

        # We test _consume_events directly since it's the core logic
        import asyncio

        event_queue: queue.Queue[PipelineEvent | object] = queue.Queue()
        final_state_holder: list[Any] = []

        from siopv.application.orchestration.state import create_initial_state

        initial_state = create_initial_state(
            report_path="/tmp/test.json",
            thread_id="test-thread",
        )
        config: dict[str, Any] = {"configurable": {"thread_id": "test-thread"}}

        asyncio.run(
            _consume_events(mock_graph, initial_state, config, event_queue, final_state_holder)
        )

        events: list[PipelineEvent] = []
        while not event_queue.empty():
            item = event_queue.get_nowait()
            if isinstance(item, PipelineEvent):
                events.append(item)

        assert len(events) >= 3  # pipeline_start + authorize_start + authorize_end
        assert events[0].event_type == "pipeline_start"
        assert events[1].event_type == "node_start"
        assert events[1].node_name == "authorize"
        assert events[2].event_type == "node_end"
        assert events[2].node_name == "authorize"

    def test_consume_events_tracks_final_state(self) -> None:
        """Verify that _consume_events captures the final state."""
        from siopv.interfaces.dashboard.streaming import _consume_events

        mock_graph = AsyncMock()
        mock_graph.astream_events = _make_async_event_generator(
            [
                {
                    "event": "on_chain_end",
                    "name": "output",
                    "metadata": {"langgraph_node": "output", "langgraph_step": 7},
                    "data": {"output": {"output_pdf_path": "/tmp/report.pdf"}},
                },
            ]
        )

        import asyncio

        event_queue: queue.Queue[PipelineEvent | object] = queue.Queue()
        final_state_holder: list[Any] = []

        from siopv.application.orchestration.state import create_initial_state

        initial_state = create_initial_state(thread_id="test")
        config: dict[str, Any] = {"configurable": {"thread_id": "test"}}

        asyncio.run(
            _consume_events(mock_graph, initial_state, config, event_queue, final_state_holder)
        )

        assert len(final_state_holder) == 1
        assert final_state_holder[0].get("output_pdf_path") == "/tmp/report.pdf"

    def test_consume_events_emits_pipeline_end(self) -> None:
        """Verify pipeline_end event is emitted after all node events."""
        from siopv.interfaces.dashboard.streaming import _consume_events

        mock_graph = AsyncMock()
        mock_graph.astream_events = _make_async_event_generator([])

        import asyncio

        event_queue: queue.Queue[PipelineEvent | object] = queue.Queue()
        final_state_holder: list[Any] = []

        from siopv.application.orchestration.state import create_initial_state

        initial_state = create_initial_state(thread_id="test")
        config: dict[str, Any] = {"configurable": {"thread_id": "test"}}

        asyncio.run(
            _consume_events(mock_graph, initial_state, config, event_queue, final_state_holder)
        )

        events: list[PipelineEvent] = []
        while not event_queue.empty():
            item = event_queue.get_nowait()
            if isinstance(item, PipelineEvent):
                events.append(item)

        # pipeline_start + pipeline_end (no node events)
        assert len(events) == 2
        assert events[0].event_type == "pipeline_start"
        assert events[1].event_type == "pipeline_end"


def _make_async_event_generator(events: list[dict[str, Any]]) -> Any:
    """Create a mock async generator for astream_events."""

    async def _generator(*_args: Any, **_kwargs: Any) -> Any:
        for event in events:
            yield event

    return _generator
