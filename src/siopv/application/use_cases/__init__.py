"""Application use cases for SIOPV."""

from siopv.application.use_cases.authorization import (
    AuthorizationStats,
    BatchCheckAuthorizationUseCase,
    BatchCheckResult,
    CheckAuthorizationResult,
    CheckAuthorizationUseCase,
    ManageRelationshipsUseCase,
    RelationshipWriteResult,
    create_batch_check_authorization_use_case,
    create_check_authorization_use_case,
    create_manage_relationships_use_case,
)
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
from siopv.application.use_cases.generate_report import (
    GenerateReportUseCase,
    create_generate_report_use_case,
)
from siopv.application.use_cases.ingest_trivy import (
    IngestionResult,
    IngestionStats,
    IngestTrivyReportUseCase,
    ingest_trivy_report,
)

__all__ = [
    "AuthorizationStats",
    "BatchCheckAuthorizationUseCase",
    "BatchCheckResult",
    "BatchClassificationResult",
    "BatchEnrichmentResult",
    "CheckAuthorizationResult",
    "CheckAuthorizationUseCase",
    "ClassificationResult",
    "ClassificationStats",
    "ClassifyRiskUseCase",
    "EnrichContextUseCase",
    "EnrichmentResult",
    "EnrichmentStatsPhase2",
    "GenerateReportUseCase",
    "IngestTrivyReportUseCase",
    "IngestionResult",
    "IngestionStats",
    "ManageRelationshipsUseCase",
    "RelationshipWriteResult",
    "create_batch_check_authorization_use_case",
    "create_check_authorization_use_case",
    "create_classify_risk_use_case",
    "create_enrich_context_use_case",
    "create_generate_report_use_case",
    "create_manage_relationships_use_case",
    "ingest_trivy_report",
]
