"""Conditional edge routing for LangGraph pipeline.

Implements the Uncertainty Trigger with adaptive threshold logic
for routing between nodes based on classification confidence.

Based on specification section 3.4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import structlog

from siopv.application.orchestration.state import (
    get_classifications,
    get_errors,
    get_escalated_cves,
    get_llm_confidence,
)
from siopv.application.orchestration.utils import check_any_escalation_needed

if TYPE_CHECKING:
    from siopv.domain.value_objects.discrepancy import ThresholdConfig

logger = structlog.get_logger(__name__)

# Route type for conditional edges
RouteType = Literal["escalate", "continue", "end"]


def should_escalate_route(
    state: dict[str, object], *, config: ThresholdConfig | None = None
) -> RouteType:
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
    classifications = get_classifications(state)
    llm_confidence = get_llm_confidence(state)

    if not classifications:
        logger.info("routing_to_end", reason="no_classifications")
        return "end"

    # Check if any CVE requires escalation
    needs_escalation = check_any_escalation_needed(
        classifications,
        llm_confidence,
        config=config,
    )

    if needs_escalation:
        logger.info(
            "routing_to_escalate",
            reason="uncertainty_trigger_activated",
        )
        return "escalate"

    logger.info("routing_to_continue", reason="all_classifications_confident")
    return "continue"


def route_after_classify(
    state: dict[str, object], *, config: ThresholdConfig | None = None
) -> RouteType:
    """Route after classification node based on results.

    Simple routing logic:
    - If classifications exist, check for escalation needs
    - If errors occurred, route to end

    Args:
        state: Current pipeline state

    Returns:
        Route to take
    """
    errors = get_errors(state)
    classifications = get_classifications(state)

    if errors:
        logger.warning(
            "routing_to_end_due_to_errors",
            error_count=len(errors),
        )
        return "end"

    if not classifications:
        logger.info("routing_to_end", reason="no_classifications")
        return "end"

    return should_escalate_route(state, config=config)


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
    escalated_count = len(get_escalated_cves(state))
    logger.info(
        "routing_to_end_after_escalate",
        escalated_count=escalated_count,
    )
    return "end"


__all__ = [
    "RouteType",
    "route_after_classify",
    "route_after_escalate",
    "should_escalate_route",
]
