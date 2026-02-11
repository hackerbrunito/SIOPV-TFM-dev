"""Escalate node for LangGraph pipeline.

Handles escalation of uncertain classifications to human review.
Part of Phase 4 orchestration logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.application.orchestration.utils import calculate_escalation_candidates

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState

logger = structlog.get_logger(__name__)


def escalate_node(state: PipelineState) -> dict[str, object]:
    """Execute escalation phase as a LangGraph node.

    This node handles CVEs that require human review due to:
    - High discrepancy between ML and LLM scores
    - Low LLM confidence
    - Adaptive threshold exceeded

    The escalated CVEs are stored in state for the Human-in-the-Loop
    dashboard (Phase 7) to process.

    Args:
        state: Current pipeline state with classifications and llm_confidence

    Returns:
        State updates with escalated_cves list
    """
    logger.info(
        "escalate_node_started",
        thread_id=state.get("thread_id"),
        classification_count=len(state.get("classifications", {})),
    )

    classifications = state.get("classifications", {})
    llm_confidence = state.get("llm_confidence", {})

    if not classifications:
        logger.warning("escalate_node_skipped", reason="no_classifications")
        return {
            "escalated_cves": [],
            "current_node": "escalate",
        }

    try:
        # Identify CVEs requiring escalation
        # state.get returns object; typed dicts at runtime
        escalated = _identify_escalation_candidates(classifications, llm_confidence)  # type: ignore[arg-type]

        logger.info(
            "escalate_node_complete",
            escalated_count=len(escalated),
            total_classifications=len(classifications),
            escalation_rate=f"{len(escalated) / len(classifications) * 100:.1f}%"
            if classifications
            else "0%",
        )

        # Log details for each escalated CVE
        for cve_id in escalated:
            classification = classifications.get(cve_id)
            confidence = llm_confidence.get(cve_id, 0.0)
            ml_score = (
                classification.risk_score.risk_probability
                if classification and classification.risk_score
                else 0.0
            )
            logger.info(
                "cve_escalated",
                cve_id=cve_id,
                ml_score=ml_score,
                llm_confidence=confidence,
                discrepancy=abs(ml_score - confidence),
            )

    except Exception as e:
        error_msg = f"Escalation failed: {e}"
        logger.exception("escalate_node_failed", error=error_msg, exception=str(e))
        return {
            "escalated_cves": [],
            "errors": [error_msg],
            "current_node": "escalate",
        }
    else:
        return {
            "escalated_cves": escalated,
            "current_node": "escalate",
        }


def _identify_escalation_candidates(
    classifications: dict[str, object],
    llm_confidence: dict[str, float],
) -> list[str]:
    """Identify CVEs that should be escalated to human review.

    Escalation criteria (from spec section 3.4):
    - LLM confidence < 0.7 (confidence floor)
    - High discrepancy between ML and LLM scores

    Args:
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence

    Returns:
        List of CVE IDs requiring escalation
    """

    escalated, _ = calculate_escalation_candidates(classifications, llm_confidence)
    return escalated


def get_escalation_summary(state: PipelineState) -> dict[str, object]:
    """Generate a summary of escalated CVEs for dashboard display.

    Args:
        state: Pipeline state with escalation data

    Returns:
        Summary dictionary with escalation details
    """
    escalated_cves = state.get("escalated_cves", [])
    classifications = state.get("classifications", {})
    llm_confidence = state.get("llm_confidence", {})

    escalated_details: list[dict[str, object]] = []

    for cve_id in escalated_cves:
        classification = classifications.get(cve_id)
        confidence = llm_confidence.get(cve_id, 0.0)

        detail: dict[str, object] = {
            "cve_id": cve_id,
            "llm_confidence": confidence,
            "ml_score": None,
            "risk_label": None,
            "discrepancy": None,
        }

        if classification and classification.risk_score:
            ml_score = classification.risk_score.risk_probability
            detail["ml_score"] = ml_score
            detail["risk_label"] = classification.risk_score.risk_label
            detail["discrepancy"] = abs(ml_score - confidence)

        escalated_details.append(detail)

    # Sort by discrepancy (highest first)
    # Note: type ignores needed because dict value type is `object` but we know
    # "discrepancy" is float|None at runtime. Two separate issues:
    # - arg-type: lambda signature doesn't match expected Callable
    # - return-value: returning object instead of SupportsDunderLT
    escalated_details.sort(
        # dict values typed as object; discrepancy is float|None at runtime
        key=lambda x: x["discrepancy"] if x["discrepancy"] is not None else 0,  # type: ignore[arg-type, return-value]
        reverse=True,
    )

    summary: dict[str, object] = {
        "total_escalated": len(escalated_cves),
        "total_processed": len(classifications),
        "escalation_rate": len(escalated_cves) / len(classifications) * 100
        if classifications
        else 0,
        "escalated_details": escalated_details,
    }

    return summary


__all__ = [
    "escalate_node",
    "get_escalation_summary",
]
