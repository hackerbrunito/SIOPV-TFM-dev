"""Classify Risk Use Case for ML-based vulnerability classification.

Orchestrates the ML classification pipeline:
1. Extract features from enrichment data
2. Predict exploitation risk
3. Generate XAI explanations (SHAP + LIME)

Based on specification section 3.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from siopv.adapters.ml.feature_engineer import FeatureEngineer
from siopv.domain.value_objects.risk_score import RiskScore

if TYPE_CHECKING:
    from siopv.application.ports.ml_classifier import MLClassifierPort
    from siopv.domain.entities import VulnerabilityRecord
    from siopv.domain.value_objects import EnrichmentData

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ClassificationResult:
    """Result of risk classification for a single vulnerability."""

    cve_id: str
    risk_score: RiskScore | None
    error: str | None = None

    @property
    def is_successful(self) -> bool:
        """Check if classification was successful."""
        return self.risk_score is not None and self.error is None

    def to_output_tuple(self) -> tuple[float, object, object] | None:
        """Return the output tuple for LangGraph state.

        Returns:
            (risk_probability, shap_values, lime_explanation) or None on error
        """
        if self.risk_score is None:
            return None
        return self.risk_score.to_output_tuple()


@dataclass(frozen=True)
class BatchClassificationResult:
    """Result of batch risk classification."""

    results: list[ClassificationResult]
    stats: ClassificationStats


@dataclass(frozen=True)
class ClassificationStats:
    """Statistics from the classification process."""

    total_processed: int
    successful: int
    failed: int
    high_risk_count: int
    critical_count: int
    avg_risk_probability: float


class ClassifyRiskUseCase:
    """Use case for ML-based vulnerability risk classification.

    Combines feature engineering, XGBoost prediction, and XAI explanations
    to produce risk scores with interpretable justifications.

    Output for LangGraph:
        (risk_probability, shap_values, lime_explanation)
    """

    def __init__(
        self,
        classifier: MLClassifierPort,
        feature_engineer: FeatureEngineer | None = None,
    ) -> None:
        """Initialize classification use case.

        Args:
            classifier: ML classifier implementation (XGBoostClassifier)
            feature_engineer: Feature extraction component (uses default if None)
        """
        self._classifier = classifier
        self._feature_engineer = feature_engineer or FeatureEngineer()

        logger.info(
            "classify_risk_use_case_initialized",
            classifier_loaded=classifier.is_loaded(),
        )

    def execute(
        self,
        vulnerability: VulnerabilityRecord,
        enrichment: EnrichmentData,
    ) -> ClassificationResult:
        """Execute risk classification for a single vulnerability.

        Args:
            vulnerability: VulnerabilityRecord from Phase 1
            enrichment: EnrichmentData from Phase 2

        Returns:
            ClassificationResult with RiskScore and XAI explanations
        """
        cve_id = vulnerability.cve_id.value

        logger.info("classification_started", cve_id=cve_id)

        try:
            # Step 1: Extract features
            feature_vector = self._feature_engineer.extract_features(vulnerability, enrichment)

            # Step 2: Predict with XAI
            risk_score = self._classifier.predict(feature_vector)

            logger.info(
                "classification_complete",
                cve_id=cve_id,
                risk_probability=risk_score.risk_probability,
                risk_label=risk_score.risk_label,
            )

            return ClassificationResult(
                cve_id=cve_id,
                risk_score=risk_score,
            )

        except Exception as e:
            logger.error(
                "classification_failed",
                cve_id=cve_id,
                error=str(e),
            )
            return ClassificationResult(
                cve_id=cve_id,
                risk_score=None,
                error=str(e),
            )

    def execute_batch(
        self,
        vulnerabilities: list[VulnerabilityRecord],
        enrichments: dict[str, EnrichmentData],
    ) -> BatchClassificationResult:
        """Execute risk classification for multiple vulnerabilities.

        Args:
            vulnerabilities: List of VulnerabilityRecord from Phase 1
            enrichments: Dictionary mapping CVE ID to EnrichmentData

        Returns:
            BatchClassificationResult with all results and statistics
        """
        logger.info("batch_classification_started", count=len(vulnerabilities))

        results = []
        successful = 0
        failed = 0
        high_risk_count = 0
        critical_count = 0
        total_probability = 0.0

        for vuln in vulnerabilities:
            cve_id = vuln.cve_id.value
            enrichment = enrichments.get(cve_id)

            if enrichment is None:
                logger.warning("missing_enrichment_for_classification", cve_id=cve_id)
                # Create minimal enrichment
                from siopv.domain.value_objects import EnrichmentData

                enrichment = EnrichmentData(cve_id=cve_id)

            result = self.execute(vuln, enrichment)
            results.append(result)

            if result.is_successful and result.risk_score is not None:
                successful += 1
                total_probability += result.risk_score.risk_probability

                if result.risk_score.is_high_risk:
                    high_risk_count += 1
                if result.risk_score.requires_immediate_action:
                    critical_count += 1
            else:
                failed += 1

        avg_probability = total_probability / successful if successful > 0 else 0.0

        stats = ClassificationStats(
            total_processed=len(vulnerabilities),
            successful=successful,
            failed=failed,
            high_risk_count=high_risk_count,
            critical_count=critical_count,
            avg_risk_probability=avg_probability,
        )

        logger.info(
            "batch_classification_complete",
            total=stats.total_processed,
            successful=stats.successful,
            failed=stats.failed,
            high_risk=stats.high_risk_count,
            critical=stats.critical_count,
        )

        return BatchClassificationResult(results=results, stats=stats)

    def get_risk_summary(
        self,
        results: list[ClassificationResult],
    ) -> dict:
        """Generate a summary of classification results.

        Args:
            results: List of ClassificationResult

        Returns:
            Summary dictionary for reporting
        """
        successful_results = [r for r in results if r.is_successful and r.risk_score]

        if not successful_results:
            return {"status": "no_successful_classifications"}

        # Group by risk label
        by_label: dict[str, list[str]] = {}
        for result in successful_results:
            if result.risk_score:
                label = result.risk_score.risk_label
                if label not in by_label:
                    by_label[label] = []
                by_label[label].append(result.cve_id)

        # Get top risk CVEs
        top_risks = sorted(
            successful_results,
            key=lambda r: r.risk_score.risk_probability if r.risk_score else 0,
            reverse=True,
        )[:10]

        return {
            "total_classified": len(successful_results),
            "by_risk_label": {label: len(cves) for label, cves in by_label.items()},
            "top_10_risks": [
                {
                    "cve_id": r.cve_id,
                    "probability": r.risk_score.risk_probability if r.risk_score else 0,
                    "label": r.risk_score.risk_label if r.risk_score else "UNKNOWN",
                }
                for r in top_risks
            ],
        }


def create_classify_risk_use_case(
    classifier: MLClassifierPort,
    feature_engineer: FeatureEngineer | None = None,
) -> ClassifyRiskUseCase:
    """Factory function to create ClassifyRiskUseCase.

    Args:
        classifier: ML classifier implementation
        feature_engineer: Optional custom feature engineer

    Returns:
        Configured ClassifyRiskUseCase
    """
    return ClassifyRiskUseCase(
        classifier=classifier,
        feature_engineer=feature_engineer,
    )


__all__ = [
    "BatchClassificationResult",
    "ClassificationResult",
    "ClassificationStats",
    "ClassifyRiskUseCase",
    "create_classify_risk_use_case",
]
