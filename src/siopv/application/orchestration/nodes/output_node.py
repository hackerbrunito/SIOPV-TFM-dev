"""Output node for LangGraph pipeline.

Handles Phase 8: Report generation across Jira, PDF, and metrics channels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.ports.jira_client import JiraClientPort
    from siopv.application.ports.metrics_exporter import MetricsExporterPort
    from siopv.application.ports.pdf_generator import PdfGeneratorPort

logger = structlog.get_logger(__name__)


async def output_node(
    state: PipelineState,
    *,
    jira: JiraClientPort | None = None,
    pdf: PdfGeneratorPort | None = None,
    metrics: MetricsExporterPort | None = None,
) -> dict[str, Any]:
    """Execute output phase as a LangGraph node.

    This node wraps the GenerateReportUseCase to produce Jira tickets,
    PDF reports, and CSV/JSON metric exports from pipeline results.

    Args:
        state: Current pipeline state with all phase results
        jira: Jira client port for ticket creation
        pdf: PDF generator port for report rendering
        metrics: Metrics exporter port for JSON/CSV output

    Returns:
        State updates with output fields (jira keys, paths, errors)
    """
    logger.info(
        "output_node_started",
        thread_id=state.get("thread_id"),
        vulnerability_count=len(state.get("vulnerabilities", [])),
    )

    try:
        if any(port is None for port in [jira, pdf, metrics]):
            logger.warning(
                "output_node_skipped",
                reason="missing_output_ports",
            )
            return {
                "output_run_id": state.get("thread_id"),
                "output_jira_keys": [],
                "output_pdf_path": None,
                "output_csv_path": None,
                "output_json_path": None,
                "output_errors": ["Output skipped: one or more output ports not configured"],
                "current_node": "output",
            }

        from siopv.application.use_cases.generate_report import (  # noqa: PLC0415
            GenerateReportUseCase,
        )

        # Ports checked non-None above; mypy can't narrow after guard
        use_case = GenerateReportUseCase(
            jira=jira,  # type: ignore[arg-type]
            pdf=pdf,  # type: ignore[arg-type]
            metrics=metrics,  # type: ignore[arg-type]
        )

        result = await use_case.execute(state)

        logger.info(
            "output_node_complete",
            jira_keys=len(result.get("output_jira_keys", [])),
            pdf_generated=result.get("output_pdf_path") is not None,
            json_exported=result.get("output_json_path") is not None,
            csv_exported=result.get("output_csv_path") is not None,
            error_count=len(result.get("output_errors", [])),
        )

        return {
            "output_run_id": state.get("thread_id"),
            **result,
            "current_node": "output",
        }

    except Exception as exc:
        error_msg = f"Output generation failed: {exc}"
        logger.exception("output_node_failed", error=error_msg)
        return {
            "output_run_id": state.get("thread_id"),
            "output_jira_keys": [],
            "output_pdf_path": None,
            "output_csv_path": None,
            "output_json_path": None,
            "output_errors": [error_msg],
            "current_node": "output",
        }


__all__ = [
    "output_node",
]
