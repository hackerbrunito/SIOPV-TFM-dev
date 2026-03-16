"""Conditional edge routing for LangGraph pipeline.

Implements the Uncertainty Trigger with adaptive threshold logic
for routing between nodes based on classification confidence.

Based on specification section 3.4.
"""

from __future__ import annotations

from typing import Literal

import structlog

from siopv.application.orchestration.utils import check_any_escalation_needed
from siopv.domain.services.discrepancy import (
    calculate_batch_discrepancies,
    calculate_discrepancy,
)

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
