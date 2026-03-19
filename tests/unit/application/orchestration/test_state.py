"""Tests for PipelineState and related state management."""

from __future__ import annotations

import pytest

from siopv.application.orchestration.state import (
    DiscrepancyHistory,
    DiscrepancyResult,
    ThresholdConfig,
    create_initial_state,
)


class TestPipelineState:
    """Tests for PipelineState TypedDict."""

    def test_create_initial_state_with_defaults(self) -> None:
        """Test creating initial state with default values."""
        state = create_initial_state()

        assert state["vulnerabilities"] == []
        assert state["enrichments"] == {}
        assert state["classifications"] == {}
        assert state["escalated_cves"] == []
        assert state["llm_confidence"] == {}
        assert state["processed_count"] == 0
        assert state["errors"] == []
        assert state["current_node"] == "start"
        assert state["thread_id"] is not None
        assert state["report_path"] is None

    def test_create_initial_state_with_report_path(self) -> None:
        """Test creating initial state with report path."""
        state = create_initial_state(report_path="/path/to/report.json")

        assert state["report_path"] == "/path/to/report.json"

    def test_create_initial_state_with_thread_id(self) -> None:
        """Test creating initial state with custom thread ID."""
        state = create_initial_state(thread_id="custom-thread-123")

        assert state["thread_id"] == "custom-thread-123"

    def test_state_is_typed_dict(self) -> None:
        """Test that PipelineState is a proper TypedDict."""
        state = create_initial_state()

        # TypedDict should be dict-like
        assert isinstance(state, dict)
        assert "vulnerabilities" in state
        assert "enrichments" in state


class TestDiscrepancyHistory:
    """Tests for DiscrepancyHistory tracking."""

    def test_empty_history_percentile(self) -> None:
        """Test percentile calculation with empty history."""
        history = DiscrepancyHistory(max_size=500, base_threshold=0.3)

        # Should return default threshold
        assert history.get_percentile(90) == 0.3

    def test_add_single_value(self) -> None:
        """Test adding a single discrepancy value."""
        history = DiscrepancyHistory(max_size=500, base_threshold=0.3)
        history.add(0.25)

        assert len(history.values) == 1
        assert history.values[0] == 0.25

    def test_add_multiple_values(self) -> None:
        """Test adding multiple discrepancy values."""
        history = DiscrepancyHistory(max_size=500, base_threshold=0.3)
        for value in [0.1, 0.2, 0.3, 0.4, 0.5]:
            history.add(value)

        assert len(history.values) == 5

    def test_percentile_calculation(self) -> None:
        """Test percentile calculation with values."""
        history = DiscrepancyHistory(max_size=500, base_threshold=0.3)
        # Add 10 values from 0.1 to 1.0
        for i in range(1, 11):
            history.add(i / 10)

        # 90th percentile should be around 0.9
        p90 = history.get_percentile(90)
        assert 0.8 <= p90 <= 1.0

    def test_history_size_limit(self) -> None:
        """Test that history respects max_size."""
        history = DiscrepancyHistory(max_size=5, base_threshold=0.3)

        # Add more than max_size
        for i in range(10):
            history.add(float(i))

        assert len(history.values) == 5
        # Should keep the last 5 values
        assert history.values == [5.0, 6.0, 7.0, 8.0, 9.0]

    def test_percentile_50(self) -> None:
        """Test 50th percentile (median)."""
        history = DiscrepancyHistory(max_size=500, base_threshold=0.3)
        for value in [0.1, 0.2, 0.3, 0.4, 0.5]:
            history.add(value)

        p50 = history.get_percentile(50)
        assert 0.2 <= p50 <= 0.3


class TestDiscrepancyResult:
    """Tests for DiscrepancyResult dataclass."""

    def test_discrepancy_result_creation(self) -> None:
        """Test creating a DiscrepancyResult."""
        result = DiscrepancyResult(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.6,
            discrepancy=0.2,
            should_escalate=False,
        )

        assert result.cve_id == "CVE-2024-1234"
        assert result.ml_score == 0.8
        assert result.llm_confidence == 0.6
        assert result.discrepancy == 0.2
        assert result.should_escalate is False

    def test_discrepancy_result_frozen(self) -> None:
        """Test that DiscrepancyResult is immutable."""
        result = DiscrepancyResult(
            cve_id="CVE-2024-1234",
            ml_score=0.8,
            llm_confidence=0.6,
            discrepancy=0.2,
            should_escalate=False,
        )

        with pytest.raises(AttributeError):
            result.cve_id = "CVE-2024-5678"


class TestThresholdConfig:
    """Tests for ThresholdConfig."""

    def test_default_config(self) -> None:
        """Test default threshold configuration."""
        config = ThresholdConfig(
            base_threshold=0.3,
            confidence_floor=0.7,
            percentile=90,
            history_size=500,
            default_confidence=0.5,
        )

        assert config.base_threshold == 0.3
        assert config.confidence_floor == 0.7
        assert config.percentile == 90
        assert config.history_size == 500
        assert config.default_confidence == 0.5

    def test_custom_config(self) -> None:
        """Test custom threshold configuration."""
        config = ThresholdConfig(
            base_threshold=0.25,
            confidence_floor=0.8,
            percentile=95,
            history_size=1000,
            default_confidence=0.6,
        )

        assert config.base_threshold == 0.25
        assert config.confidence_floor == 0.8
        assert config.percentile == 95
        assert config.history_size == 1000
        assert config.default_confidence == 0.6
