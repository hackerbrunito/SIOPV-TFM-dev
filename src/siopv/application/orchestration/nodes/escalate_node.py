"""Escalate node for LangGraph pipeline.

Handles escalation of uncertain classifications to human review.
Phase 4 logic (candidate identification) + Phase 7 HITL flagging.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from siopv.application.orchestration.state import (
    get_classifications,
    get_escalated_cves,
    get_llm_confidence,
)
from siopv.application.orchestration.utils import calculate_escalation_candidates

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.use_cases.classify_risk import ClassificationResult
    from siopv.domain.value_objects.discrepancy import ThresholdConfig

logger = structlog.get_logger(__name__)


def _calculate_escalation_level(
    escalation_timestamp: str,
    *,
    level_thresholds: tuple[tuple[int, int], ...] | None = None,
) -> int:
    """Calculate escalation level based on elapsed time since escalation.

    Escalation tiers:
    - 0: <4h elapsed (no escalation)
    - 1: >4h elapsed (analyst notified)
    - 2: >8h elapsed (lead escalated)
    - 3: >24h elapsed (auto-approved)

    Args:
        escalation_timestamp: ISO 8601 timestamp when escalation was triggered
        level_thresholds: Tuple of (hours, level) pairs sorted descending.
            Injected from ``EscalationConfig.level_thresholds``.

    Returns:
        Escalation level integer (0-3)

    Raises:
        ValueError: If level_thresholds is None (must be injected via DI).
    """
    if level_thresholds is None:
        msg = "level_thresholds must be provided (injected via EscalationConfig)"
        raise ValueError(msg)

    escalation_time = datetime.fromisoformat(escalation_timestamp)
    now = datetime.now(UTC)
    elapsed_hours = (now - escalation_time).total_seconds() / 3600

    for threshold_hours, level in level_thresholds:
        if elapsed_hours > threshold_hours:
            return level

    return 0


def escalate_node(
    state: PipelineState,
    *,
    level_thresholds: tuple[tuple[int, int], ...] | None = None,
    review_deadline_hours: float | None = None,
    threshold_config: ThresholdConfig | None = None,
) -> dict[str, object]:
    """Execute escalation phase — flag uncertain CVEs for human review.

    This node identifies CVEs that require human review due to:
    - High discrepancy between ML and LLM scores
    - Low LLM confidence
    - Adaptive threshold exceeded

    Flagged CVEs are tagged in the state (``escalated_cves`` list).
    The pipeline continues without interruption — the output node adds
    a NEEDS-HUMAN-REVIEW label to Jira tickets for flagged CVEs.

    Args:
        state: Current pipeline state with classifications and llm_confidence
        level_thresholds: Escalation level thresholds from EscalationConfig.
        review_deadline_hours: Hours until review deadline from EscalationConfig.
        threshold_config: Threshold configuration for discrepancy calculations.

    Returns:
        State updates with escalation fields populated

    Raises:
        ValueError: If review_deadline_hours is None when escalation is needed.
    """
    logger.info(
        "escalate_node_started",
        thread_id=state.get("thread_id"),
        classification_count=len(get_classifications(state)),
    )

    classifications = get_classifications(state)
    llm_confidence = get_llm_confidence(state)

    if not classifications:
        logger.warning("escalate_node_skipped", reason="no_classifications")
        return {
            "escalated_cves": [],
            "escalation_required": False,
            "current_node": "escalate",
        }

    try:
        # Identify CVEs requiring escalation (idempotent — safe before interrupt)
        escalated = _identify_escalation_candidates(
            classifications,
            llm_confidence,
            config=threshold_config,
        )
    except Exception:
        logger.exception("escalate_node_failed")
        return {
            "escalated_cves": [],
            "escalation_required": False,
            "errors": ["Escalation analysis failed — see server logs for details"],
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

    # --- Candidates found: tag for review and continue (no interrupt) ---
    now = datetime.now(UTC)
    escalation_timestamp = now.isoformat()
    review_deadline = (
        (now + timedelta(hours=review_deadline_hours)).isoformat()
        if review_deadline_hours is not None
        else None
    )

    escalation_level = _calculate_escalation_level(
        escalation_timestamp, level_thresholds=level_thresholds
    )

    logger.info(
        "escalate_node_flagged_for_review",
        escalated_count=len(escalated),
        total_classifications=len(classifications),
        escalation_rate=f"{len(escalated) / len(classifications) * 100:.1f}%",
        escalation_level=escalation_level,
    )

    # Pipeline continues — flagged CVEs get a NEEDS-HUMAN-REVIEW label
    # in the output node (Jira tickets, PDF report).
    # No interrupt() — the CI/CD pipeline is never blocked.
    return {
        "escalated_cves": escalated,
        "escalation_required": True,
        "escalation_timestamp": escalation_timestamp,
        "review_deadline": review_deadline,
        "human_decision": None,
        "human_modified_score": None,
        "human_modified_recommendation": None,
        "escalation_level": escalation_level,
        "current_node": "escalate",
    }


def _identify_escalation_candidates(
    classifications: dict[str, ClassificationResult],
    llm_confidence: dict[str, float],
    *,
    config: ThresholdConfig | None = None,
) -> list[str]:
    """Identify CVEs that should be escalated to human review.

    Escalation criteria (from spec section 3.4):
    - LLM confidence < 0.7 (confidence floor)
    - High discrepancy between ML and LLM scores

    Args:
        classifications: Dictionary mapping CVE ID to ClassificationResult
        llm_confidence: Dictionary mapping CVE ID to LLM confidence
        config: Threshold configuration for discrepancy calculations.

    Returns:
        List of CVE IDs requiring escalation
    """
    escalated, _ = calculate_escalation_candidates(classifications, llm_confidence, config=config)
    return escalated


def _build_escalation_summary(
    escalated: list[str],
    classifications: dict[str, ClassificationResult],
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
            classification.risk_score.risk_probability
            if classification and classification.risk_score
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
    """Extract and summarize escalation data from pipeline state.

    Utility for extracting escalation summary from pipeline state — used by tests
    and available for dashboard integration. The Streamlit dashboard currently reads
    raw checkpoint state directly, but this function provides a structured alternative.

    Args:
        state: Pipeline state with escalation data

    Returns:
        Summary dictionary with escalation details
    """
    escalated_cves = get_escalated_cves(state)
    classifications = get_classifications(state)
    llm_confidence = get_llm_confidence(state)

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
    escalated_details.sort(
        key=lambda x: x["discrepancy"] if x["discrepancy"] is not None else 0,  # type: ignore[arg-type,return-value]
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
