"""Tests for the evidence panel dashboard component."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from siopv.interfaces.dashboard.components.evidence_panel import (
    _render_ai_summary,
    _render_chain_of_thought,
    _render_lime_chart,
    render_evidence_panel,
)


class TestRenderEvidencePanel:
    """Tests for render_evidence_panel."""

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_empty_state_does_not_crash(self, mock_st: MagicMock) -> None:
        mock_tab = MagicMock()
        mock_tab.__enter__ = MagicMock(return_value=mock_tab)
        mock_tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [mock_tab, mock_tab, mock_tab]

        case: dict[str, object] = {
            "thread_id": "t-001",
            "state": {},
            "interrupt_data": {},
            "created_at": None,
        }
        render_evidence_panel(case)
        mock_st.subheader.assert_called_once_with("Evidence Review")


class TestRenderAiSummary:
    """Tests for _render_ai_summary."""

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_no_escalated_cves_shows_info(self, mock_st: MagicMock) -> None:
        _render_ai_summary([], {}, {})
        mock_st.info.assert_called_once_with("No escalated CVEs to display.")

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_no_enrichment_shows_warning(self, mock_st: MagicMock) -> None:
        _render_ai_summary(["CVE-2024-0001"], {}, {})
        mock_st.warning.assert_called_once()

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_enrichment_dict_renders_description(self, mock_st: MagicMock) -> None:
        enrichments = {
            "CVE-2024-0001": {
                "nvd_description": "Test vulnerability",
                "epss_score": 0.85,
                "github_advisories": [],
            },
        }
        _render_ai_summary(["CVE-2024-0001"], enrichments, {})

        markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
        assert any("Test vulnerability" in c for c in markdown_calls)

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_epss_none_shows_na(self, mock_st: MagicMock) -> None:
        """When epss_score is None, renders 'N/A'."""
        enrichments = {
            "CVE-2024-0001": {
                "nvd_description": "Desc",
                "epss_score": None,
                "github_advisories": [],
            },
        }
        _render_ai_summary(["CVE-2024-0001"], enrichments, {})
        markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
        assert any("N/A" in c for c in markdown_calls)

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_github_advisories_non_empty(self, mock_st: MagicMock) -> None:
        """When github_advisories is non-empty, renders count."""
        enrichments = {
            "CVE-2024-0001": {
                "nvd_description": "Desc",
                "epss_score": 0.5,
                "github_advisories": [{"id": "GHSA-001"}],
            },
        }
        _render_ai_summary(["CVE-2024-0001"], enrichments, {})
        markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
        assert any("1 found" in c for c in markdown_calls)

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_classification_with_risk_probability(self, mock_st: MagicMock) -> None:
        """When classification has risk_probability, renders risk score."""
        classifications = {
            "CVE-2024-0001": {"risk_probability": 0.9123},
        }
        _render_ai_summary(["CVE-2024-0001"], {}, classifications)
        markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
        assert any("0.9123" in c for c in markdown_calls)

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_enrichment_as_object_uses_vars(self, mock_st: MagicMock) -> None:
        """When enrichment is an object (not dict), uses vars() to extract data."""

        class FakeEnrichment:
            def __init__(self) -> None:
                self.nvd_description = "Object enrichment"
                self.epss_score = 0.42
                self.github_advisories: list[str] = []

        enrichments = {"CVE-2024-0001": FakeEnrichment()}
        _render_ai_summary(["CVE-2024-0001"], enrichments, {})
        markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
        assert any("Object enrichment" in c for c in markdown_calls)


class TestRenderLimeChart:
    """Tests for _render_lime_chart."""

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_no_data_shows_placeholder(self, mock_st: MagicMock) -> None:
        _render_lime_chart(["CVE-2024-0001"], {})
        mock_st.info.assert_called_once_with("LIME explanation not available for this case.")

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_empty_cves_shows_info(self, mock_st: MagicMock) -> None:
        _render_lime_chart([], {})
        mock_st.info.assert_called_once_with("No escalated CVEs to display.")

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_lime_data_renders_chart(self, mock_st: MagicMock) -> None:
        classifications = {
            "CVE-2024-0001": {
                "feature_importances": {"epss": 0.8, "cvss": 0.6, "age": -0.2},
            },
        }
        _render_lime_chart(["CVE-2024-0001"], classifications)
        mock_st.bar_chart.assert_called_once()

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_lime_non_dict_data_skipped(self, mock_st: MagicMock) -> None:
        """When lime_data exists but is not a dict, skip and show placeholder."""
        classifications = {
            "CVE-2024-0001": {
                "feature_importances": "not-a-dict",
            },
        }
        _render_lime_chart(["CVE-2024-0001"], classifications)
        mock_st.info.assert_called_once_with("LIME explanation not available for this case.")
        mock_st.bar_chart.assert_not_called()


class TestRenderChainOfThought:
    """Tests for _render_chain_of_thought."""

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_no_data_shows_placeholder(self, mock_st: MagicMock) -> None:
        _render_chain_of_thought(["CVE-2024-0001"], {})
        mock_st.info.assert_called_once_with("Chain-of-thought log not available for this case.")

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_cot_data_renders_code(self, mock_st: MagicMock) -> None:
        classifications = {
            "CVE-2024-0001": {
                "chain_of_thought": "Step 1: Analyzed EPSS\nStep 2: Checked CVSS",
            },
        }
        _render_chain_of_thought(["CVE-2024-0001"], classifications)
        mock_st.code.assert_called_once()

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_cot_none_skipped(self, mock_st: MagicMock) -> None:
        """When classification exists but has no CoT keys, skip and show placeholder."""
        classifications = {
            "CVE-2024-0001": {"risk_probability": 0.5},
        }
        _render_chain_of_thought(["CVE-2024-0001"], classifications)
        mock_st.info.assert_called_once_with("Chain-of-thought log not available for this case.")
        mock_st.code.assert_not_called()

    @patch("siopv.interfaces.dashboard.components.evidence_panel.st")
    def test_cot_non_string_converted(self, mock_st: MagicMock) -> None:
        """When cot_log is not a string, it gets converted via str()."""
        classifications = {
            "CVE-2024-0001": {
                "chain_of_thought": ["Step 1", "Step 2"],
            },
        }
        _render_chain_of_thought(["CVE-2024-0001"], classifications)
        mock_st.code.assert_called_once()
        code_arg = mock_st.code.call_args[0][0]
        assert "Step 1" in code_arg
