"""Unit tests for the pipeline summary component."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from siopv.interfaces.dashboard.components.pipeline_summary import (
    _format_total_time,
    _render_classification_distribution,
    _render_errors,
    _render_key_metrics,
    _render_output_artifacts,
)

# ---------------------------------------------------------------------------
# _format_total_time
# ---------------------------------------------------------------------------


class TestFormatTotalTime:
    """Tests for _format_total_time helper."""

    def test_seconds_only(self) -> None:
        assert _format_total_time(30.5) == "30.5s"

    def test_minutes_and_seconds(self) -> None:
        assert _format_total_time(150.0) == "2m 30s"

    def test_zero_seconds(self) -> None:
        assert _format_total_time(0.0) == "0.0s"

    def test_exact_minute(self) -> None:
        assert _format_total_time(60.0) == "1m 0s"

    def test_large_value(self) -> None:
        result = _format_total_time(3661.0)
        assert result == "61m 1s"


# ---------------------------------------------------------------------------
# _render_key_metrics (with mocked Streamlit)
# ---------------------------------------------------------------------------


class TestRenderKeyMetrics:
    """Tests for _render_key_metrics."""

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_renders_correct_counts(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col, mock_col]

        data = {
            "vulnerabilities": [1, 2, 3],
            "classifications": {"a": {}, "b": {}},
            "escalated_cves": ["a"],
            "errors": [],
        }
        _render_key_metrics(data)

        mock_st.columns.assert_called_once_with(4)

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_handles_missing_keys(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col, mock_col]

        _render_key_metrics({})
        # Should not raise


# ---------------------------------------------------------------------------
# _render_errors
# ---------------------------------------------------------------------------


class TestRenderErrors:
    """Tests for _render_errors."""

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_no_errors_renders_nothing(self, mock_st: MagicMock) -> None:
        _render_errors({"errors": [], "output_errors": []})
        mock_st.markdown.assert_not_called()

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_with_errors_renders_header(self, mock_st: MagicMock) -> None:
        _render_errors({"errors": ["Error 1"], "output_errors": []})
        mock_st.markdown.assert_called_once_with("#### Errors & Warnings")


# ---------------------------------------------------------------------------
# _render_output_artifacts
# ---------------------------------------------------------------------------


class TestRenderOutputArtifacts:
    """Tests for _render_output_artifacts."""

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_no_artifacts_renders_nothing(self, mock_st: MagicMock) -> None:
        _render_output_artifacts({})
        mock_st.markdown.assert_not_called()

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_with_pdf_renders_path(self, mock_st: MagicMock) -> None:
        _render_output_artifacts({"output_pdf_path": "/tmp/report.pdf"})
        mock_st.markdown.assert_any_call("#### Output Artifacts")
        mock_st.markdown.assert_any_call("**PDF Report:** `/tmp/report.pdf`")

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_with_jira_keys(self, mock_st: MagicMock) -> None:
        _render_output_artifacts({"output_jira_keys": ["SEC-1", "SEC-2"]})
        mock_st.markdown.assert_any_call("**Jira Tickets:** SEC-1, SEC-2")


# ---------------------------------------------------------------------------
# _render_classification_distribution
# ---------------------------------------------------------------------------


class TestRenderClassificationDistribution:
    """Tests for _render_classification_distribution."""

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_no_classifications_renders_nothing(self, mock_st: MagicMock) -> None:
        _render_classification_distribution({})
        mock_st.markdown.assert_not_called()

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_classifications_bucket_correctly(self, mock_st: MagicMock) -> None:
        """Verify classifications are bucketed by risk probability thresholds."""
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col] * 5

        data = {
            "classifications": {
                "CVE-1": {"risk_probability": 0.9},  # CRITICAL
                "CVE-2": {"risk_probability": 0.7},  # HIGH
                "CVE-3": {"risk_probability": 0.5},  # MEDIUM
                "CVE-4": {"risk_probability": 0.3},  # LOW
                "CVE-5": {"risk_probability": 0.1},  # MINIMAL
            }
        }
        _render_classification_distribution(data)
        mock_st.markdown.assert_called_once_with("#### Risk Classification Distribution")

    @patch("siopv.interfaces.dashboard.components.pipeline_summary.st")
    def test_handles_non_dict_classification(self, mock_st: MagicMock) -> None:
        """Should handle classification objects with attributes."""
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col] * 5

        class FakeClassification:
            risk_probability = 0.85

        data = {"classifications": {"CVE-1": FakeClassification()}}
        _render_classification_distribution(data)
        # Should not raise
