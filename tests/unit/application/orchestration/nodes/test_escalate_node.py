"""Tests for escalate_node with Phase 7 HITL interrupt support."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from siopv.application.orchestration.nodes.escalate_node import (
    _calculate_escalation_level,
    escalate_node,
    get_escalation_summary,
)
from siopv.application.orchestration.state import create_initial_state
from siopv.application.use_cases.classify_risk import ClassificationResult
from siopv.domain.value_objects.risk_score import RiskScore


class TestEscalateNode:
    """Tests for escalate_node function."""

    @pytest.fixture
    def mock_classification_high_confidence(self) -> ClassificationResult:
        """Create classification with high confidence (no escalation needed)."""
        return ClassificationResult(
            cve_id="CVE-2024-1111",
            risk_score=RiskScore.from_prediction(
                cve_id="CVE-2024-1111",
                probability=0.8,
            ),
        )

    @pytest.fixture
    def mock_classification_low_confidence(self) -> ClassificationResult:
        """Create classification that should trigger escalation."""
        return ClassificationResult(
            cve_id="CVE-2024-2222",
            risk_score=RiskScore.from_prediction(
                cve_id="CVE-2024-2222",
                probability=0.9,
            ),
        )

    @pytest.fixture
    def mock_classification_no_score(self) -> ClassificationResult:
        """Create classification with no risk score."""
        return ClassificationResult(
            cve_id="CVE-2024-3333",
            risk_score=None,
        )

    def test_escalate_node_no_classifications(self) -> None:
        """Test escalate node with no classifications returns escalation_required=False."""
        state = create_initial_state()

        result = escalate_node(state)

        assert result["escalated_cves"] == []
        assert result["escalation_required"] is False
        assert result["current_node"] == "escalate"

    def test_escalate_node_no_escalation_needed(
        self, mock_classification_high_confidence: ClassificationResult
    ) -> None:
        """Test escalate node when no escalation needed (no interrupt called)."""
        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-1111": mock_classification_high_confidence},
            "llm_confidence": {"CVE-2024-1111": 0.85},
        }

        result = escalate_node(state)

        assert result["current_node"] == "escalate"
        assert result["escalation_required"] is False
        assert len(result["escalated_cves"]) == 0

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_escalate_node_calls_interrupt_with_candidates(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test that escalate_node calls interrupt() when candidates exist."""
        mock_interrupt.return_value = {"decision": "approve"}  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        result = escalate_node(state)

        mock_interrupt.assert_called_once()  # type: ignore[union-attr]
        assert result["escalation_required"] is True
        assert result["human_decision"] == "approve"
        assert "CVE-2024-2222" in result["escalated_cves"]

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_interrupt_receives_correct_data_structure(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test that interrupt() receives a JSON-serializable dict with expected keys."""
        mock_interrupt.return_value = {"decision": "reject"}  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        escalate_node(state)

        call_args = mock_interrupt.call_args  # type: ignore[union-attr]
        escalation_data = call_args[0][0]

        assert "escalated_cves" in escalation_data
        assert "escalation_timestamp" in escalation_data
        assert "review_deadline" in escalation_data
        assert "summary" in escalation_data
        assert "CVE-2024-2222" in escalation_data["escalated_cves"]
        assert isinstance(escalation_data["summary"], list)
        assert len(escalation_data["summary"]) == 1
        assert escalation_data["summary"][0]["cve_id"] == "CVE-2024-2222"

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_human_decision_approve(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test processing of 'approve' human decision after interrupt."""
        mock_interrupt.return_value = {"decision": "approve"}  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        result = escalate_node(state)

        assert result["human_decision"] == "approve"
        assert result["human_modified_score"] is None
        assert result["human_modified_recommendation"] is None

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_human_decision_reject(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test processing of 'reject' human decision after interrupt."""
        mock_interrupt.return_value = {"decision": "reject"}  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        result = escalate_node(state)

        assert result["human_decision"] == "reject"

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_human_decision_modify(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test processing of 'modify' human decision with overrides."""
        mock_interrupt.return_value = {  # type: ignore[union-attr]
            "decision": "modify",
            "modified_score": 0.75,
            "modified_recommendation": "Patch immediately",
        }

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        result = escalate_node(state)

        assert result["human_decision"] == "modify"
        assert result["human_modified_score"] == 0.75
        assert result["human_modified_recommendation"] == "Patch immediately"

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_escalation_timestamp_and_deadline_set(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test that escalation_timestamp and review_deadline are set correctly."""
        mock_interrupt.return_value = {"decision": "approve"}  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        result = escalate_node(state)

        assert result["escalation_timestamp"] is not None
        assert result["review_deadline"] is not None

        # Verify deadline is ~24h after timestamp
        ts = datetime.fromisoformat(result["escalation_timestamp"])
        dl = datetime.fromisoformat(result["review_deadline"])
        delta = dl - ts
        assert timedelta(hours=23, minutes=59) <= delta <= timedelta(hours=24, minutes=1)

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_escalate_node_missing_risk_score_escalates(
        self,
        mock_interrupt: object,
        mock_classification_no_score: ClassificationResult,
    ) -> None:
        """Test escalate node escalates CVE with missing risk score."""
        mock_interrupt.return_value = {"decision": "approve"}  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-3333": mock_classification_no_score},
            "llm_confidence": {"CVE-2024-3333": 0.8},
        }

        result = escalate_node(state)

        assert result["escalation_required"] is True
        assert "CVE-2024-3333" in result["escalated_cves"]
        mock_interrupt.assert_called_once()  # type: ignore[union-attr]

    @patch("siopv.application.orchestration.nodes.escalate_node.interrupt")
    def test_escalate_node_non_dict_response_defaults_to_approve(
        self,
        mock_interrupt: object,
        mock_classification_low_confidence: ClassificationResult,
    ) -> None:
        """Test that a non-dict interrupt response defaults to 'approve'."""
        mock_interrupt.return_value = "approve"  # type: ignore[union-attr]

        state = {
            **create_initial_state(),
            "classifications": {"CVE-2024-2222": mock_classification_low_confidence},
            "llm_confidence": {"CVE-2024-2222": 0.4},
        }

        result = escalate_node(state)

        assert result["human_decision"] == "approve"
        assert result["human_modified_score"] is None
        assert result["human_modified_recommendation"] is None


class TestCalculateEscalationLevel:
    """Tests for _calculate_escalation_level function."""

    def test_level_0_no_elapsed_time(self) -> None:
        """Test level 0 when virtually no time has elapsed."""
        now = datetime.now(UTC)
        timestamp = now.isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 0

    def test_level_0_under_4_hours(self) -> None:
        """Test level 0 when under 4 hours have elapsed."""
        now = datetime.now(UTC)
        timestamp = (now - timedelta(hours=3, minutes=59)).isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 0

    def test_level_1_over_4_hours(self) -> None:
        """Test level 1 (analyst notified) when >4h elapsed."""
        now = datetime.now(UTC)
        timestamp = (now - timedelta(hours=5)).isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 1

    def test_level_2_over_8_hours(self) -> None:
        """Test level 2 (lead escalated) when >8h elapsed."""
        now = datetime.now(UTC)
        timestamp = (now - timedelta(hours=9)).isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 2

    def test_level_3_over_24_hours(self) -> None:
        """Test level 3 (auto-approved) when >24h elapsed."""
        now = datetime.now(UTC)
        timestamp = (now - timedelta(hours=25)).isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 3

    def test_level_boundary_exactly_4_hours(self) -> None:
        """Test boundary: exactly 4h should be level 0 (need >4h)."""
        now = datetime.now(UTC)
        # Slightly under 4h to stay at level 0
        timestamp = (now - timedelta(hours=4, seconds=-1)).isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 0

    def test_level_boundary_just_over_24_hours(self) -> None:
        """Test boundary: just over 24h should be level 3."""
        now = datetime.now(UTC)
        timestamp = (now - timedelta(hours=24, seconds=1)).isoformat()

        level = _calculate_escalation_level(timestamp)

        assert level == 3


class TestGetEscalationSummary:
    """Tests for get_escalation_summary function."""

    @pytest.fixture
    def mock_classification(self) -> ClassificationResult:
        """Create mock classification for summary."""
        return ClassificationResult(
            cve_id="CVE-2024-1234",
            risk_score=RiskScore.from_prediction(
                cve_id="CVE-2024-1234",
                probability=0.85,
            ),
        )

    def test_get_escalation_summary_empty(self) -> None:
        """Test escalation summary with no escalations."""
        state = {
            **create_initial_state(),
            "escalated_cves": [],
            "classifications": {},
            "llm_confidence": {},
        }

        summary = get_escalation_summary(state)

        assert summary["total_escalated"] == 0
        assert summary["total_processed"] == 0
        assert summary["escalation_rate"] == 0
        assert summary["escalated_details"] == []

    def test_get_escalation_summary_with_escalations(
        self, mock_classification: ClassificationResult
    ) -> None:
        """Test escalation summary with escalated CVEs."""
        state = {
            **create_initial_state(),
            "escalated_cves": ["CVE-2024-1234"],
            "classifications": {"CVE-2024-1234": mock_classification},
            "llm_confidence": {"CVE-2024-1234": 0.5},
        }

        summary = get_escalation_summary(state)

        assert summary["total_escalated"] == 1
        assert summary["total_processed"] == 1
        assert summary["escalation_rate"] == 100.0
        assert len(summary["escalated_details"]) == 1

        detail = summary["escalated_details"][0]
        assert detail["cve_id"] == "CVE-2024-1234"
        assert detail["llm_confidence"] == 0.5
        assert detail["ml_score"] == 0.85
        assert detail["discrepancy"] == pytest.approx(0.35, rel=0.01)

    def test_get_escalation_summary_sorts_by_discrepancy(self) -> None:
        """Test escalation summary sorts by discrepancy (highest first)."""
        classification1 = ClassificationResult(
            cve_id="CVE-2024-1111",
            risk_score=RiskScore.from_prediction(
                cve_id="CVE-2024-1111",
                probability=0.9,
            ),
        )
        classification2 = ClassificationResult(
            cve_id="CVE-2024-2222",
            risk_score=RiskScore.from_prediction(
                cve_id="CVE-2024-2222",
                probability=0.5,
            ),
        )

        state = {
            **create_initial_state(),
            "escalated_cves": ["CVE-2024-1111", "CVE-2024-2222"],
            "classifications": {
                "CVE-2024-1111": classification1,
                "CVE-2024-2222": classification2,
            },
            "llm_confidence": {
                "CVE-2024-1111": 0.5,  # discrepancy = 0.4
                "CVE-2024-2222": 0.45,  # discrepancy = 0.05
            },
        }

        summary = get_escalation_summary(state)

        assert summary["escalated_details"][0]["cve_id"] == "CVE-2024-1111"
        assert summary["escalated_details"][1]["cve_id"] == "CVE-2024-2222"

    def test_get_escalation_summary_handles_missing_risk_score(self) -> None:
        """Test escalation summary handles CVE with missing risk score."""
        classification = ClassificationResult(
            cve_id="CVE-2024-9999",
            risk_score=None,
        )

        state = {
            **create_initial_state(),
            "escalated_cves": ["CVE-2024-9999"],
            "classifications": {"CVE-2024-9999": classification},
            "llm_confidence": {"CVE-2024-9999": 0.6},
        }

        summary = get_escalation_summary(state)

        assert len(summary["escalated_details"]) == 1
        detail = summary["escalated_details"][0]
        assert detail["cve_id"] == "CVE-2024-9999"
        assert detail["ml_score"] is None
        assert detail["discrepancy"] is None
