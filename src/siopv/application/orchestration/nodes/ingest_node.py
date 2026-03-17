"""Ingest node for LangGraph pipeline.

Handles Phase 1: Parse Trivy report, deduplicate, and populate state.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from siopv.application.use_cases.ingest_trivy import IngestTrivyReportUseCase

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState

logger = structlog.get_logger(__name__)


def ingest_node(
    state: PipelineState,
    use_case: IngestTrivyReportUseCase | None = None,
) -> dict[str, object]:
    """Execute ingestion phase as a LangGraph node.

    This node wraps the IngestTrivyReportUseCase to integrate with
    the LangGraph orchestration pipeline.

    Args:
        state: Current pipeline state with report_path
        use_case: Optional pre-constructed use case for dependency injection.
            If None, a default instance is created with TrivyParser.

    Returns:
        State updates with vulnerabilities list and processed_count
    """

    logger.info("ingest_node_started", thread_id=state.get("thread_id"))

    report_path = state.get("report_path")

    if not report_path:
        error_msg = "No report_path provided in state"
        logger.error("ingest_node_failed", error=error_msg)
        return {
            "vulnerabilities": [],
            "processed_count": 0,
            "errors": [error_msg],
            "current_node": "ingest",
        }

    if use_case is None:
        error_msg = "use_case is required — inject IngestTrivyReportUseCase via graph wiring"
        logger.error("ingest_node_failed", error=error_msg)
        return {
            "vulnerabilities": [],
            "processed_count": 0,
            "errors": [error_msg],
            "current_node": "ingest",
        }

    try:
        result = use_case.execute(Path(report_path))

        logger.info(
            "ingest_node_complete",
            total_vulnerabilities=len(result.records),
            unique_packages=result.stats.unique_packages,
            by_severity=result.stats.by_severity,
        )

        return {
            "vulnerabilities": result.records,
            "processed_count": len(result.records),
            "current_node": "ingest",
        }

    except FileNotFoundError as e:
        error_msg = f"Report file not found: {report_path}"
        logger.exception("ingest_node_failed", error=error_msg, exception=str(e))
        return {
            "vulnerabilities": [],
            "processed_count": 0,
            "errors": [error_msg],
            "current_node": "ingest",
        }

    except Exception as e:
        error_msg = f"Ingestion failed: {e}"
        logger.exception("ingest_node_failed", error=error_msg, exception=str(e))
        return {
            "vulnerabilities": [],
            "processed_count": 0,
            "errors": [error_msg],
            "current_node": "ingest",
        }


def ingest_node_from_dict(
    state: PipelineState,
    report_data: dict[str, object],
    use_case: IngestTrivyReportUseCase | None = None,
) -> dict[str, object]:
    """Execute ingestion from a dictionary (for API/testing).

    Alternative entry point when the report is already parsed JSON.

    Args:
        state: Current pipeline state
        report_data: Trivy report as dictionary
        use_case: Optional pre-constructed use case for dependency injection.
            If None, a default instance is created with TrivyParser.

    Returns:
        State updates with vulnerabilities list and processed_count
    """

    logger.info("ingest_node_from_dict_started", thread_id=state.get("thread_id"))

    if use_case is None:
        error_msg = "use_case is required — inject IngestTrivyReportUseCase via graph wiring"
        logger.error("ingest_node_from_dict_failed", error=error_msg)
        return {
            "vulnerabilities": [],
            "processed_count": 0,
            "errors": [error_msg],
            "current_node": "ingest",
        }

    try:
        result = use_case.execute_from_dict(report_data)

        logger.info(
            "ingest_node_from_dict_complete",
            total_vulnerabilities=len(result.records),
            unique_packages=result.stats.unique_packages,
        )

        return {
            "vulnerabilities": result.records,
            "processed_count": len(result.records),
            "current_node": "ingest",
        }

    except Exception as e:
        error_msg = f"Ingestion from dict failed: {e}"
        logger.exception("ingest_node_from_dict_failed", error=error_msg)
        return {
            "vulnerabilities": [],
            "processed_count": 0,
            "errors": [error_msg],
            "current_node": "ingest",
        }


__all__ = [
    "ingest_node",
    "ingest_node_from_dict",
]
