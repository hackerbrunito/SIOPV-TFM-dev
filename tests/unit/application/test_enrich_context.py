"""Tests for EnrichContextUseCase with CRAG pattern."""

from unittest.mock import AsyncMock

import pytest

from siopv.application.use_cases import (
    EnrichContextUseCase,
    EnrichmentResult,
)
from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.value_objects import (
    CVEId,
    EnrichmentData,
    EPSSScore,
    GitHubAdvisory,
    NVDEnrichment,
    OSINTResult,
    PackageVersion,
)


@pytest.fixture
def mock_nvd_client() -> AsyncMock:
    """Create mock NVD client."""
    client = AsyncMock()
    client.get_cve = AsyncMock(
        return_value=NVDEnrichment(
            cve_id="CVE-2021-44228",
            description="Apache Log4j2 vulnerability",
            cvss_v3_score=10.0,
            has_exploit_ref=True,
        )
    )
    return client


@pytest.fixture
def mock_epss_client() -> AsyncMock:
    """Create mock EPSS client."""
    client = AsyncMock()
    client.get_score = AsyncMock(return_value=EPSSScore(score=0.95, percentile=0.99))
    return client


@pytest.fixture
def mock_github_client() -> AsyncMock:
    """Create mock GitHub Advisory client."""
    client = AsyncMock()
    client.get_advisory_by_cve = AsyncMock(
        return_value=GitHubAdvisory(
            ghsa_id="GHSA-jfh8-c2jp-5v3q",
            cve_id="CVE-2021-44228",
            summary="Log4j RCE vulnerability",
            severity="CRITICAL",
        )
    )
    return client


