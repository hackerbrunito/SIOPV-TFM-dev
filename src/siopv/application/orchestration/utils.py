"""Shared utilities for LangGraph orchestration.

Provides common functions for escalation logic used by both
edges.py and escalate_node.py to avoid code duplication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.domain.value_objects.discrepancy import (
    DiscrepancyHistory,
    ThresholdConfig,
)

if TYPE_CHECKING:
    from siopv.application.use_cases.classify_risk import ClassificationResult

logger = structlog.get_logger(__name__)


def should_escalate_cve(
    *,
    ml_score: float | None,
    llm_confidence: float,
    threshold: float,
    confidence_floor: float,
) -> bool:
    """Determine if a single CVE should be escalated.

    Escalation criteria (from spec section 3.4):
    - ml_score is None (no valid classification)
    - discrepancy > threshold
    - llm_confidence < confidence_floor

    Args:
        ml_score: ML model risk probability (0.0-1.0), None if unavailable
        llm_confidence: LLM confidence score (0.0-1.0)
        threshold: Discrepancy threshold for escalation
        confidence_floor: Minimum acceptable confidence (default 0.7)

    Returns:
        True if CVE should be escalated to human review
    """
    if ml_score is None:
        return True

    # Check confidence floor
    if llm_confidence < confidence_floor:
        return True

    # Check discrepancy
    discrepancy = abs(ml_score - llm_confidence)
    return discrepancy > threshold


def _extract_ml_score(classification: ClassificationResult) -> float | None:
    """Extract ML risk probability from a ClassificationResult."""
    if classification.risk_score is None:
        return None
    return classification.risk_score.risk_probability


def calculate_escalation_candidates(
    classifications: dict[str, ClassificationResult],
    llm_confidence: dict[str, float],
    *,
    config: ThresholdConfig | None = None,
    history: DiscrepancyHistory | None = None,
) -> tuple[list[str], float]:
    """Calculate which CVEs should be escalated based on uncertainty.

    Implements the adaptive threshold logic from spec section 3.4:
    - threshold = percentile_90(historical_discrepancies)
    - if discrepancy > threshold OR llm_confidence < 0.7 -> escalate

    Args:
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence
        config: Optional threshold configuration
        history: Optional historical discrepancy tracker

    Returns:
        Tuple of (list of CVE IDs to escalate, adaptive_threshold)
    """
    if config is None:
        msg = "ThresholdConfig must be provided — inject via DI from settings"
        raise ValueError(msg)
    history = history or DiscrepancyHistory(
        max_size=config.history_size,
        base_threshold=config.base_threshold,
    )

    # First pass: calculate all discrepancies and populate history
    discrepancies: dict[str, float] = {}
    for cve_id, classification in classifications.items():
        ml_score = _extract_ml_score(classification)
        if ml_score is None:
            continue

        confidence = llm_confidence.get(cve_id, config.default_confidence)
        discrepancy = abs(ml_score - confidence)

        discrepancies[cve_id] = discrepancy
        history.add(discrepancy)

    # Calculate adaptive threshold
    adaptive_threshold = history.get_percentile(config.percentile)

    logger.debug(
        "escalation_threshold_calculated",
        adaptive_threshold=adaptive_threshold,
        base_threshold=config.base_threshold,
        confidence_floor=config.confidence_floor,
        history_size=len(history.values),
    )

    # Second pass: identify escalation candidates
    escalated: list[str] = []
    for cve_id, classification in classifications.items():
        ml_score = _extract_ml_score(classification)
        confidence = llm_confidence.get(cve_id, config.default_confidence)

        if should_escalate_cve(
            ml_score=ml_score,
            llm_confidence=confidence,
            threshold=adaptive_threshold,
            confidence_floor=config.confidence_floor,
        ):
            escalated.append(cve_id)

    return escalated, adaptive_threshold


def check_any_escalation_needed(
    classifications: dict[str, ClassificationResult],
    llm_confidence: dict[str, float],
    *,
    config: ThresholdConfig | None = None,
) -> bool:
    """Check if any CVE in the batch requires escalation.

    This is a quick check for routing decisions, using base threshold
    without history tracking for efficiency.

    Args:
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence
        config: Optional threshold configuration

    Returns:
        True if any CVE should be escalated
    """
    if config is None:
        msg = "ThresholdConfig must be provided — inject via DI from settings"
        raise ValueError(msg)

    for cve_id, classification in classifications.items():
        ml_score = _extract_ml_score(classification)
        confidence = llm_confidence.get(cve_id, config.default_confidence)

        if should_escalate_cve(
            ml_score=ml_score,
            llm_confidence=confidence,
            threshold=config.base_threshold,
            confidence_floor=config.confidence_floor,
        ):
            return True

    return False


__all__ = [
    "calculate_escalation_candidates",
    "check_any_escalation_needed",
    "should_escalate_cve",
]
