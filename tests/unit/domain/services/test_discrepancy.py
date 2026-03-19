"""Tests for discrepancy calculation service.

Covers uncovered branches:
- calculate_discrepancy with config=None raises ValueError
- calculate_batch_discrepancies with config=None raises ValueError
"""

from __future__ import annotations

import pytest

from siopv.domain.services.discrepancy import (
    calculate_batch_discrepancies,
    calculate_discrepancy,
)
from siopv.domain.value_objects.discrepancy import ThresholdConfig

_DEFAULT_CONFIG = ThresholdConfig(
    base_threshold=0.3,
    confidence_floor=0.7,
    percentile=90,
    history_size=500,
    default_confidence=0.5,
)


class TestCalculateDiscrepancy:
    def test_raises_when_config_is_none(self) -> None:
        with pytest.raises(ValueError, match="ThresholdConfig must be provided"):
            calculate_discrepancy("CVE-2024-0001", 0.8, 0.5, config=None)

    def test_uses_base_threshold_when_no_explicit_threshold(self) -> None:
        result = calculate_discrepancy("CVE-2024-0001", 0.8, 0.5, config=_DEFAULT_CONFIG)
        assert result.discrepancy == pytest.approx(0.3)
        # discrepancy == threshold (0.3), not > threshold, so no escalation from discrepancy
        # but llm_confidence 0.5 < confidence_floor 0.7 → should_escalate
        assert result.should_escalate is True

    def test_uses_explicit_threshold_over_base(self) -> None:
        result = calculate_discrepancy(
            "CVE-2024-0001", 0.8, 0.5, threshold=0.5, config=_DEFAULT_CONFIG
        )
        # discrepancy=0.3, threshold=0.5 → discrepancy < threshold
        # but llm_confidence=0.5 < 0.7 → still escalate
        assert result.should_escalate is True

    def test_no_escalation_when_both_conditions_false(self) -> None:
        result = calculate_discrepancy("CVE-2024-0001", 0.8, 0.75, config=_DEFAULT_CONFIG)
        # discrepancy=0.05, threshold=0.3 → no; llm_confidence=0.75 >= 0.7 → no
        assert result.should_escalate is False

    def test_escalation_from_high_discrepancy(self) -> None:
        result = calculate_discrepancy(
            "CVE-2024-0001", 0.9, 0.75, threshold=0.1, config=_DEFAULT_CONFIG
        )
        # discrepancy=0.15 > 0.1 → escalate
        assert result.should_escalate is True


class TestCalculateBatchDiscrepancies:
    def test_raises_when_config_is_none(self) -> None:
        with pytest.raises(ValueError, match="ThresholdConfig must be provided"):
            calculate_batch_discrepancies({"CVE-1": object()}, {"CVE-1": 0.5}, config=None)