@pytest.fixture
def mock_osint_client() -> AsyncMock:
    """Create mock OSINT client."""
    client = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.search_exploit_info = AsyncMock(
        return_value=[
            OSINTResult(
                title="Log4j Exploit PoC",
                url="https://example.com/exploit",
                content="Proof of concept...",
                score=0.9,
            )
        ]
    )
    return client


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Create mock vector store."""
    store = AsyncMock()
    store.get_by_cve_id = AsyncMock(return_value=None)
    store.store_enrichment = AsyncMock(return_value="CVE-2021-44228")
    store.exists = AsyncMock(return_value=False)
    return store


@pytest.fixture
def sample_vulnerability() -> VulnerabilityRecord:
    """Create sample vulnerability record."""
    return VulnerabilityRecord(
        cve_id=CVEId(value="CVE-2021-44228"),
        package_name="log4j-core",
        installed_version=PackageVersion(value="2.14.1"),
        severity="CRITICAL",
    )


@pytest.fixture
def use_case(
    mock_nvd_client: AsyncMock,
    mock_epss_client: AsyncMock,
    mock_github_client: AsyncMock,
    mock_osint_client: AsyncMock,
    mock_vector_store: AsyncMock,
) -> EnrichContextUseCase:
    """Create use case with mock dependencies."""
    return EnrichContextUseCase(
        nvd_client=mock_nvd_client,
        epss_client=mock_epss_client,
        github_client=mock_github_client,
        osint_client=mock_osint_client,
        vector_store=mock_vector_store,
    )


class TestEnrichContextUseCase:
    """Tests for EnrichContextUseCase."""

    @pytest.mark.asyncio
    async def test_successful_enrichment(
        self,
        use_case: EnrichContextUseCase,
        sample_vulnerability: VulnerabilityRecord,
        mock_vector_store: AsyncMock,
    ) -> None:
        """Test successful enrichment with all sources."""
        result = await use_case.execute(sample_vulnerability)

        assert isinstance(result, EnrichmentResult)
        assert result.cve_id == "CVE-2021-44228"
        assert result.enrichment is not None
        assert result.error is None
        assert not result.from_cache

        # Verify enrichment data
        enrichment = result.enrichment
        assert enrichment.nvd is not None
        assert enrichment.epss is not None
        assert enrichment.github_advisory is not None

        # Verify storage was called
        mock_vector_store.store_enrichment.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit(
        self,
        use_case: EnrichContextUseCase,
        sample_vulnerability: VulnerabilityRecord,
        mock_vector_store: AsyncMock,
        mock_nvd_client: AsyncMock,
    ) -> None:
        """Test that cached enrichment is returned."""
        cached_enrichment = EnrichmentData(
            cve_id="CVE-2021-44228",
            nvd=NVDEnrichment(cve_id="CVE-2021-44228", description="Cached"),
            relevance_score=0.9,
        )
        mock_vector_store.get_by_cve_id = AsyncMock(return_value=cached_enrichment)

        result = await use_case.execute(sample_vulnerability)

        assert result.from_cache is True
        assert result.enrichment == cached_enrichment

        # NVD client should not be called
        mock_nvd_client.get_cve.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_cache(
        self,
        use_case: EnrichContextUseCase,
        sample_vulnerability: VulnerabilityRecord,
        mock_vector_store: AsyncMock,
        mock_nvd_client: AsyncMock,
    ) -> None:
        """Test that skip_cache bypasses cache."""
        cached_enrichment = EnrichmentData(
            cve_id="CVE-2021-44228",
            relevance_score=0.9,
        )
        mock_vector_store.get_by_cve_id = AsyncMock(return_value=cached_enrichment)

        result = await use_case.execute(sample_vulnerability, skip_cache=True)

        assert result.from_cache is False

        # NVD client should be called
        mock_nvd_client.get_cve.assert_called_once()

    @pytest.mark.asyncio
    async def test_osint_fallback_triggered(
        self,
        mock_epss_client: AsyncMock,
        mock_github_client: AsyncMock,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test OSINT fallback when relevance is low."""
        # NVD returns None (no data)
        mock_nvd_client = AsyncMock()
        mock_nvd_client.get_cve = AsyncMock(return_value=None)

        # EPSS returns None
        mock_epss_client.get_score = AsyncMock(return_value=None)

        # GitHub returns None
        mock_github_client.get_advisory_by_cve = AsyncMock(return_value=None)

        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
            relevance_threshold=0.6,
        )

        result = await use_case.execute(sample_vulnerability)

        # OSINT fallback should be used
        assert result.osint_fallback_used is True
        mock_osint_client.search_exploit_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_osint_fallback_not_triggered_high_relevance(
        self,
        use_case: EnrichContextUseCase,
        sample_vulnerability: VulnerabilityRecord,
        mock_osint_client: AsyncMock,
    ) -> None:
        """Test OSINT fallback not triggered when relevance is high."""
        result = await use_case.execute(sample_vulnerability)

        # OSINT fallback should NOT be used (high relevance from NVD+EPSS+GitHub)
        assert result.osint_fallback_used is False
        mock_osint_client.search_exploit_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_source_failure(
        self,
        mock_nvd_client: AsyncMock,
        mock_github_client: AsyncMock,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test graceful handling of partial source failures."""
        # EPSS fails
        mock_epss_client = AsyncMock()
        mock_epss_client.get_score = AsyncMock(side_effect=Exception("EPSS API error"))

        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
        )

        result = await use_case.execute(sample_vulnerability)

        # Should still succeed with partial data
        assert result.enrichment is not None
        assert result.error is None
        assert result.enrichment.nvd is not None  # NVD succeeded
        assert result.enrichment.epss is None  # EPSS failed

    @pytest.mark.asyncio
    async def test_all_sources_fail(
        self,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test handling when all sources fail."""
        mock_nvd_client = AsyncMock()
        mock_nvd_client.get_cve = AsyncMock(return_value=None)

        mock_epss_client = AsyncMock()
        mock_epss_client.get_score = AsyncMock(return_value=None)

        mock_github_client = AsyncMock()
        mock_github_client.get_advisory_by_cve = AsyncMock(return_value=None)

        # OSINT also returns empty
        mock_osint_client.search_exploit_info = AsyncMock(return_value=[])
        mock_osint_client.search = AsyncMock(return_value=[])

        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
        )

        result = await use_case.execute(sample_vulnerability)

        # Should still return enrichment (empty but valid)
        assert result.enrichment is not None
        assert result.enrichment.relevance_score == 0.0


