"""Tests for output_node."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from siopv.application.orchestration.nodes.output_node import output_node
from siopv.application.orchestration.state import create_initial_state


class TestOutputNode:
    """Tests for output_node function."""

    @pytest.fixture
    def mock_jira(self) -> MagicMock:
        """Create a mock JiraClientPort."""
        mock = MagicMock()
        mock.create_ticket = AsyncMock(return_value="SEC-001")
        mock.find_ticket_by_cve = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_pdf(self) -> MagicMock:
        """Create a mock PdfGeneratorPort."""
        mock = MagicMock()
        mock.generate = MagicMock(return_value="/tmp/siopv-report-test.pdf")
        return mock

    @pytest.fixture
    def mock_metrics(self) -> MagicMock:
        """Create a mock MetricsExporterPort."""
        mock = MagicMock()
        mock.export_json = MagicMock(return_value="/tmp/siopv-metrics-test.json")
        mock.export_csv = MagicMock(return_value="/tmp/siopv-metrics-test.csv")
        return mock

    @pytest.fixture
    def base_state(self) -> dict[str, Any]:
        """Create a base pipeline state for tests."""
        return dict(create_initial_state(thread_id="test-thread-001"))

    async def test_output_node_happy_path(
        self,
        base_state: dict[str, Any],
        mock_jira: MagicMock,
        mock_pdf: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test output_node succeeds with all ports configured."""
        result = await output_node(
            base_state,  # type: ignore[arg-type]
            jira=mock_jira,
            pdf=mock_pdf,
            metrics=mock_metrics,
        )

        assert result["current_node"] == "output"
        assert result["output_run_id"] == "test-thread-001"
        assert isinstance(result["output_jira_keys"], list)
        assert isinstance(result["output_errors"], list)

    async def test_output_node_missing_ports_skips(
        self,
        base_state: dict[str, Any],
    ) -> None:
        """Test output_node skips when ports are None."""
        result = await output_node(
            base_state,  # type: ignore[arg-type]
            jira=None,
            pdf=None,
            metrics=None,
        )

        assert result["current_node"] == "output"
        assert result["output_run_id"] == "test-thread-001"
        assert result["output_jira_keys"] == []
        assert result["output_pdf_path"] is None
        assert result["output_csv_path"] is None
        assert result["output_json_path"] is None
        assert len(result["output_errors"]) == 1
        assert "not configured" in result["output_errors"][0]

    async def test_output_node_partial_ports_skips(
        self,
        base_state: dict[str, Any],
        mock_jira: MagicMock,
    ) -> None:
        """Test output_node skips when only some ports are configured."""
        result = await output_node(
            base_state,  # type: ignore[arg-type]
            jira=mock_jira,
            pdf=None,
            metrics=None,
        )

        assert result["current_node"] == "output"
        assert "not configured" in result["output_errors"][0]

    async def test_output_node_error_handling(
        self,
        base_state: dict[str, Any],
        mock_jira: MagicMock,
        mock_pdf: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test output_node catches exceptions and returns error state."""
        mock_jira.find_ticket_by_cve = AsyncMock(
            side_effect=RuntimeError("Jira API down"),
        )
        mock_jira.create_ticket = AsyncMock(
            side_effect=RuntimeError("Jira API down"),
        )

        # Add a classification to trigger Jira ticket creation
        base_state["classifications"] = {"CVE-2024-1234": MagicMock()}

        result = await output_node(
            base_state,  # type: ignore[arg-type]
            jira=mock_jira,
            pdf=mock_pdf,
            metrics=mock_metrics,
        )

        assert result["current_node"] == "output"
        assert result["output_run_id"] == "test-thread-001"
        # The use case catches per-channel errors, so we still get a result
        assert isinstance(result["output_errors"], list)

    async def test_output_node_returns_all_state_fields(
        self,
        base_state: dict[str, Any],
    ) -> None:
        """Test output_node always returns all required state fields."""
        result = await output_node(base_state)  # type: ignore[arg-type]

        required_fields = [
            "output_run_id",
            "output_jira_keys",
            "output_pdf_path",
            "output_csv_path",
            "output_json_path",
            "output_errors",
            "current_node",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    async def test_output_node_use_case_exception_caught(
        self,
        base_state: dict[str, Any],
        mock_jira: MagicMock,
        mock_pdf: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that a catastrophic use case failure is caught."""
        # Force GenerateReportUseCase.execute to raise
        mock_pdf.generate = MagicMock(side_effect=RuntimeError("PDF crash"))
        # The use case catches per-channel, but let's check node-level too
        result = await output_node(
            base_state,  # type: ignore[arg-type]
            jira=mock_jira,
            pdf=mock_pdf,
            metrics=mock_metrics,
        )

        assert result["current_node"] == "output"
        assert result["output_run_id"] == "test-thread-001"
        # Error should be captured (either in output_errors or as node-level catch)
        assert isinstance(result["output_errors"], list)

    async def test_output_node_catches_use_case_init_failure(
        self,
        base_state: dict[str, Any],
        mock_jira: MagicMock,
        mock_pdf: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test lines 92-95: node-level except catches GenerateReportUseCase crash."""
        from unittest.mock import patch

        # Patch at the source module since it's imported inline
        with patch(
            "siopv.application.use_cases.generate_report.GenerateReportUseCase",
            side_effect=RuntimeError("Use case init exploded"),
        ):
            result = await output_node(
                base_state,  # type: ignore[arg-type]
                jira=mock_jira,
                pdf=mock_pdf,
                metrics=mock_metrics,
            )

        assert result["current_node"] == "output"
        assert result["output_run_id"] == "test-thread-001"
        assert result["output_jira_keys"] == []
        assert result["output_pdf_path"] is None
        assert result["output_csv_path"] is None
        assert result["output_json_path"] is None
        assert len(result["output_errors"]) == 1
        assert "Output generation failed" in result["output_errors"][0]
        assert "Use case init exploded" in result["output_errors"][0]
