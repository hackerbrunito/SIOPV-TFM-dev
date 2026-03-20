"""Classify node for LangGraph pipeline.

Handles Phase 3: ML-based risk classification with XAI explanations.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from siopv.application.use_cases.classify_risk import (
    ClassificationResult,
    ClassifyRiskUseCase,
)
from siopv.domain.value_objects.risk_score import RiskScore

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.ports.llm_analysis import LLMAnalysisPort
    from siopv.application.ports.ml_classifier import MLClassifierPort
    from siopv.domain.value_objects import EnrichmentData

logger = structlog.get_logger(__name__)


async def classify_node(
    state: PipelineState,
    *,
    classifier: MLClassifierPort | None = None,
    llm_analysis: LLMAnalysisPort | None = None,
) -> dict[str, object]:
    """Execute classification phase as a LangGraph node.

    This node wraps the ClassifyRiskUseCase to integrate with
    the LangGraph orchestration pipeline.

    Args:
        state: Current pipeline state with vulnerabilities and enrichments
        classifier: ML classifier implementation (optional, uses mock if None)
        llm_analysis: LLM analysis port for real confidence evaluation (optional)

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
            classifications, llm_confidence = await _run_classification(
                vulnerabilities=vulnerabilities,  # type: ignore[arg-type]
                enrichments=enrichments,  # type: ignore[arg-type]
                classifier=classifier,
                llm_analysis=llm_analysis,
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


async def _run_classification(
    vulnerabilities: list[object],
    enrichments: dict[str, object],
    classifier: MLClassifierPort,
    llm_analysis: LLMAnalysisPort | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Run classification using ClassifyRiskUseCase.

    Args:
        vulnerabilities: List of VulnerabilityRecord to classify
        enrichments: Dictionary mapping CVE ID to EnrichmentData
        classifier: ML classifier implementation
        llm_analysis: LLM analysis port for real confidence evaluation (optional)

    Returns:
        Tuple of (classifications dict, llm_confidence dict)
    """

    use_case = ClassifyRiskUseCase(classifier=classifier)

    # list[object]/dict[str, object] are typed lists/dicts at runtime
    result = use_case.execute_batch(vulnerabilities, enrichments)  # type: ignore[arg-type]

    # Convert results to dictionaries
    classifications: dict[str, ClassificationResult] = {}
    llm_confidence: dict[str, float] = {}

    # First pass: collect all classifications
    for classification_result in result.results:
        cve_id = classification_result.cve_id
        classifications[cve_id] = classification_result

    # Second pass: evaluate LLM confidence with bounded concurrency
    # Limits parallel API calls to avoid Anthropic rate limits and timeouts
    _LLM_CONCURRENCY = 5  # noqa: N806

    if llm_analysis is not None:
        semaphore = asyncio.Semaphore(_LLM_CONCURRENCY)

        async def _evaluate_one(cve_id: str, cr: ClassificationResult) -> tuple[str, float]:
            async with semaphore:
                assert cr.risk_score is not None  # guaranteed by caller filter
                classification_dict = {
                    "cve_id": cve_id,
                    "risk_probability": cr.risk_score.risk_probability,
                    "risk_label": cr.risk_score.risk_label,
                }
                enrichment_dict = {}
                enrichment_obj = enrichments.get(cve_id)
                if enrichment_obj is not None:
                    enrichment_dict = {
                        "cve_id": enrichment_obj.cve_id,  # type: ignore[attr-defined]
                        "relevance_score": enrichment_obj.relevance_score,  # type: ignore[attr-defined]
                    }
                try:
                    conf = await llm_analysis.evaluate_confidence(
                        cve_id,
                        classification_dict,
                        enrichment_dict,
                    )
                except Exception as exc:
                    logger.warning(
                        "llm_confidence_fallback",
                        cve_id=cve_id,
                        error=str(exc),
                    )
                    fallback = _estimate_llm_confidence_fallback(
                        cr,
                        enrichments.get(cve_id),  # type: ignore[arg-type]
                    )
                    return cve_id, fallback
                else:
                    logger.info(
                        "llm_confidence_evaluated",
                        cve_id=cve_id,
                        confidence=conf,
                    )
                    return cve_id, conf

        # Build tasks for CVEs that have risk scores
        tasks = [
            _evaluate_one(cve_id, cr)
            for cve_id, cr in classifications.items()
            if cr.risk_score is not None
        ]

        # Run all LLM evaluations with bounded concurrency
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result_item in results:
                if isinstance(result_item, tuple):
                    cve_id, conf = result_item
                    llm_confidence[cve_id] = conf
                # Exceptions already logged in _evaluate_one

    # Heuristic fallback for CVEs without LLM evaluation
    for cve_id, cr in classifications.items():
        if cve_id not in llm_confidence:
            llm_confidence[cve_id] = _estimate_llm_confidence_fallback(
                cr,
                enrichments.get(cve_id),  # type: ignore[arg-type]
            )

    # typed dicts narrower than tuple[dict[str, object], ...] return type
    return classifications, llm_confidence  # type: ignore[return-value]


def _estimate_llm_confidence_fallback(
    classification: ClassificationResult,
    enrichment: EnrichmentData | None,
) -> float:
    """Estimate LLM confidence using heuristics when no LLM is configured.

    Uses ML classification probability extremeness and enrichment relevance
    as proxy signals for confidence.

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

        # Heuristic confidence estimate (used when LLM and classifier are unavailable)
        llm_confidence[cve_id] = 0.6 + (risk_probability * 0.3)

    # typed dicts narrower than tuple[dict[str, object], ...] return type
    return classifications, llm_confidence  # type: ignore[return-value]


__all__ = [
    "classify_node",
]
