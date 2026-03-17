"""Escalate node for LangGraph pipeline.

Handles escalation of uncertain classifications to human review.
Phase 4 logic (candidate identification) + Phase 7 HITL interrupt.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog
from langgraph.types import interrupt

from siopv.application.orchestration.utils import calculate_escalation_candidates

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState

logger = structlog.get_logger(__name__)

# Escalation timeout thresholds (hours → level)
_ESCALATION_LEVEL_THRESHOLDS: list[tuple[int, int]] = [
    (24, 3),  # >24h → auto-approved
    (8, 2),  # >8h  → lead escalated
    (4, 1),  # >4h  → analyst notified
]


def _calculate_escalation_level(escalation_timestamp: str) -> int:
    """Calculate escalation level based on elapsed time since escalation.

    Escalation tiers:
    - 0: <4h elapsed (no escalation)
    - 1: >4h elapsed (analyst notified)
    - 2: >8h elapsed (lead escalated)
    - 3: >24h elapsed (auto-approved)

    Args:
        escalation_timestamp: ISO 8601 timestamp when escalation was triggered

    Returns:
        Escalation level integer (0-3)
    """
    escalation_time = datetime.fromisoformat(escalation_timestamp)
    now = datetime.now(UTC)
    elapsed_hours = (now - escalation_time).total_seconds() / 3600

    for threshold_hours, level in _ESCALATION_LEVEL_THRESHOLDS:
        if elapsed_hours > threshold_hours:
            return level

    return 0


def escalate_node(state: PipelineState) -> dict[str, object]:
    """Execute escalation phase as a LangGraph node with HITL interrupt.

    This node handles CVEs that require human review due to:
    - High discrepancy between ML and LLM scores
    - Low LLM confidence
    - Adaptive threshold exceeded

    When candidates are found, ``interrupt()`` pauses execution until a human
    submits a decision via the Streamlit dashboard.  On resume the node
    re-executes from the top (pre-interrupt logic is idempotent).

    Args:
        state: Current pipeline state with classifications and llm_confidence

    Returns:
        State updates with escalation fields populated
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
            "escalation_required": False,
            "current_node": "escalate",
        }

    try:
        # Identify CVEs requiring escalation (idempotent — safe before interrupt)
        escalated = _identify_escalation_candidates(classifications, llm_confidence)  # type: ignore[arg-type]
    except Exception as e:
        error_msg = f"Escalation failed: {e}"
        logger.exception("escalate_node_failed", error=error_msg, exception=str(e))
        return {
            "escalated_cves": [],
            "escalation_required": False,
            "errors": [error_msg],
            "current_node": "escalate",
        }

    if not escalated:
        logger.info(
            "escalate_node_complete",
            escalated_count=0,
            total_classifications=len(classifications),
        )
        return {
            "escalated_cves": [],
            "escalation_required": False,
            "current_node": "escalate",
        }

    # --- Candidates found: prepare escalation data and interrupt ---
    now = datetime.now(UTC)
    escalation_timestamp = now.isoformat()
    review_deadline = (now + timedelta(hours=24)).isoformat()

    # Build interrupt payload (must be JSON-serializable)
    escalation_data: dict[str, object] = {
        "escalated_cves": escalated,
        "escalation_timestamp": escalation_timestamp,
        "review_deadline": review_deadline,
        "summary": _build_escalation_summary(escalated, classifications, llm_confidence),  # type: ignore[arg-type]
    }

    logger.info(
        "escalate_node_interrupting",
        escalated_count=len(escalated),
        total_classifications=len(classifications),
        escalation_rate=f"{len(escalated) / len(classifications) * 100:.1f}%",
    )

    # Pause execution — human resumes via dashboard
    # NEVER wrap interrupt() in try/except; it uses internal exceptions
    human_response = interrupt(escalation_data)

    # --- Post-interrupt: process human decision ---
    decision = (
        human_response.get("decision", "approve") if isinstance(human_response, dict) else "approve"
    )
    modified_score = (
        human_response.get("modified_score") if isinstance(human_response, dict) else None
    )
    modified_recommendation = (
        human_response.get("modified_recommendation") if isinstance(human_response, dict) else None
    )

    escalation_level = _calculate_escalation_level(escalation_timestamp)

    logger.info(
        "escalate_node_complete",
        escalated_count=len(escalated),
        human_decision=decision,
        escalation_level=escalation_level,
        total_classifications=len(classifications),
    )

    return {
        "escalated_cves": escalated,
        "escalation_required": True,
        "escalation_timestamp": escalation_timestamp,
        "review_deadline": review_deadline,
        "human_decision": decision,
        "human_modified_score": modified_score,
        "human_modified_recommendation": modified_recommendation,
        "escalation_level": escalation_level,
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


def _build_escalation_summary(
    escalated: list[str],
    classifications: dict[str, object],
    llm_confidence: dict[str, float],
) -> list[dict[str, object]]:
    """Build a JSON-serializable summary of escalated CVEs for the interrupt payload.

    Args:
        escalated: List of escalated CVE IDs
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence

    Returns:
        List of summary dicts for each escalated CVE
    """
    summaries: list[dict[str, object]] = []
    for cve_id in escalated:
        classification = classifications.get(cve_id)
        confidence = llm_confidence.get(cve_id, 0.0)
        ml_score = (
            classification.risk_score.risk_probability  # type: ignore[attr-defined]
            if classification and classification.risk_score  # type: ignore[attr-defined]
            else 0.0
        )
        summaries.append(
            {
                "cve_id": cve_id,
                "ml_score": ml_score,
                "llm_confidence": confidence,
                "discrepancy": abs(ml_score - confidence),
            }
        )
    return summaries


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
