"""Pipeline State schema for LangGraph orchestration.

Defines the TypedDict state schema for the SIOPV vulnerability processing
pipeline. LangGraph requires TypedDict (not Pydantic BaseModel) for state.

Based on specification section 3.4.
"""

from __future__ import annotations

import operator
import uuid
from typing import Annotated, TypedDict

from siopv.application.use_cases.classify_risk import ClassificationResult
from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.services.discrepancy_types import (
    DiscrepancyHistory,
    DiscrepancyResult,
    ThresholdConfig,
)
from siopv.domain.value_objects import EnrichmentData


class PipelineState(TypedDict, total=False):
    """LangGraph state schema for the SIOPV pipeline.

    Uses TypedDict as required by LangGraph StateGraph.
    Fields marked with Annotated[..., operator.add] are append-only.

    Attributes:
        user_id: User identifier for authorization (Phase 5)
        project_id: Project identifier for authorization context (Phase 5)
        authorization_allowed: Whether user is authorized to proceed (Phase 5)
        authorization_skipped: Whether authorization was skipped (Phase 5)
        authorization_result: Detailed authorization result (Phase 5)
        vulnerabilities: List of parsed VulnerabilityRecord from Phase 1
        enrichments: Dict mapping CVE ID to EnrichmentData from Phase 2
        classifications: Dict mapping CVE ID to ClassificationResult from Phase 3
        escalated_cves: List of CVE IDs requiring human review
        llm_confidence: Dict mapping CVE ID to LLM confidence score (0.0-1.0)
        processed_count: Number of vulnerabilities processed
        errors: List of error messages encountered during processing
        escalation_required: Whether the current case requires human review (Phase 7)
        human_decision: Human reviewer decision: "approve", "reject", or "modify" (Phase 7)
        human_modified_score: Overridden risk score when decision is "modify" (Phase 7)
        human_modified_recommendation: Overridden recommendation when decision is "modify" (Phase 7)
        escalation_timestamp: ISO 8601 timestamp when escalation was triggered (Phase 7)
        escalation_level: Escalation tier: 0=none, 1=analyst, 2=lead, 3=auto-approved (Phase 7)
        review_deadline: ISO 8601 deadline for human review completion (Phase 7)
        report_path: Path to the input Trivy report (optional, for file-based ingestion)
        output_run_id: LangGraph thread_id set by output_node (Phase 8)
        output_jira_keys: Jira ticket keys created during output (Phase 8)
        output_pdf_path: Absolute path to generated PDF report (Phase 8)
        output_csv_path: Absolute path to generated CSV export (Phase 8)
        output_json_path: Absolute path to generated JSON export (Phase 8)
        output_errors: Non-fatal errors during output generation (Phase 8)
        thread_id: Unique identifier for this pipeline execution
        current_node: Name of the currently executing node
    """

    # Phase 5 - Authorization (executed first as gatekeeper)
    user_id: str | None
    project_id: str | None
    system_execution: bool  # Explicit flag to allow anonymous/system access
    authorization_allowed: bool
    authorization_skipped: bool
    authorization_result: dict[str, object] | None

    # Phase 1 - Ingestion
    vulnerabilities: list[VulnerabilityRecord]
    report_path: str | None

    # Phase 2 - Enrichment
    enrichments: dict[str, EnrichmentData]

    # Phase 3 - Classification
    classifications: dict[str, ClassificationResult]

    # Phase 4 - Orchestration state
    escalated_cves: Annotated[list[str], operator.add]
    llm_confidence: dict[str, float]
    processed_count: int
    errors: Annotated[list[str], operator.add]

    # Phase 6 - DLP/Privacy
    dlp_result: dict[str, object] | None

    # Phase 7 - Human-in-the-Loop
    escalation_required: bool
    human_decision: str | None  # "approve" | "reject" | "modify"
    human_modified_score: float | None
    human_modified_recommendation: str | None
    escalation_timestamp: str | None  # ISO 8601 string (JSON-serializable for LangGraph)
    escalation_level: int  # 0=none, 1=analyst notified, 2=lead escalated, 3=auto-approved
    review_deadline: str | None  # ISO 8601 string (JSON-serializable for LangGraph)

    # Phase 8 - Output
    output_run_id: str | None  # LangGraph thread_id, set by output_node
    output_jira_keys: list[str]  # Jira ticket keys created (e.g. ['SEC-123'])
    output_pdf_path: str | None  # Absolute path to generated PDF
    output_csv_path: str | None  # Absolute path to generated CSV
    output_json_path: str | None  # Absolute path to generated JSON
    output_errors: Annotated[list[str], operator.add]  # Non-fatal errors during output

    # Metadata
    thread_id: str
    current_node: str


def create_initial_state(
    *,
    report_path: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    system_execution: bool = False,
) -> PipelineState:
    """Create initial pipeline state with default values.

    Args:
        report_path: Optional path to Trivy report file
        thread_id: Optional thread ID for checkpointing
        user_id: Optional user ID for authorization (Phase 5)
        project_id: Optional project ID for authorization context (Phase 5)
        system_execution: If True, allows anonymous execution without user_id

    Returns:
        PipelineState with initialized fields
    """

    return PipelineState(
        # Phase 5 - Authorization
        user_id=user_id,
        project_id=project_id,
        system_execution=system_execution,
        authorization_allowed=False,
        authorization_skipped=False,
        authorization_result=None,
        # Phase 1 - Ingestion
        vulnerabilities=[],
        report_path=report_path,
        # Phase 2 - Enrichment
        enrichments={},
        # Phase 3 - Classification
        classifications={},
        # Phase 4 - Orchestration
        escalated_cves=[],
        llm_confidence={},
        processed_count=0,
        errors=[],
        # Phase 6 - DLP/Privacy
        dlp_result=None,
        # Phase 7 - Human-in-the-Loop
        escalation_required=False,
        human_decision=None,
        human_modified_score=None,
        human_modified_recommendation=None,
        escalation_timestamp=None,
        escalation_level=0,
        review_deadline=None,
        # Phase 8 - Output
        output_run_id=None,
        output_jira_keys=[],
        output_pdf_path=None,
        output_csv_path=None,
        output_json_path=None,
        output_errors=[],
        # Metadata
        thread_id=thread_id or str(uuid.uuid4()),
        current_node="start",
    )


__all__ = [
    "DiscrepancyHistory",
    "DiscrepancyResult",
    "PipelineState",
    "ThresholdConfig",
    "create_initial_state",
]
