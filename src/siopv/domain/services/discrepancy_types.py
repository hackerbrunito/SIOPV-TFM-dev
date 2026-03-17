"""Domain types for discrepancy calculation between ML and LLM scores.

These dataclasses model the adaptive threshold logic from spec section 3.4.
Defined in the domain layer so that both domain services and application
orchestration can import them without violating hexagonal architecture.
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

    Attributes:
        base_threshold: Base discrepancy threshold (default 0.3 from spec)
        confidence_floor: LLM confidence below this triggers escalation (default 0.7)
        percentile: Percentile for adaptive threshold calculation (default 90)
        history_size: Number of historical discrepancies to track (default 500)
    """

    base_threshold: float = 0.3
    confidence_floor: float = 0.7
    percentile: int = 90
    history_size: int = 500


@dataclass
class DiscrepancyHistory:
    """Tracks historical discrepancies for adaptive threshold calculation.

    Maintains a rolling window of discrepancies from past evaluations
    to compute the adaptive percentile-based threshold.
    """

    values: list[float] = field(default_factory=list)
    max_size: int = 500

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
            The percentile value, or 0.3 (base threshold) if no history
        """
        if not self.values:
            return 0.3  # Default base threshold

        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


__all__ = [
    "DiscrepancyHistory",
    "DiscrepancyResult",
    "ThresholdConfig",
]
