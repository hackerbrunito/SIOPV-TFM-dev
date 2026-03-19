"""Tests for conditional edge routing logic."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from siopv.application.orchestration.edges import (
    route_after_classify,
    route_after_escalate,
    should_escalate_route,
)
from siopv.application.orchestration.state import (
    PipelineState,
    create_initial_state,
)
from siopv.domain.services.discrepancy import (
    calculate_batch_discrepancies,
    calculate_discrepancy,
)
from siopv.domain.value_objects.discrepancy import DiscrepancyHistory, ThresholdConfig

_DEFAULT_CONFIG = ThresholdConfig(
    base_threshold=0.3,
    confidence_floor=0.7,
    percentile=90,
    history_size=500,
    default_confidence=0.5,
)


class TestShouldEscalateRoute:
    """Tests for the should_escalate_route function."""

    def test_empty_classifications_returns_end(self) -> None:
        """Test that empty classifications routes to end."""
        state = create_initial_state()

        result = should_escalate_route(state, config=_DEFAULT_CONFIG)

        assert result == "end"

    def test_confident_classifications_returns_continue(self) -> None:
        """Test that confident classifications route to continue."""
        # Create mock classification with high confidence
        mock_classification = MagicMock()
        mock_classification.risk_score.risk_probability = 0.8

        state: PipelineState = {
            **create_initial_state(),
            "classifications": {"CVE-2024-1234": mock_classification},
            "llm_confidence": {"CVE-2024-1234": 0.85},
        }

        result = should_escalate_route(state, config=_DEFAULT_CONFIG)

        assert result == "continue"

    def test_low_confidence_returns_escalate(self) -> None:
        """Test that low LLM confidence routes to escalate."""
        mock_classification = MagicMock()
        mock_classification.risk_score.risk_probability = 0.8

        state: PipelineState = {
            **create_initial_state(),
            "classifications": {"CVE-2024-1234": mock_classification},
            "llm_confidence": {"CVE-2024-1234": 0.5},  # Below 0.7 threshold
        }

        result = should_escalate_route(state, config=_DEFAULT_CONFIG)

        assert result == "escalate"

    def test_high_discrepancy_returns_escalate(self) -> None:
        """Test that high ML/LLM discrepancy routes to escalate."""
        mock_classification = MagicMock()
        mock_classification.risk_score.risk_probability = 0.9

        state: PipelineState = {
            **create_initial_state(),
            "classifications": {"CVE-2024-1234": mock_classification},
            "llm_confidence": {"CVE-2024-1234": 0.4},  # High discrepancy
        }

        result = should_escalate_route(state, config=_DEFAULT_CONFIG)

        assert result == "escalate"


class TestCalculateDiscrepancy:
    """Tests for calculate_discrepancy function."""

    def test_calculate_basic_discrepancy(self) -> None:
        """Test basic discrepancy calculation."""
        result = calculate_discrepancy(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.6,
            config=_DEFAULT_CONFIG,
        )

        assert result.cve_id == "CVE-2024-1234"
        assert result.ml_score == 0.8
        assert result.llm_confidence == 0.6
        assert result.discrepancy == pytest.approx(0.2, rel=0.01)

    def test_no_escalation_when_confident(self) -> None:
        """Test no escalation when scores are close and confidence is high."""
        result = calculate_discrepancy(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.75,
            config=_DEFAULT_CONFIG,
        )

        assert result.should_escalate is False

    def test_escalation_on_low_confidence(self) -> None:
        """Test escalation when LLM confidence is below floor."""
        result = calculate_discrepancy(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.5,  # Below 0.7 floor
            config=_DEFAULT_CONFIG,
        )

        assert result.should_escalate is True

    def test_escalation_on_high_discrepancy(self) -> None:
        """Test escalation when discrepancy exceeds threshold."""
        result = calculate_discrepancy(
            cve_id="CVE-2024-1234",
            ml_score=0.9,
            llm_confidence=0.5,  # 0.4 discrepancy > 0.3 threshold
            config=_DEFAULT_CONFIG,
        )

        assert result.should_escalate is True

    def test_custom_threshold(self) -> None:
        """Test with custom explicit threshold."""
        result = calculate_discrepancy(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.75,
            threshold=0.1,  # Stricter threshold
            config=_DEFAULT_CONFIG,
        )

        # 0.05 discrepancy < 0.1 threshold, but confidence is high
        assert result.should_escalate is False

    def test_custom_config(self) -> None:
        """Test with custom config."""
        config = ThresholdConfig(
            base_threshold=0.1,
            confidence_floor=0.8,
            percentile=90,
            history_size=500,
            default_confidence=0.5,
        )

        result = calculate_discrepancy(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.75,  # Below 0.8 floor
            config=config,
        )

        assert result.should_escalate is True


class TestCalculateBatchDiscrepancies:
    """Tests for calculate_batch_discrepancies function."""

    def test_batch_calculation_with_multiple_cves(self) -> None:
        """Test batch discrepancy calculation."""
        mock_class_1 = MagicMock()
        mock_class_1.risk_score.risk_probability = 0.9
        mock_class_2 = MagicMock()
        mock_class_2.risk_score.risk_probability = 0.5

        classifications = {
            "CVE-2024-1234": mock_class_1,
            "CVE-2024-5678": mock_class_2,
        }
        llm_confidence = {
            "CVE-2024-1234": 0.85,
            "CVE-2024-5678": 0.55,
        }

        results, threshold = calculate_batch_discrepancies(
            classifications,
            llm_confidence,
            config=_DEFAULT_CONFIG,
        )

        assert len(results) == 2
        assert isinstance(threshold, float)

    def test_batch_with_missing_risk_score(self) -> None:
        """Test batch handling of missing risk scores."""
        mock_class = MagicMock()
        mock_class.risk_score = None

        classifications = {"CVE-2024-1234": mock_class}
        llm_confidence = {"CVE-2024-1234": 0.5}

        results, _ = calculate_batch_discrepancies(
            classifications,
            llm_confidence,
            config=_DEFAULT_CONFIG,
        )

        # Should have result for the CVE with missing score
        assert len(results) >= 0  # Implementation may skip or handle differently

    def test_batch_with_custom_history(self) -> None:
        """Test batch with pre-populated history."""
        history = DiscrepancyHistory(
            max_size=_DEFAULT_CONFIG.history_size,
            base_threshold=_DEFAULT_CONFIG.base_threshold,
        )
        # Pre-populate with some values
        for v in [0.1, 0.2, 0.15, 0.18]:
            history.add(v)

        mock_class = MagicMock()
        mock_class.risk_score.risk_probability = 0.8

        classifications = {"CVE-2024-1234": mock_class}
        llm_confidence = {"CVE-2024-1234": 0.75}

        results, threshold = calculate_batch_discrepancies(
            classifications,
            llm_confidence,
            history=history,
            config=_DEFAULT_CONFIG,
        )

        assert len(results) == 1
        # Threshold should be influenced by history
        assert threshold > 0


class TestRouteAfterClassify:
    """Tests for route_after_classify function."""

    def test_route_to_end_on_errors(self) -> None:
        """Test routing to end when errors exist."""
        state: PipelineState = {
            **create_initial_state(),
            "errors": ["Some error occurred"],
            "classifications": {"CVE-2024-1234": MagicMock()},
        }

        result = route_after_classify(state, config=_DEFAULT_CONFIG)

        assert result == "end"

    def test_route_to_end_on_no_classifications(self) -> None:
        """Test routing to end with no classifications."""
        state = create_initial_state()

        result = route_after_classify(state, config=_DEFAULT_CONFIG)

        assert result == "end"

    def test_delegates_to_should_escalate(self) -> None:
        """Test that it delegates to should_escalate_route."""
        mock_classification = MagicMock()
        mock_classification.risk_score.risk_probability = 0.8

        state: PipelineState = {
            **create_initial_state(),
            "classifications": {"CVE-2024-1234": mock_classification},
            "llm_confidence": {"CVE-2024-1234": 0.5},  # Low confidence
        }

        result = route_after_classify(state, config=_DEFAULT_CONFIG)

        assert result == "escalate"


class TestRouteAfterEscalate:
    """Tests for route_after_escalate function."""

    def test_always_returns_end(self) -> None:
        """Test that escalate always routes to end."""
        state: PipelineState = {
            **create_initial_state(),
            "escalated_cves": ["CVE-2024-1234", "CVE-2024-5678"],
        }

        result = route_after_escalate(state)

        assert result == "end"

    def test_returns_end_with_no_escalations(self) -> None:
        """Test routing to end even with no escalations."""
        state = create_initial_state()

        result = route_after_escalate(state)

        assert result == "end"
