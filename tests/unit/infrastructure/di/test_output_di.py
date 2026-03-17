"""Unit tests for output DI factory functions.

Tests factory functions for creating Phase 8 output components:
- build_jira_adapter: Creates JiraAdapter from Settings
- build_pdf_adapter: Creates Fpdf2Adapter from Settings
- build_metrics_exporter: Creates MetricsExporterAdapter from Settings
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from siopv.adapters.notification.jira_adapter import JiraAdapter
from siopv.adapters.output.fpdf2_adapter import Fpdf2Adapter
from siopv.adapters.output.metrics_exporter_adapter import MetricsExporterAdapter
from siopv.infrastructure.config.settings import Settings
from siopv.infrastructure.di.output import (
    build_jira_adapter,
    build_metrics_exporter,
    build_pdf_adapter,
)

# === Fixtures ===


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings with Jira and output configuration."""
    return Settings(
        jira_base_url="https://test.atlassian.net",
        jira_email="test@example.com",
        jira_api_token="test-jira-token",
        jira_project_key="SEC",
        output_dir=tmp_path / "output",
    )


@pytest.fixture
def settings_no_jira(tmp_path: Path) -> Settings:
    """Settings with no Jira configuration."""
    return Settings(
        jira_base_url=None,
        jira_email=None,
        jira_api_token=None,
        jira_project_key=None,
        output_dir=tmp_path / "output",
    )


@pytest.fixture
def settings_minimal(tmp_path: Path) -> Settings:
    """Minimal settings with only output_dir."""
    return Settings(
        output_dir=tmp_path / "output",
    )


# === Test build_jira_adapter ===


class TestBuildJiraAdapter:
    """Tests for the build_jira_adapter factory function."""

    def test_returns_jira_adapter(self, settings: Settings) -> None:
        """Happy path: factory returns a properly initialized JiraAdapter."""
        result = build_jira_adapter(settings)

        assert isinstance(result, JiraAdapter)

    def test_logging_on_creation(self, settings: Settings) -> None:
        """Factory logs info event with Jira base URL."""
        with patch("siopv.infrastructure.di.output.logger") as mock_logger:
            build_jira_adapter(settings)

            mock_logger.info.assert_called_once_with(
                "jira_adapter_created",
                base_url="https://test.atlassian.net",
            )

    def test_raises_with_none_jira_url(self, settings_no_jira: Settings) -> None:
        """Factory propagates JiraIntegrationError when Jira URL is None."""
        from siopv.domain.exceptions import JiraIntegrationError

        with pytest.raises(JiraIntegrationError):
            build_jira_adapter(settings_no_jira)


# === Test build_pdf_adapter ===


class TestBuildPdfAdapter:
    """Tests for the build_pdf_adapter factory function."""

    def test_returns_fpdf2_adapter(self, settings: Settings) -> None:
        """Happy path: factory returns a properly initialized Fpdf2Adapter."""
        result = build_pdf_adapter(settings)

        assert isinstance(result, Fpdf2Adapter)

    def test_logging_on_creation(self, settings: Settings) -> None:
        """Factory logs info event with output directory."""
        with patch("siopv.infrastructure.di.output.logger") as mock_logger:
            build_pdf_adapter(settings)

            mock_logger.info.assert_called_once_with(
                "pdf_adapter_created",
                output_dir=str(settings.output_dir),
            )


# === Test build_metrics_exporter ===


class TestBuildMetricsExporter:
    """Tests for the build_metrics_exporter factory function."""

    def test_returns_metrics_exporter_adapter(self, settings: Settings) -> None:
        """Happy path: factory returns a properly initialized MetricsExporterAdapter."""
        result = build_metrics_exporter(settings)

        assert isinstance(result, MetricsExporterAdapter)

    def test_logging_on_creation(self, settings: Settings) -> None:
        """Factory logs info event with output directory."""
        with patch("siopv.infrastructure.di.output.logger") as mock_logger:
            build_metrics_exporter(settings)

            mock_logger.info.assert_called_once_with(
                "metrics_exporter_created",
                output_dir=str(settings.output_dir),
            )


# === Test exports ===


class TestOutputDiExports:
    """Tests for output DI module exports via __init__.py."""

    def test_importable_from_di_package(self) -> None:
        from siopv.infrastructure.di import (
            build_jira_adapter,
            build_metrics_exporter,
            build_pdf_adapter,
        )

        assert callable(build_jira_adapter)
        assert callable(build_metrics_exporter)
        assert callable(build_pdf_adapter)
