"""Unit tests for the pipeline flow visualization component."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from siopv.domain.constants import (
    PIPELINE_NODE_LABELS,
    PIPELINE_NODE_SEQUENCE,
)
from siopv.interfaces.dashboard.components.pipeline_flow import (
    _NODE_SUMMARY_EXTRACTORS,
    FlowPlaceholders,
    NodeState,
    _extract_authorize,
    _extract_classify,
    _extract_dlp,
    _extract_enrich,
    _extract_escalate,
    _extract_ingest,
    _extract_node_summary,
    _extract_output,
    mark_skipped_nodes,
    update_node_end,
    update_node_error,
    update_node_start,
)

# ---------------------------------------------------------------------------
# NodeState
# ---------------------------------------------------------------------------


class TestNodeState:
    """Tests for NodeState dataclass."""

    def test_default_state(self) -> None:
        state = NodeState(name="ingest", label="Ingestion", description="Parse report")
        assert state.status == "pending"
        assert state.started_at is None
        assert state.completed_at is None
        assert state.data_summary == {}
        assert state.error_message is None

    def test_elapsed_seconds_none_when_not_started(self) -> None:
        state = NodeState(name="ingest", label="Ingestion", description="Test")
        assert state.elapsed_seconds is None

    def test_elapsed_seconds_running(self) -> None:
        started = datetime.now(UTC) - timedelta(seconds=5)
        state = NodeState(
            name="ingest",
            label="Ingestion",
            description="Test",
            started_at=started,
        )
        elapsed = state.elapsed_seconds
        assert elapsed is not None
        assert elapsed >= 5.0

    def test_elapsed_seconds_completed(self) -> None:
        started = datetime(2026, 3, 21, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2026, 3, 21, 10, 0, 3, tzinfo=UTC)
        state = NodeState(
            name="ingest",
            label="Ingestion",
            description="Test",
            started_at=started,
            completed_at=completed,
        )
        assert state.elapsed_seconds == 3.0

    def test_elapsed_display_empty_when_not_started(self) -> None:
        state = NodeState(name="ingest", label="Ingestion", description="Test")
        assert state.elapsed_display == ""

    def test_elapsed_display_milliseconds(self) -> None:
        started = datetime(2026, 3, 21, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2026, 3, 21, 10, 0, 0, 500_000, tzinfo=UTC)
        state = NodeState(
            name="ingest",
            label="Ingestion",
            description="Test",
            started_at=started,
            completed_at=completed,
        )
        assert state.elapsed_display == "500ms"

    def test_elapsed_display_seconds(self) -> None:
        started = datetime(2026, 3, 21, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2026, 3, 21, 10, 0, 15, tzinfo=UTC)
        state = NodeState(
            name="ingest",
            label="Ingestion",
            description="Test",
            started_at=started,
            completed_at=completed,
        )
        assert state.elapsed_display == "15.0s"

    def test_elapsed_display_minutes(self) -> None:
        started = datetime(2026, 3, 21, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2026, 3, 21, 10, 2, 30, tzinfo=UTC)
        state = NodeState(
            name="enrich",
            label="Enrichment",
            description="Test",
            started_at=started,
            completed_at=completed,
        )
        assert state.elapsed_display == "2m 30s"


# ---------------------------------------------------------------------------
# FlowPlaceholders
# ---------------------------------------------------------------------------


class TestFlowPlaceholders:
    """Tests for FlowPlaceholders dataclass."""

    def test_completed_count_empty(self) -> None:
        flow = FlowPlaceholders()
        assert flow.completed_count() == 0

    def test_completed_count_with_states(self) -> None:
        flow = FlowPlaceholders()
        flow.node_states["a"] = NodeState(
            name="a", label="A", description="test", status="complete"
        )
        flow.node_states["b"] = NodeState(name="b", label="B", description="test", status="running")
        flow.node_states["c"] = NodeState(name="c", label="C", description="test", status="skipped")
        assert flow.completed_count() == 2  # complete + skipped


# ---------------------------------------------------------------------------
# Node summary extractors
# ---------------------------------------------------------------------------


class TestExtractNodeSummary:
    """Tests for _extract_node_summary dispatch."""

    def test_unknown_node_returns_empty(self) -> None:
        assert _extract_node_summary("unknown", {"key": "val"}) == {}

    def test_dispatch_table_covers_all_nodes(self) -> None:
        for node in PIPELINE_NODE_SEQUENCE:
            assert node in _NODE_SUMMARY_EXTRACTORS


class TestExtractAuthorize:
    def test_authorized(self) -> None:
        result = _extract_authorize({"authorization_allowed": True})
        assert result == {"Access": "Granted"}

    def test_denied(self) -> None:
        result = _extract_authorize({"authorization_allowed": False})
        assert result == {"Access": "Denied"}

    def test_missing(self) -> None:
        result = _extract_authorize({})
        assert result == {}


class TestExtractIngest:
    def test_with_vulnerabilities(self) -> None:
        result = _extract_ingest({"vulnerabilities": [1, 2, 3]})
        assert result == {"CVEs": 3}

    def test_empty(self) -> None:
        result = _extract_ingest({})
        assert result == {}

    def test_non_list(self) -> None:
        result = _extract_ingest({"vulnerabilities": "not-a-list"})
        assert result == {}


class TestExtractDlp:
    def test_with_result(self) -> None:
        result = _extract_dlp({"dlp_result": {"sanitized_count": 5}})
        assert result == {"Sanitized": 5}

    def test_empty(self) -> None:
        result = _extract_dlp({})
        assert result == {}


class TestExtractEnrich:
    def test_with_enrichments(self) -> None:
        result = _extract_enrich({"enrichments": {"CVE-1": {}, "CVE-2": {}}})
        assert result == {"Enriched": 2}

    def test_empty(self) -> None:
        result = _extract_enrich({})
        assert result == {}


class TestExtractClassify:
    def test_with_classifications(self) -> None:
        result = _extract_classify({"classifications": {"CVE-1": {}}})
        assert result == {"Classified": 1}

    def test_with_escalated(self) -> None:
        result = _extract_classify(
            {
                "classifications": {"CVE-1": {}},
                "escalated_cves": ["CVE-1"],
            }
        )
        assert result == {"Classified": 1, "Escalated": 1}

    def test_empty_escalated_not_shown(self) -> None:
        result = _extract_classify(
            {
                "classifications": {"CVE-1": {}},
                "escalated_cves": [],
            }
        )
        assert "Escalated" not in result


class TestExtractEscalate:
    def test_with_decision(self) -> None:
        result = _extract_escalate({"human_decision": "approve", "escalation_level": 1})
        assert result == {"Decision": "approve", "Level": 1}

    def test_empty(self) -> None:
        result = _extract_escalate({})
        assert result == {}


class TestExtractOutput:
    def test_with_jira(self) -> None:
        result = _extract_output({"output_jira_keys": ["SEC-123"]})
        assert result == {"Jira": 1}

    def test_with_pdf(self) -> None:
        result = _extract_output({"output_pdf_path": "/tmp/report.pdf"})
        assert result == {"PDF": "Generated"}

    def test_with_errors(self) -> None:
        result = _extract_output({"output_errors": ["Jira unavailable"]})
        assert result == {"Warnings": 1}

    def test_empty(self) -> None:
        result = _extract_output({})
        assert result == {}


# ---------------------------------------------------------------------------
# UI update functions (with mocked Streamlit)
# ---------------------------------------------------------------------------


class TestUpdateNodeStart:
    """Tests for update_node_start."""

    def test_updates_state(self) -> None:
        flow = _make_flow_with_mocks()
        now = datetime.now(UTC)
        update_node_start(flow, "ingest", now)

        assert flow.node_states["ingest"].status == "running"
        assert flow.node_states["ingest"].started_at == now

    def test_unknown_node_is_noop(self) -> None:
        flow = _make_flow_with_mocks()
        update_node_start(flow, "nonexistent", datetime.now(UTC))
        # Should not raise


class TestUpdateNodeEnd:
    """Tests for update_node_end."""

    def test_updates_state(self) -> None:
        flow = _make_flow_with_mocks()
        start = datetime.now(UTC) - timedelta(seconds=2)
        end = datetime.now(UTC)

        flow.node_states["ingest"].status = "running"
        flow.node_states["ingest"].started_at = start

        update_node_end(flow, "ingest", end, {"vulnerabilities": [1, 2]})

        assert flow.node_states["ingest"].status == "complete"
        assert flow.node_states["ingest"].completed_at == end
        assert flow.node_states["ingest"].data_summary == {"CVEs": 2}


class TestUpdateNodeError:
    """Tests for update_node_error."""

    def test_updates_state(self) -> None:
        flow = _make_flow_with_mocks()
        update_node_error(flow, "enrich", "API timeout")

        assert flow.node_states["enrich"].status == "error"
        assert flow.node_states["enrich"].error_message == "API timeout"


class TestMarkSkippedNodes:
    """Tests for mark_skipped_nodes."""

    def test_marks_pending_as_skipped(self) -> None:
        flow = _make_flow_with_mocks()
        flow.node_states["authorize"].status = "complete"
        flow.node_states["ingest"].status = "complete"
        # dlp, enrich, classify, escalate, output remain "pending"

        mark_skipped_nodes(flow)

        assert flow.node_states["authorize"].status == "complete"
        assert flow.node_states["ingest"].status == "complete"
        assert flow.node_states["dlp"].status == "skipped"
        assert flow.node_states["escalate"].status == "skipped"

    def test_does_not_change_non_pending(self) -> None:
        flow = _make_flow_with_mocks()
        flow.node_states["enrich"].status = "error"
        mark_skipped_nodes(flow)
        assert flow.node_states["enrich"].status == "error"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flow_with_mocks() -> FlowPlaceholders:
    """Create a FlowPlaceholders with mock placeholders for testing."""
    flow = FlowPlaceholders()
    for name in PIPELINE_NODE_SEQUENCE:
        flow.node_states[name] = NodeState(
            name=name,
            label=PIPELINE_NODE_LABELS[name],
            description="test",
        )
        flow.placeholders[name] = MagicMock()
    flow.progress_bar = MagicMock()
    return flow
