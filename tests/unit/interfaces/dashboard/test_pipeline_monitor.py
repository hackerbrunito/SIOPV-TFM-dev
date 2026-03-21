"""Unit tests for the pipeline monitor Streamlit page."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from siopv.interfaces.dashboard.pipeline_monitor import (
    _handle_event,
    _initialize_session_state,
    _resolve_report_path,
)
from siopv.interfaces.dashboard.streaming import PipelineEvent

# ---------------------------------------------------------------------------
# _initialize_session_state
# ---------------------------------------------------------------------------


class TestInitializeSessionState:
    """Tests for session state initialization."""

    @patch("siopv.interfaces.dashboard.pipeline_monitor.st")
    def test_sets_default_keys(self, mock_st: MagicMock) -> None:
        mock_st.session_state = {}
        _initialize_session_state()

        assert mock_st.session_state["pipeline_running"] is False
        assert mock_st.session_state["pipeline_completed"] is False
        assert mock_st.session_state["last_run_data"] is None
        assert mock_st.session_state["last_run_flow"] is None

    @patch("siopv.interfaces.dashboard.pipeline_monitor.st")
    def test_does_not_overwrite_existing(self, mock_st: MagicMock) -> None:
        mock_st.session_state = {"pipeline_running": True}
        _initialize_session_state()

        assert mock_st.session_state["pipeline_running"] is True


# ---------------------------------------------------------------------------
# _resolve_report_path
# ---------------------------------------------------------------------------


class TestResolveReportPath:
    """Tests for report path resolution."""

    @patch("siopv.interfaces.dashboard.pipeline_monitor.st")
    def test_direct_path_valid(
        self,
        mock_st: MagicMock,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        report = tmp_path / "report.json"
        report.write_text('{"Results": []}')

        config = {
            "report_path": str(report),
            "uploaded_file": None,
        }
        result = _resolve_report_path(config)
        assert result == report

    @patch("siopv.interfaces.dashboard.pipeline_monitor.st")
    def test_direct_path_invalid(self, mock_st: MagicMock) -> None:
        config = {
            "report_path": "/nonexistent/report.json",
            "uploaded_file": None,
        }
        result = _resolve_report_path(config)
        assert result is None
        mock_st.error.assert_called_once()

    @patch("siopv.interfaces.dashboard.pipeline_monitor.st")
    def test_no_path_no_upload(
        self,
        mock_st: MagicMock,  # noqa: ARG002
    ) -> None:
        config = {
            "report_path": None,
            "uploaded_file": None,
        }
        result = _resolve_report_path(config)
        assert result is None

    @patch("siopv.interfaces.dashboard.pipeline_monitor.st")
    def test_uploaded_file(
        self,
        mock_st: MagicMock,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        mock_uploaded = MagicMock()
        mock_uploaded.name = "trivy-report.json"
        mock_uploaded.getvalue.return_value = b'{"Results": []}'

        with patch("siopv.infrastructure.config.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            config = {
                "report_path": None,
                "uploaded_file": mock_uploaded,
            }
            result = _resolve_report_path(config)
            assert result is not None
            assert result.name == "uploaded_trivy-report.json"
            assert result.exists()


# ---------------------------------------------------------------------------
# _handle_event
# ---------------------------------------------------------------------------


class TestHandleEvent:
    """Tests for event handling during pipeline execution."""

    def test_pipeline_start(self) -> None:
        flow = MagicMock()
        log_container = MagicMock()
        accumulated: dict[str, Any] = {}

        event = PipelineEvent(
            event_type="pipeline_start",
            node_name=None,
            timestamp=datetime.now(UTC),
        )

        with patch("siopv.interfaces.dashboard.pipeline_monitor.st"):
            _handle_event(event, flow, log_container, accumulated)

    def test_node_start(self) -> None:
        flow = MagicMock()
        flow.node_states = {"ingest": MagicMock(elapsed_display="1.2s")}
        log_container = MagicMock()
        accumulated: dict[str, Any] = {}

        event = PipelineEvent(
            event_type="node_start",
            node_name="ingest",
            timestamp=datetime.now(UTC),
        )

        with (
            patch("siopv.interfaces.dashboard.pipeline_monitor.st"),
            patch(
                "siopv.interfaces.dashboard.pipeline_monitor.update_node_start",
            ) as mock_update,
        ):
            _handle_event(event, flow, log_container, accumulated)
            mock_update.assert_called_once()

    def test_node_end_accumulates_data(self) -> None:
        flow = MagicMock()
        flow.node_states = {"ingest": MagicMock(elapsed_display="1.2s")}
        log_container = MagicMock()
        accumulated: dict[str, Any] = {}

        event = PipelineEvent(
            event_type="node_end",
            node_name="ingest",
            timestamp=datetime.now(UTC),
            data={"vulnerabilities": [1, 2, 3]},
        )

        with (
            patch("siopv.interfaces.dashboard.pipeline_monitor.st"),
            patch("siopv.interfaces.dashboard.pipeline_monitor.update_node_end"),
        ):
            _handle_event(event, flow, log_container, accumulated)

        assert accumulated["vulnerabilities"] == [1, 2, 3]

    def test_pipeline_end_accumulates_data(self) -> None:
        flow = MagicMock()
        log_container = MagicMock()
        accumulated: dict[str, Any] = {}

        event = PipelineEvent(
            event_type="pipeline_end",
            node_name=None,
            timestamp=datetime.now(UTC),
            data={"thread_id": "abc-123"},
        )

        with patch("siopv.interfaces.dashboard.pipeline_monitor.st"):
            _handle_event(event, flow, log_container, accumulated)

        assert accumulated["thread_id"] == "abc-123"

    def test_pipeline_error(self) -> None:
        flow = MagicMock()
        log_container = MagicMock()
        accumulated: dict[str, Any] = {}

        event = PipelineEvent(
            event_type="pipeline_error",
            node_name=None,
            timestamp=datetime.now(UTC),
            data={"error": "Something broke"},
        )

        with patch("siopv.interfaces.dashboard.pipeline_monitor.st"):
            _handle_event(event, flow, log_container, accumulated)