class TestBatchEnrichment:
    """Tests for batch enrichment functionality."""

    @pytest.mark.asyncio
    async def test_batch_enrichment(
        self,
        use_case: EnrichContextUseCase,
    ) -> None:
        """Test batch enrichment of multiple vulnerabilities."""
        vulnerabilities = [
            VulnerabilityRecord(
                cve_id=CVEId(value=f"CVE-2021-{i}"),
                package_name="test-package",
                installed_version=PackageVersion(value="1.0.0"),
                severity="HIGH",
            )
            for i in range(44228, 44231)  # 3 CVEs
        ]

        result = await use_case.execute_batch(vulnerabilities, max_concurrent=2)

        assert len(result.results) == 3
        assert result.stats.total_processed == 3
        assert result.stats.successful >= 0

    @pytest.mark.asyncio
    async def test_batch_enrichment_stats(
        self,
        mock_nvd_client: AsyncMock,
        mock_epss_client: AsyncMock,
        mock_github_client: AsyncMock,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
    ) -> None:
        """Test batch enrichment statistics calculation."""
        # Set up one cached result
        mock_vector_store.get_by_cve_id = AsyncMock(
            side_effect=[
                EnrichmentData(cve_id="CVE-2021-44228", relevance_score=0.8),  # Cached
                None,  # Not cached
            ]
        )

        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
        )

        vulnerabilities = [
            VulnerabilityRecord(
                cve_id=CVEId(value="CVE-2021-44228"),
                package_name="log4j",
                installed_version=PackageVersion(value="2.14.1"),
                severity="CRITICAL",
            ),
            VulnerabilityRecord(
                cve_id=CVEId(value="CVE-2021-44229"),
                package_name="log4j",
                installed_version=PackageVersion(value="2.14.1"),
                severity="HIGH",
            ),
        ]

        result = await use_case.execute_batch(vulnerabilities)

        assert result.stats.total_processed == 2
        assert result.stats.from_cache == 1
        assert result.stats.successful == 2


class TestRelevanceCalculation:
    """Tests for relevance score calculation."""

    def test_relevance_with_all_sources(
        self,
        use_case: EnrichContextUseCase,
    ) -> None:
        """Test relevance calculation with all sources."""
        from siopv.application.use_cases.enrich_context import EnrichmentSources

        sources = EnrichmentSources(
            nvd=NVDEnrichment(cve_id="CVE-2021-44228", description="Test"),
            epss=EPSSScore(score=0.9, percentile=0.99),
            github=GitHubAdvisory(ghsa_id="GHSA-test"),
        )

        relevance = use_case._calculate_relevance(sources)

        # NVD with description: 0.4 + EPSS: 0.2 + GitHub: 0.2 = 0.8
        assert relevance == 0.8

    def test_relevance_with_nvd_only(
        self,
        use_case: EnrichContextUseCase,
    ) -> None:
        """Test relevance calculation with NVD only."""
        from siopv.application.use_cases.enrich_context import EnrichmentSources

        sources = EnrichmentSources(
            nvd=NVDEnrichment(cve_id="CVE-2021-44228", description="Test"),
        )

        relevance = use_case._calculate_relevance(sources)

        # NVD with description: 0.4
        assert relevance == 0.4

    def test_relevance_with_nvd_no_description(
        self,
        use_case: EnrichContextUseCase,
    ) -> None:
        """Test relevance calculation with NVD but no description."""
        from siopv.application.use_cases.enrich_context import EnrichmentSources

        sources = EnrichmentSources(
            nvd=NVDEnrichment(cve_id="CVE-2021-44228"),  # No description
        )

        relevance = use_case._calculate_relevance(sources)

        # NVD without description: 0.2
        assert relevance == 0.2

    def test_relevance_with_osint(
        self,
        use_case: EnrichContextUseCase,
    ) -> None:
        """Test relevance calculation including OSINT results."""
        from siopv.application.use_cases.enrich_context import EnrichmentSources

        sources = EnrichmentSources(
            osint=[
                OSINTResult(title="Test1", url="http://test1.com", content="", score=0.8),
                OSINTResult(title="Test2", url="http://test2.com", content="", score=0.7),
            ],
        )

        relevance = use_case._calculate_relevance(sources)

        # 2 OSINT results: 0.1 * 2 = 0.2
        assert relevance == 0.2

    def test_relevance_capped_at_one(
        self,
        use_case: EnrichContextUseCase,
    ) -> None:
        """Test that relevance score is capped at 1.0."""
        from siopv.application.use_cases.enrich_context import EnrichmentSources

        sources = EnrichmentSources(
            nvd=NVDEnrichment(cve_id="CVE-2021-44228", description="Test"),
            epss=EPSSScore(score=0.9, percentile=0.99),
            github=GitHubAdvisory(ghsa_id="GHSA-test"),
            osint=[
                OSINTResult(title=f"Test{i}", url=f"http://test{i}.com", content="", score=0.8)
                for i in range(5)
            ],
        )

        relevance = use_case._calculate_relevance(sources)

        # Should be capped at 1.0
        assert relevance == 1.0


