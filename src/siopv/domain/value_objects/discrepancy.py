"""Value objects for discrepancy calculation between ML and LLM scores.

These types support the adaptive threshold logic from spec section 3.4.
Moved from application/orchestration/state.py to domain layer
because they are pure data with no application dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiscrepancyResult:
    """Result of discrepancy calculation between ML and LLM scores.

    Attributes:
        cve_id: CVE identifier
        ml_score: ML model risk probability (0.0-1.0)
        llm_confidence: LLM confidence score (0.0-1.0)
        discrepancy: Absolute difference |ml_score - llm_confidence|
        should_escalate: Whether this CVE should be escalated to human review
    """

    cve_id: str
    ml_score: float
    llm_confidence: float
    discrepancy: float
    should_escalate: bool


@dataclass
class ThresholdConfig:
    """Configuration for the adaptive uncertainty threshold.

    Values are injected from Settings via DI — no hardcoded defaults.

    Attributes:
        base_threshold: Base discrepancy threshold
        confidence_floor: LLM confidence below this triggers escalation
        percentile: Percentile for adaptive threshold calculation
        history_size: Number of historical discrepancies to track
        default_confidence: Fallback LLM confidence when no score available
    """

    base_threshold: float
    confidence_floor: float
    percentile: int
    history_size: int
    default_confidence: float


@dataclass
class DiscrepancyHistory:
    """Tracks historical discrepancies for adaptive threshold calculation.

    Maintains a rolling window of discrepancies from past evaluations
    to compute the adaptive percentile-based threshold.

    Args:
        max_size: Maximum history size (from ThresholdConfig)
        base_threshold: Fallback when no history exists
    """

    max_size: int
    base_threshold: float
    values: list[float] = field(default_factory=list)

    def add(self, discrepancy: float) -> None:
        """Add a discrepancy value to history.

        Args:
            discrepancy: The discrepancy value to add
        """
        self.values.append(discrepancy)
        if len(self.values) > self.max_size:
            self.values = self.values[-self.max_size :]

    def get_percentile(self, percentile: int) -> float:
        """Calculate the specified percentile of historical discrepancies.

        Args:
            percentile: The percentile to calculate (0-100)

        Returns:
            The percentile value, or base_threshold if no history
        """
        if not self.values:
            return self.base_threshold

        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


__all__ = [
    "DiscrepancyHistory",
    "DiscrepancyResult",
    "ThresholdConfig",
]
