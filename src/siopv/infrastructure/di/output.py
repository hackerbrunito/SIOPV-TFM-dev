"""Dependency injection factory functions for Phase 8 output components.

Factory functions for creating Jira, PDF, and metrics export adapters
that implement the corresponding ports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from siopv.adapters.notification.jira_adapter import JiraAdapter
from siopv.adapters.output.fpdf2_adapter import Fpdf2Adapter
from siopv.adapters.output.metrics_exporter_adapter import MetricsExporterAdapter
from siopv.application.ports.jira_client import JiraClientPort
from siopv.application.ports.metrics_exporter import MetricsExporterPort
from siopv.application.ports.pdf_generator import PdfGeneratorPort

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def build_jira_adapter(settings: Settings) -> JiraClientPort:
    """Create a configured JiraAdapter from application settings.

    Args:
        settings: Application settings with Jira configuration

    Returns:
        JiraClientPort implementation backed by JiraAdapter
    """
    adapter = JiraAdapter(settings)
    logger.info("jira_adapter_created", base_url=settings.jira_base_url)
    return adapter


def build_pdf_adapter(settings: Settings) -> PdfGeneratorPort:
    """Create a configured PDF generator adapter from application settings.

    Args:
        settings: Application settings

    Returns:
        PdfGeneratorPort implementation backed by Fpdf2Adapter
    """
    adapter = Fpdf2Adapter()
    logger.info("pdf_adapter_created", output_dir=str(settings.output_dir))
    return adapter


def build_metrics_exporter(settings: Settings) -> MetricsExporterPort:
    """Create a configured metrics exporter adapter from application settings.

    Args:
        settings: Application settings

    Returns:
        MetricsExporterPort implementation backed by MetricsExporterAdapter
    """
    adapter = MetricsExporterAdapter(output_dir=settings.output_dir)
    logger.info("metrics_exporter_created", output_dir=str(settings.output_dir))
    return adapter


__all__ = [
    "build_jira_adapter",
    "build_metrics_exporter",
    "build_pdf_adapter",
]
