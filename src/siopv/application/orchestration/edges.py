"""Conditional edge routing for LangGraph pipeline.

Implements the Uncertainty Trigger with adaptive threshold logic
for routing between nodes based on classification confidence.

Based on specification section 3.4.
"""

from __future__ import annotations

from typing import Literal

import structlog

from siopv.application.orchestration.state import (
    DiscrepancyHistory,
    DiscrepancyResult,
    ThresholdConfig,
)
from siopv.application.orchestration.utils import check_any_escalation_needed

logger = structlog.get_logger(__name__)

# Route type for conditional edges
RouteType = Literal["escalate", "continue", "end"]


def should_escalate_route(state: dict[str, object]) -> RouteType:
    """Determine routing based on uncertainty trigger logic.

    Implements the adaptive threshold from spec section 3.4:
    - discrepancy = |ml_score - llm_confidence|
    - threshold = percentile_90(historical_discrepancies)
    - if discrepancy > threshold OR llm_confidence < 0.7 -> escalate

    Args:
        state: Current pipeline state with classifications and llm_confidence

    Returns:
        Route to take: "escalate", "continue", or "end"
    """
    classifications = state.get("classifications", {})
    llm_confidence = state.get("llm_confidence", {})

    if not classifications:
        logger.info("routing_to_end", reason="no_classifications")
        return "end"

    # Check if any CVE requires escalation
    # state.get returns object; function expects typed dicts
    needs_escalation = _check_escalation_needed(classifications, llm_confidence)  # type: ignore[arg-type]

    if needs_escalation:
        logger.info(
            "routing_to_escalate",
            reason="uncertainty_trigger_activated",
        )
        return "escalate"

    logger.info("routing_to_continue", reason="all_classifications_confident")
    return "continue"


def _check_escalation_needed(
    classifications: dict[str, object],
    llm_confidence: dict[str, object],
) -> bool:
    """Check if any CVE requires escalation based on uncertainty.

    Args:
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence

    Returns:
        True if any CVE should be escalated
    """

    # dict[str, object] → dict[str, float] narrowing at call boundary
    return check_any_escalation_needed(classifications, llm_confidence)  # type: ignore[arg-type]


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
    config = config or ThresholdConfig()
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
    config = config or ThresholdConfig()
    history = history or DiscrepancyHistory(max_size=config.history_size)

    results: list[DiscrepancyResult] = []

    # First pass: calculate all discrepancies and update history
    for cve_id, classification in classifications.items():
        # classification typed as object; is ClassificationResult at runtime
        if classification.risk_score is None:  # type: ignore[attr-defined]
            # Handle missing scores
            results.append(
                DiscrepancyResult(
                    cve_id=cve_id,
                    ml_score=0.0,
                    # dict values are object; float at runtime
                    llm_confidence=llm_confidence.get(cve_id, 0.5),  # type: ignore[arg-type]
                    discrepancy=1.0,  # Maximum uncertainty
                    should_escalate=True,
                )
            )
            continue

        # classification typed as object; is ClassificationResult at runtime
        ml_score = classification.risk_score.risk_probability  # type: ignore[attr-defined]
        confidence = llm_confidence.get(cve_id, 0.5)
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
            # Already handled above
            continue

        ml_score = classification.risk_score.risk_probability  # type: ignore[attr-defined]
        confidence = llm_confidence.get(cve_id, 0.5)

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


def route_after_classify(state: dict[str, object]) -> RouteType:
    """Route after classification node based on results.

    Simple routing logic:
    - If classifications exist, check for escalation needs
    - If errors occurred, route to end

    Args:
        state: Current pipeline state

    Returns:
        Route to take
    """
    errors = state.get("errors", [])
    classifications = state.get("classifications", {})

    if errors:
        logger.warning(
            "routing_to_end_due_to_errors",
            # state.get returns object; is list at runtime
            error_count=len(errors),  # type: ignore[arg-type]
        )
        return "end"

    if not classifications:
        logger.info("routing_to_end", reason="no_classifications")
        return "end"

    return should_escalate_route(state)


def route_after_escalate(state: dict[str, object]) -> Literal["end"]:
    """Route after escalation node.

    After escalation, the pipeline proceeds to end.
    The escalated CVEs will be picked up by the Human-in-the-Loop
    dashboard (Phase 7).

    Args:
        state: Current pipeline state

    Returns:
        Always returns "end"
    """
    # state.get returns object; is list at runtime
    escalated_count = len(state.get("escalated_cves", []))  # type: ignore[arg-type]
    logger.info(
        "routing_to_end_after_escalate",
        escalated_count=escalated_count,
    )
    return "end"


__all__ = [
    "RouteType",
    "calculate_batch_discrepancies",
    "calculate_discrepancy",
    "route_after_classify",
    "route_after_escalate",
    "should_escalate_route",
]