class TestLLMAnalysisIntegration:
    """Tests for LLM analysis integration in enrichment use case."""

    @pytest.fixture
    def mock_llm_analysis(self) -> AsyncMock:
        """Create mock LLM analysis port."""
        from siopv.application.ports.llm_analysis import VulnerabilityAnalysis

        mock = AsyncMock()
        mock.analyze_vulnerability = AsyncMock(
            return_value=VulnerabilityAnalysis(
                summary="Critical RCE via JNDI injection in Log4j2",
                remediation_recommendation="Upgrade to Log4j 2.17.1 or later",
                relevance_assessment=0.95,
                reasoning="Log4Shell is actively exploited with high EPSS score",
            )
        )
        return mock

    @pytest.mark.asyncio
    async def test_enrichment_with_llm_analysis(
        self,
        mock_nvd_client: AsyncMock,
        mock_epss_client: AsyncMock,
        mock_github_client: AsyncMock,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_llm_analysis: AsyncMock,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test enrichment with LLM analysis populates LLM fields."""
        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
            llm_analysis=mock_llm_analysis,
        )

        result = await use_case.execute(sample_vulnerability)

        assert result.enrichment is not None
        assert result.enrichment.llm_summary == "Critical RCE via JNDI injection in Log4j2"
        assert result.enrichment.llm_remediation == "Upgrade to Log4j 2.17.1 or later"
        assert result.enrichment.llm_relevance_assessment == 0.95
        assert result.enrichment.llm_reasoning is not None
        # LLM relevance overrides heuristic
        assert result.enrichment.relevance_score == 0.95
        mock_llm_analysis.analyze_vulnerability.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrichment_without_llm_backward_compatible(
        self,
        use_case: EnrichContextUseCase,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test enrichment without LLM analysis keeps heuristic behavior."""
        result = await use_case.execute(sample_vulnerability)

        assert result.enrichment is not None
        assert result.enrichment.llm_summary is None
        assert result.enrichment.llm_remediation is None
        assert result.enrichment.llm_relevance_assessment is None
        assert result.enrichment.llm_reasoning is None
        # Heuristic score: NVD(0.4) + EPSS(0.2) + GitHub(0.2) = 0.8
        assert result.enrichment.relevance_score == 0.8

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_heuristic(
        self,
        mock_nvd_client: AsyncMock,
        mock_epss_client: AsyncMock,
        mock_github_client: AsyncMock,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test that LLM failure gracefully falls back to heuristic score."""
        mock_llm = AsyncMock()
        mock_llm.analyze_vulnerability = AsyncMock(side_effect=RuntimeError("LLM API unavailable"))

        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
            llm_analysis=mock_llm,
        )

        result = await use_case.execute(sample_vulnerability)

        assert result.enrichment is not None
        assert result.error is None
        # LLM fields should be None (failure)
        assert result.enrichment.llm_summary is None
        assert result.enrichment.llm_relevance_assessment is None
        # Heuristic score preserved
        assert result.enrichment.relevance_score == 0.8

    @pytest.mark.asyncio
    async def test_llm_receives_correct_context(
        self,
        mock_nvd_client: AsyncMock,
        mock_epss_client: AsyncMock,
        mock_github_client: AsyncMock,
        mock_osint_client: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_llm_analysis: AsyncMock,
        sample_vulnerability: VulnerabilityRecord,
    ) -> None:
        """Test that LLM receives enrichment context with correct keys."""
        use_case = EnrichContextUseCase(
            nvd_client=mock_nvd_client,
            epss_client=mock_epss_client,
            github_client=mock_github_client,
            osint_client=mock_osint_client,
            vector_store=mock_vector_store,
            llm_analysis=mock_llm_analysis,
        )

        await use_case.execute(sample_vulnerability)

        call_args = mock_llm_analysis.analyze_vulnerability.call_args
        cve_id_arg = call_args[0][0]
        context_arg = call_args[0][1]

        assert cve_id_arg == "CVE-2021-44228"
        assert "nvd_description" in context_arg
        assert "epss_score" in context_arg
        assert "github_advisory" in context_arg
        assert "heuristic_relevance" in context_arg
