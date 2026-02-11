"""Classify node for LangGraph pipeline.

Handles Phase 3: ML-based risk classification with XAI explanations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.application.use_cases.classify_risk import (
    ClassificationResult,
    ClassifyRiskUseCase,
)
from siopv.domain.value_objects.risk_score import RiskScore

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.ports.ml_classifier import MLClassifierPort
    from siopv.domain.value_objects import EnrichmentData

logger = structlog.get_logger(__name__)


def classify_node(
    state: PipelineState,
    *,
    classifier: MLClassifierPort | None = None,
) -> dict[str, object]:
    """Execute classification phase as a LangGraph node.

    This node wraps the ClassifyRiskUseCase to integrate with
    the LangGraph orchestration pipeline.

    Args:
        state: Current pipeline state with vulnerabilities and enrichments
        classifier: ML classifier implementation (optional, uses mock if None)

    Returns:
        State updates with classifications dict and llm_confidence
    """
    logger.info(
        "classify_node_started",
        thread_id=state.get("thread_id"),
        vulnerability_count=len(state.get("vulnerabilities", [])),
        enrichment_count=len(state.get("enrichments", {})),
    )

    vulnerabilities = state.get("vulnerabilities", [])
    enrichments = state.get("enrichments", {})

    if not vulnerabilities:
        logger.warning("classify_node_skipped", reason="no_vulnerabilities")
        return {
            "classifications": {},
            "llm_confidence": {},
            "current_node": "classify",
        }

    try:
        # If no classifier provided, use mock classifications
        if classifier is None:
            logger.warning(
                "classify_node_using_mock",
                reason="no_classifier_provided",
            )
            # state.get returns object; narrowed types at runtime
            classifications, llm_confidence = _create_mock_classifications(
                vulnerabilities,  # type: ignore[arg-type]
                enrichments,  # type: ignore[arg-type]
            )
        else:
            # state.get returns object; narrowed types at runtime
            classifications, llm_confidence = _run_classification(
                vulnerabilities=vulnerabilities,  # type: ignore[arg-type]
                enrichments=enrichments,  # type: ignore[arg-type]
                classifier=classifier,
            )

        logger.info(
            "classify_node_complete",
            classified_count=len(classifications),
            total_vulnerabilities=len(vulnerabilities),
        )

    except Exception as e:
        error_msg = f"Classification failed: {e}"
        logger.exception("classify_node_failed", error=error_msg, exception=str(e))
        return {
            "classifications": {},
            "llm_confidence": {},
            "errors": [error_msg],
            "current_node": "classify",
        }
    else:
        return {
            "classifications": classifications,
            "llm_confidence": llm_confidence,
            "current_node": "classify",
        }


def _run_classification(
    vulnerabilities: list[object],
    enrichments: dict[str, object],
    classifier: MLClassifierPort,
) -> tuple[dict[str, object], dict[str, object]]:
    """Run classification using ClassifyRiskUseCase.

    Args:
        vulnerabilities: List of VulnerabilityRecord to classify
        enrichments: Dictionary mapping CVE ID to EnrichmentData
        classifier: ML classifier implementation

    Returns:
        Tuple of (classifications dict, llm_confidence dict)
    """

    use_case = ClassifyRiskUseCase(classifier=classifier)

    # list[object]/dict[str, object] are typed lists/dicts at runtime
    result = use_case.execute_batch(vulnerabilities, enrichments)  # type: ignore[arg-type]

    # Convert results to dictionaries
    classifications: dict[str, ClassificationResult] = {}
    llm_confidence: dict[str, float] = {}

    for classification_result in result.results:
        cve_id = classification_result.cve_id
        classifications[cve_id] = classification_result

        # Extract LLM confidence from risk score
        # For now, use ML probability as proxy for LLM confidence
        # In production, this would come from actual LLM evaluation
        if classification_result.risk_score is not None:
            llm_confidence[cve_id] = _estimate_llm_confidence(
                classification_result,
                # enrichments values are object; EnrichmentData at runtime
                enrichments.get(cve_id),  # type: ignore[arg-type]
            )

    # typed dicts narrower than tuple[dict[str, object], ...] return type
    return classifications, llm_confidence  # type: ignore[return-value]


def _estimate_llm_confidence(
    classification: ClassificationResult,
    enrichment: EnrichmentData | None,
) -> float:
    """Estimate LLM confidence based on classification and enrichment.

    In production, this would be replaced by actual LLM evaluation.
    For now, we estimate based on:
    - Risk score confidence
    - Enrichment relevance score
    - Feature availability

    Args:
        classification: ClassificationResult from ML model
        enrichment: EnrichmentData from enrichment phase

    Returns:
        Estimated LLM confidence (0.0-1.0)
    """

    if classification.risk_score is None:
        return 0.5  # Default uncertainty

    base_confidence = 0.7  # Base confidence when we have a valid score

    # Adjust based on risk probability extremeness
    # More extreme scores (close to 0 or 1) indicate higher confidence
    risk_prob = classification.risk_score.risk_probability
    extremeness = abs(risk_prob - 0.5) * 2  # 0 to 1 scale
    confidence_boost = extremeness * 0.2  # Up to 0.2 boost

    # Adjust based on enrichment relevance if available
    relevance_boost = 0.0
    if enrichment is not None:
        relevance_boost = enrichment.relevance_score * 0.1  # Up to 0.1 boost

    confidence = min(1.0, base_confidence + confidence_boost + relevance_boost)

    return round(confidence, 3)


def _create_mock_classifications(
    vulnerabilities: list[object],
    _enrichments: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Create mock classifications when classifier is unavailable.

    This provides basic classification structure for testing or
    when ML model is not configured.

    Args:
        vulnerabilities: List of VulnerabilityRecord
        _enrichments: Dictionary of enrichments (unused in mock)

    Returns:
        Tuple of (mock classifications dict, mock llm_confidence dict)
    """
    classifications: dict[str, ClassificationResult] = {}
    llm_confidence: dict[str, float] = {}

    for vuln in vulnerabilities:
        # vuln typed as object; is VulnerabilityRecord at runtime
        cve_id = vuln.cve_id.value  # type: ignore[attr-defined]

        # Estimate risk based on severity
        severity_risk_map = {
            "CRITICAL": 0.9,
            "HIGH": 0.7,
            "MEDIUM": 0.5,
            "LOW": 0.3,
            "UNKNOWN": 0.4,
        }
        # vuln typed as object; VulnerabilityRecord has severity at runtime
        risk_probability = severity_risk_map.get(vuln.severity, 0.4)  # type: ignore[attr-defined]

        # Create mock risk score using factory method
        mock_risk_score = RiskScore.from_prediction(
            cve_id=cve_id,
            probability=risk_probability,
        )

        classifications[cve_id] = ClassificationResult(
            cve_id=cve_id,
            risk_score=mock_risk_score,
        )

        # Mock LLM confidence based on severity certainty
        llm_confidence[cve_id] = 0.6 + (risk_probability * 0.3)

    # typed dicts narrower than tuple[dict[str, object], ...] return type
    return classifications, llm_confidence  # type: ignore[return-value]


__all__ = [
    "classify_node",
]
