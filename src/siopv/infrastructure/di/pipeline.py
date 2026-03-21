"""Pipeline port assembly for SIOPV.

Centralizes the construction of ``PipelinePorts`` from application settings,
shared by the CLI ``process_report`` command and the pipeline monitor dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from siopv.infrastructure.config.settings import Settings

from siopv.application.orchestration.graph import PipelinePorts
from siopv.infrastructure.di.enrichment import (
    build_epss_client,
    build_github_client,
    build_llm_analysis,
    build_nvd_client,
    build_osint_client,
    build_vector_store,
)
from siopv.infrastructure.di.ml import build_classifier, build_trivy_parser
from siopv.infrastructure.di.orchestration import (
    build_escalation_config,
    build_threshold_config,
)
from siopv.infrastructure.di.output import (
    build_jira_adapter,
    build_metrics_exporter,
    build_pdf_adapter,
)

logger = structlog.get_logger(__name__)


def build_pipeline_ports(
    settings: Settings,
    *,
    batch_size: int | None = None,
    output_dir: Path | None = None,
) -> PipelinePorts:
    """Build all pipeline ports from application settings.

    Constructs the full ``PipelinePorts`` bundle needed to run the SIOPV
    pipeline graph.  Output adapters (Jira, PDF, metrics) degrade gracefully
    — if their configuration is missing, the port is set to ``None`` and
    the pipeline skips that output channel.

    Args:
        settings: Application settings instance.
        batch_size: Optional batch size override for enrichment concurrency.
        output_dir: Optional output directory override for report artifacts.

    Returns:
        Fully wired ``PipelinePorts`` ready for graph compilation.
    """
    from siopv.infrastructure.di.authorization import get_authorization_port  # noqa: PLC0415
    from siopv.infrastructure.di.dlp import get_dual_layer_dlp_port  # noqa: PLC0415

    jira_port = _build_optional(build_jira_adapter, settings, "jira_adapter")
    pdf_port = _build_optional(build_pdf_adapter, settings, "pdf_adapter")
    metrics_port = _build_optional(build_metrics_exporter, settings, "metrics_exporter")

    return PipelinePorts(
        checkpoint_db_path=settings.checkpoint_db_path,
        trivy_parser=build_trivy_parser(),
        authorization_port=get_authorization_port(),
        dlp_port=get_dual_layer_dlp_port(),
        nvd_client=build_nvd_client(settings),
        epss_client=build_epss_client(settings),
        github_client=build_github_client(settings),
        osint_client=build_osint_client(settings),
        vector_store=build_vector_store(settings),
        classifier=build_classifier(settings),
        llm_analysis=build_llm_analysis(settings),
        jira=jira_port,
        pdf=pdf_port,
        metrics=metrics_port,
        threshold_config=build_threshold_config(settings),
        escalation_config=build_escalation_config(settings),
        batch_size=batch_size,
        output_dir=output_dir or settings.output_dir,
    )


def _build_optional(factory: Any, settings: Settings, name: str) -> Any:
    """Attempt to build an optional port, returning None on failure."""
    try:
        return factory(settings)
    except Exception as exc:
        logger.warning(f"{name}_unavailable", error=str(exc))
        return None
