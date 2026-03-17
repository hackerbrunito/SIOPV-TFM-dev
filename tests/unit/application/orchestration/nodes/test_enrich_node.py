"""Tests for enrich_node."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from siopv.application.orchestration.nodes.enrich_node import (
    _create_minimal_enrichments,
    enrich_node,
)
from siopv.application.orchestration.state import create_initial_state
from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.value_objects import CVEId, EnrichmentData


class TestEnrichNode:
    """Tests for enrich_node function."""

    @pytest.fixture
    def mock_vulnerability(self) -> MagicMock:
        """Create a mock VulnerabilityRecord."""
        mock = MagicMock(spec=VulnerabilityRecord)
        mock.cve_id = CVEId(value="CVE-2024-1234")
        mock.severity = "HIGH"
        return mock

    @pytest.fixture
    def mock_clients(self) -> dict:
        """Create mock clients for enrichment."""
        return {
            "nvd_client": MagicMock(),
            "epss_client": MagicMock(),
            "github_client": MagicMock(),
            "osint_client": MagicMock(),
            "vector_store": MagicMock(),
        }

    async def test_enrich_node_with_no_vulnerabilities(self):
        """Test enrich node skips when no vulnerabilities."""
        state = create_initial_state()

        result = await enrich_node(state)

        assert result["enrichments"] == {}
        assert result["current_node"] == "enrich"

    async def test_enrich_node_with_missing_clients_uses_minimal(
        self, mock_vulnerability: MagicMock
    ):
        """Test enrich node uses minimal enrichments when clients missing."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
        }

        result = await enrich_node(state, nvd_client=None)

        assert result["current_node"] == "enrich"
        assert "enrichments" in result
        # Should have minimal enrichment for the CVE
        assert "CVE-2024-1234" in result["enrichments"]

    async def test_enrich_node_success_with_all_clients(
        self, mock_vulnerability: MagicMock, mock_clients: dict
    ):
        """Test enrich node success when all clients provided."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
        }

        # Mock the async enrichment
        mock_enrichment = EnrichmentData(
            cve_id="CVE-2024-1234",
            relevance_score=0.8,
        )

        with patch(
            "siopv.application.orchestration.nodes.enrich_node._run_enrichment",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = {"CVE-2024-1234": mock_enrichment}

            result = await enrich_node(state, **mock_clients)

        assert result["current_node"] == "enrich"
        assert "CVE-2024-1234" in result["enrichments"]

    async def test_enrich_node_exception_handling(self, mock_vulnerability: MagicMock):
        """Test enrich node handles exceptions gracefully."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
        }

        with patch(
            "siopv.application.orchestration.nodes.enrich_node._run_enrichment",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Network error"),
        ):
            result = await enrich_node(state)

        assert result["enrichments"] == {}
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "Enrichment failed" in result["errors"][0]


class TestCreateMinimalEnrichments:
    """Tests for _create_minimal_enrichments function."""

    @pytest.fixture
    def mock_vulnerabilities(self) -> list[MagicMock]:
        """Create mock vulnerabilities for testing."""
        vuln1 = MagicMock(spec=VulnerabilityRecord)
        vuln1.cve_id = CVEId(value="CVE-2024-1111")

        vuln2 = MagicMock(spec=VulnerabilityRecord)
        vuln2.cve_id = CVEId(value="CVE-2024-2222")

        return [vuln1, vuln2]

    def test_create_minimal_enrichments_structure(self, mock_vulnerabilities: list[MagicMock]):
        """Test minimal enrichments have correct structure."""
        result = _create_minimal_enrichments(mock_vulnerabilities)

        assert len(result) == 2
        assert "CVE-2024-1111" in result
        assert "CVE-2024-2222" in result

        # Check EnrichmentData structure
        enrichment = result["CVE-2024-1111"]
        assert isinstance(enrichment, EnrichmentData)
        assert enrichment.cve_id == "CVE-2024-1111"
        assert enrichment.relevance_score == 0.5  # Default relevance

    def test_create_minimal_enrichments_empty_list(self):
        """Test minimal enrichments with empty vulnerability list."""
        result = _create_minimal_enrichments([])

        assert result == {}


class TestEnrichNodeLLMIntegration:
    """Tests for LLM analysis integration in enrich_node."""

    @pytest.fixture
    def mock_vulnerability(self) -> MagicMock:
        """Create a mock VulnerabilityRecord."""
        mock = MagicMock(spec=VulnerabilityRecord)
        mock.cve_id = CVEId(value="CVE-2024-1234")
        mock.severity = "HIGH"
        return mock

    async def test_enrich_node_passes_llm_to_run_enrichment(self, mock_vulnerability: MagicMock):
        """Test that enrich_node passes llm_analysis to _run_enrichment."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
        }

        mock_llm = MagicMock()
        mock_enrichment = EnrichmentData(
            cve_id="CVE-2024-1234",
            relevance_score=0.95,
            llm_summary="Test summary",
        )

        with patch(
            "siopv.application.orchestration.nodes.enrich_node._run_enrichment",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = {"CVE-2024-1234": mock_enrichment}

            mock_clients = {
                "nvd_client": MagicMock(),
                "epss_client": MagicMock(),
                "github_client": MagicMock(),
                "osint_client": MagicMock(),
                "vector_store": MagicMock(),
            }
            result = await enrich_node(state, **mock_clients, llm_analysis=mock_llm)

        assert result["enrichments"]["CVE-2024-1234"] == mock_enrichment
        # Verify llm_analysis was passed through
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["llm_analysis"] is mock_llm

    async def test_enrich_node_without_llm_backward_compatible(self, mock_vulnerability: MagicMock):
        """Test enrich_node works without llm_analysis (backward compatible)."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
        }

        mock_enrichment = EnrichmentData(
            cve_id="CVE-2024-1234",
            relevance_score=0.8,
        )

        with patch(
            "siopv.application.orchestration.nodes.enrich_node._run_enrichment",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = {"CVE-2024-1234": mock_enrichment}

            mock_clients = {
                "nvd_client": MagicMock(),
                "epss_client": MagicMock(),
                "github_client": MagicMock(),
                "osint_client": MagicMock(),
                "vector_store": MagicMock(),
            }
            result = await enrich_node(state, **mock_clients)

        assert result["enrichments"]["CVE-2024-1234"] == mock_enrichment
        # llm_analysis should default to None
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["llm_analysis"] is None

    async def test_enrich_node_missing_clients_ignores_llm(self, mock_vulnerability: MagicMock):
        """Test that missing required clients triggers minimal enrichment even with LLM."""
        state = {
            **create_initial_state(),
            "vulnerabilities": [mock_vulnerability],
        }

        mock_llm = MagicMock()

        # Only provide llm_analysis, no required clients
        result = await enrich_node(state, llm_analysis=mock_llm)

        assert result["current_node"] == "enrich"
        assert "CVE-2024-1234" in result["enrichments"]
        # Should be minimal enrichment (0.5 default), LLM not used
        enrichment = result["enrichments"]["CVE-2024-1234"]
        assert isinstance(enrichment, EnrichmentData)
        assert enrichment.relevance_score == 0.5
