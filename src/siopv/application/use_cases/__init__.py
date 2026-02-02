"""Application use cases for SIOPV."""

from siopv.application.use_cases.classify_risk import (
    BatchClassificationResult,
    ClassificationResult,
    ClassificationStats,
    ClassifyRiskUseCase,
    create_classify_risk_use_case,
)
from siopv.application.use_cases.enrich_context import (
    BatchEnrichmentResult,
    EnrichContextUseCase,
    EnrichmentResult,
    create_enrich_context_use_case,
)
from siopv.application.use_cases.enrich_context import (
    EnrichmentStats as EnrichmentStatsPhase2,
)
from siopv.application.use_cases.ingest_trivy import (
    IngestionResult,
    IngestionStats,
    IngestTrivyReportUseCase,
    ingest_trivy_report,
)

__all__ = [
    # Phase 1 - Ingestion
    "IngestTrivyReportUseCase",
    "IngestionResult",
    "IngestionStats",
    "ingest_trivy_report",
    # Phase 2 - Enrichment
    "BatchEnrichmentResult",
    "EnrichContextUseCase",
    "EnrichmentResult",
    "EnrichmentStatsPhase2",
    "create_enrich_context_use_case",
    # Phase 3 - Classification
    "BatchClassificationResult",
    "ClassificationResult",
    "ClassificationStats",
    "ClassifyRiskUseCase",
    "create_classify_risk_use_case",
]
