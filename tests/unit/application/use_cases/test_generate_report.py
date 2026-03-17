"""Tests for GenerateReportUseCase."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from siopv.application.ports.jira_client import JiraClientPort
from siopv.application.ports.metrics_exporter import MetricsExporterPort
from siopv.application.ports.pdf_generator import PdfGeneratorPort
from siopv.application.use_cases.generate_report import (
    GenerateReportUseCase,
    create_generate_report_use_case,
)


def _make_mock_jira() -> AsyncMock:
    """Create a mock JiraClientPort."""
    mock = AsyncMock(spec=JiraClientPort)
    mock.find_ticket_by_cve.return_value = None
    mock.create_ticket.return_value = "SEC-001"
    return mock


def _make_mock_pdf() -> MagicMock:
    """Create a mock PdfGeneratorPort."""
    mock = MagicMock(spec=PdfGeneratorPort)
    mock.generate.return_value = "/tmp/siopv-report-test.pdf"
    return mock


def _make_mock_metrics() -> MagicMock:
    """Create a mock MetricsExporterPort."""
    mock = MagicMock(spec=MetricsExporterPort)
    mock.export_json.return_value = "/tmp/siopv-metrics-test.json"
    mock.export_csv.return_value = "/tmp/siopv-metrics-test.csv"
    return mock


def _make_state(
    *,
    classifications: dict[str, Any] | None = None,
    thread_id: str = "test-thread-001",
) -> dict[str, Any]:
    """Create a minimal PipelineState-like dict for testing."""
    return {
        "thread_id": thread_id,
        "vulnerabilities": [],
        "classifications": classifications or {},
        "errors": [],
    }


class TestGenerateReportUseCase:
    """Tests for GenerateReportUseCase."""

    @pytest.mark.asyncio
    async def test_happy_path_all_channels_succeed(self) -> None:
        """All output channels succeed — returns all paths and no errors."""
        jira = _make_mock_jira()
        jira.create_ticket.side_effect = ["SEC-001", "SEC-002"]
        pdf = _make_mock_pdf()
        metrics = _make_mock_metrics()

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(
            classifications={
                "CVE-2024-0001": {"risk": "HIGH"},
                "CVE-2024-0002": {"risk": "MEDIUM"},
            },
        )

        result = await use_case.execute(state)

        assert result["output_jira_keys"] == ["SEC-001", "SEC-002"]
        assert result["output_pdf_path"] == "/tmp/siopv-report-test.pdf"
        assert result["output_json_path"] == "/tmp/siopv-metrics-test.json"
        assert result["output_csv_path"] == "/tmp/siopv-metrics-test.csv"
        assert result["output_errors"] == []

    @pytest.mark.asyncio
    async def test_jira_failure_does_not_block_pdf_and_csv(self) -> None:
        """If Jira fails, PDF and CSV should still be generated."""
        jira = _make_mock_jira()
        jira.create_ticket.side_effect = RuntimeError("Jira API unreachable")
        pdf = _make_mock_pdf()
        metrics = _make_mock_metrics()

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(
            classifications={"CVE-2024-0001": {"risk": "HIGH"}},
        )

        result = await use_case.execute(state)

        assert result["output_jira_keys"] == []
        assert result["output_pdf_path"] is not None
        assert result["output_json_path"] is not None
        assert result["output_csv_path"] is not None
        assert len(result["output_errors"]) == 1
        assert "Jira" in result["output_errors"][0]

    @pytest.mark.asyncio
    async def test_pdf_failure_does_not_block_other_channels(self) -> None:
        """If PDF generation fails, Jira and metrics should still work."""
        jira = _make_mock_jira()
        pdf = _make_mock_pdf()
        pdf.generate.side_effect = RuntimeError("PDF rendering error")
        metrics = _make_mock_metrics()

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(
            classifications={"CVE-2024-0001": {"risk": "HIGH"}},
        )

        result = await use_case.execute(state)

        assert result["output_jira_keys"] == ["SEC-001"]
        assert result["output_pdf_path"] is None
        assert result["output_json_path"] is not None
        assert result["output_csv_path"] is not None
        assert len(result["output_errors"]) == 1
        assert "PDF" in result["output_errors"][0]

    @pytest.mark.asyncio
    async def test_all_channels_fail(self) -> None:
        """If all channels fail, errors are collected for each."""
        jira = _make_mock_jira()
        jira.create_ticket.side_effect = RuntimeError("Jira down")
        pdf = _make_mock_pdf()
        pdf.generate.side_effect = RuntimeError("PDF error")
        metrics = _make_mock_metrics()
        metrics.export_json.side_effect = RuntimeError("JSON error")
        metrics.export_csv.side_effect = RuntimeError("CSV error")

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(
            classifications={"CVE-2024-0001": {"risk": "HIGH"}},
        )

        result = await use_case.execute(state)

        assert result["output_jira_keys"] == []
        assert result["output_pdf_path"] is None
        assert result["output_json_path"] is None
        assert result["output_csv_path"] is None
        assert len(result["output_errors"]) == 4

    @pytest.mark.asyncio
    async def test_empty_classifications_skips_jira(self) -> None:
        """With no classifications, Jira is skipped but PDF/CSV still generated."""
        jira = _make_mock_jira()
        pdf = _make_mock_pdf()
        metrics = _make_mock_metrics()

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(classifications={})

        result = await use_case.execute(state)

        assert result["output_jira_keys"] == []
        assert result["output_pdf_path"] is not None
        assert result["output_errors"] == []
        jira.create_ticket.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_jira_ticket_reused(self) -> None:
        """If a ticket already exists for a CVE, it is reused instead of created."""
        jira = _make_mock_jira()
        jira.find_ticket_by_cve.return_value = "SEC-EXISTING"
        pdf = _make_mock_pdf()
        metrics = _make_mock_metrics()

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(
            classifications={"CVE-2024-0001": {"risk": "HIGH"}},
        )

        result = await use_case.execute(state)

        assert result["output_jira_keys"] == ["SEC-EXISTING"]
        jira.create_ticket.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_jira_failure_collects_errors(self) -> None:
        """If one CVE's Jira ticket fails, others succeed and error is collected."""
        jira = _make_mock_jira()
        jira.find_ticket_by_cve.return_value = None
        jira.create_ticket.side_effect = [
            "SEC-001",
            RuntimeError("Timeout"),
            "SEC-003",
        ]
        pdf = _make_mock_pdf()
        metrics = _make_mock_metrics()

        use_case = GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)
        state = _make_state(
            classifications={
                "CVE-2024-0001": {"risk": "HIGH"},
                "CVE-2024-0002": {"risk": "MEDIUM"},
                "CVE-2024-0003": {"risk": "LOW"},
            },
        )

        result = await use_case.execute(state)

        assert "SEC-001" in result["output_jira_keys"]
        assert "SEC-003" in result["output_jira_keys"]
        assert len(result["output_errors"]) == 1
        assert "CVE-2024-0002" in result["output_errors"][0]


class TestCreateGenerateReportUseCase:
    """Tests for the factory function."""

    def test_factory_returns_use_case_instance(self) -> None:
        """create_generate_report_use_case should return a GenerateReportUseCase."""
        jira = _make_mock_jira()
        pdf = _make_mock_pdf()
        metrics = _make_mock_metrics()

        use_case = create_generate_report_use_case(jira=jira, pdf=pdf, metrics=metrics)
        assert isinstance(use_case, GenerateReportUseCase)
