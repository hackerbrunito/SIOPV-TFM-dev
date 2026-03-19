"""Discrepancy calculation between ML and LLM scores.

Implements the adaptive threshold logic from spec section 3.4:
- discrepancy = |ml_score - llm_confidence|
- threshold = percentile_90(historical_discrepancies)
- if discrepancy > threshold OR llm_confidence < 0.7 -> escalate
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.domain.constants import MAX_UNCERTAINTY
from siopv.domain.value_objects.discrepancy import (
    DiscrepancyHistory,
    DiscrepancyResult,
)

if TYPE_CHECKING:
    from siopv.domain.value_objects.discrepancy import ThresholdConfig

logger = structlog.get_logger(__name__)


def calculate_discrepancy(
    cve_id: str,
    ml_score: float,
    llm_confidence: float,
    *,
    threshold: float | None = None,
    config: ThresholdConfig | None = None,
) -> DiscrepancyResult:
    """Calculate discrepancy between ML and LLM scores for a single CVE.

    Args:
        cve_id: CVE identifier
        ml_score: ML model risk probability (0.0-1.0)
        llm_confidence: LLM confidence score (0.0-1.0)
        threshold: Optional explicit threshold (uses adaptive if None)
        config: Optional threshold configuration

    Returns:
        DiscrepancyResult with analysis
    """
    if config is None:
        msg = "ThresholdConfig must be provided — inject via DI from settings"
        raise ValueError(msg)
    effective_threshold = threshold if threshold is not None else config.base_threshold

    discrepancy = abs(ml_score - llm_confidence)

    # Determine if escalation is needed
    should_escalate = discrepancy > effective_threshold or llm_confidence < config.confidence_floor

    return DiscrepancyResult(
        cve_id=cve_id,
        ml_score=ml_score,
        llm_confidence=llm_confidence,
        discrepancy=discrepancy,
        should_escalate=should_escalate,
    )


def calculate_batch_discrepancies(
    classifications: dict[str, object],
    llm_confidence: dict[str, object],
    *,
    history: DiscrepancyHistory | None = None,
    config: ThresholdConfig | None = None,
) -> tuple[list[DiscrepancyResult], float]:
    """Calculate discrepancies for all classifications with adaptive threshold.

    Implements the full adaptive threshold logic from spec:
    - threshold = percentile_90(historical_discrepancies)

    Args:
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence
        history: Optional historical discrepancy tracker
        config: Optional threshold configuration

    Returns:
        Tuple of (list of DiscrepancyResult, adaptive_threshold)
    """
    if config is None:
        msg = "ThresholdConfig must be provided — inject via DI from settings"
        raise ValueError(msg)
    history = history or DiscrepancyHistory(
        max_size=config.history_size,
        base_threshold=config.base_threshold,
    )

    # First pass: calculate all discrepancies and update history
    for cve_id, classification in classifications.items():
        if classification.risk_score is None:  # type: ignore[attr-defined]
            continue

        ml_score = classification.risk_score.risk_probability  # type: ignore[attr-defined]
        confidence = llm_confidence.get(cve_id, config.default_confidence)
        discrepancy = abs(ml_score - confidence)

        history.add(discrepancy)

    # Calculate adaptive threshold
    adaptive_threshold = history.get_percentile(config.percentile)

    logger.debug(
        "adaptive_threshold_calculated",
        threshold=adaptive_threshold,
        history_size=len(history.values),
        percentile=config.percentile,
    )

    # Second pass: determine escalation with adaptive threshold
    final_results: list[DiscrepancyResult] = []
    for cve_id, classification in classifications.items():
        # classification typed as object; is ClassificationResult at runtime
        if classification.risk_score is None:  # type: ignore[attr-defined]
            # First-pass results for CVEs with missing risk_score
            default_conf = config.default_confidence
            final_results.append(
                DiscrepancyResult(
                    cve_id=cve_id,
                    ml_score=0.0,
                    llm_confidence=llm_confidence.get(cve_id, default_conf),  # type: ignore[arg-type]
                    discrepancy=MAX_UNCERTAINTY,
                    should_escalate=True,
                )
            )
            continue

        ml_score = classification.risk_score.risk_probability  # type: ignore[attr-defined]
        confidence = llm_confidence.get(cve_id, config.default_confidence)

        result = calculate_discrepancy(
            cve_id=cve_id,
            ml_score=ml_score,
            # dict values are object; float at runtime
            llm_confidence=confidence,  # type: ignore[arg-type]
            threshold=adaptive_threshold,
            config=config,
        )
        final_results.append(result)

    return final_results, adaptive_threshold


__all__ = [
    "calculate_batch_discrepancies",
    "calculate_discrepancy",
]
