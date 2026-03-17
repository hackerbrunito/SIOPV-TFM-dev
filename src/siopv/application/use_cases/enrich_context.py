"""Enrich Context Use Case with CRAG (Corrective RAG) pattern.

Orchestrates the enrichment pipeline for vulnerability records:
1. Parallel query to NVD + GitHub + EPSS
2. Relevance evaluation
3. OSINT fallback if relevance < 0.6
4. Store in ChromaDB for future retrieval

Based on specification section 3.2.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from siopv.domain.value_objects import EnrichmentData

if TYPE_CHECKING:
    from siopv.application.ports import (
        EPSSClientPort,
        GitHubAdvisoryClientPort,
        NVDClientPort,
        OSINTSearchClientPort,
        VectorStorePort,
    )
    from siopv.application.ports.llm_analysis import LLMAnalysisPort
    from siopv.domain.entities import VulnerabilityRecord
    from siopv.domain.value_objects import (
        EPSSScore,
        GitHubAdvisory,
        NVDEnrichment,
        OSINTResult,
    )

logger = structlog.get_logger(__name__)


# CRAG relevance threshold from specification
RELEVANCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class EnrichmentResult:
    """Result of the enrichment use case for a single CVE."""

    cve_id: str
    enrichment: EnrichmentData | None
    from_cache: bool = False
    osint_fallback_used: bool = False
    error: str | None = None


@dataclass(frozen=True)
class BatchEnrichmentResult:
    """Result of batch enrichment for multiple CVEs."""

    results: list[EnrichmentResult]
    stats: EnrichmentStats


@dataclass(frozen=True)
class EnrichmentStats:
    """Statistics from the enrichment process."""

    total_processed: int
    successful: int
    from_cache: int
    osint_fallback_count: int
    failed: int
    avg_relevance_score: float


@dataclass
class EnrichmentSources:
    """Container for enrichment data from various sources."""

    nvd: NVDEnrichment | None = None
    epss: EPSSScore | None = None
    github: GitHubAdvisory | None = None
    osint: list[OSINTResult] = field(default_factory=list)


class EnrichContextUseCase:
    """Use case for enriching vulnerability context using CRAG pattern.

    CRAG (Corrective RAG) Pattern:
    1. Retrieve context from primary sources (NVD, GitHub, EPSS)
    2. Evaluate relevance of retrieved information
    3. If relevance < threshold, trigger OSINT fallback
    4. Store enriched data in vector store
    """

    def __init__(
        self,
        nvd_client: NVDClientPort,
        epss_client: EPSSClientPort,
        github_client: GitHubAdvisoryClientPort,
        osint_client: OSINTSearchClientPort,
        vector_store: VectorStorePort,
        *,
        llm_analysis: LLMAnalysisPort | None = None,
        relevance_threshold: float = RELEVANCE_THRESHOLD,
    ):
        """Initialize enrichment use case.

        Args:
            nvd_client: NVD API client
            epss_client: EPSS API client
            github_client: GitHub Advisory client
            osint_client: Tavily OSINT client
            vector_store: ChromaDB adapter
            llm_analysis: Optional LLM analysis port for enhanced relevance scoring
            relevance_threshold: Threshold for OSINT fallback (default 0.6)
        """
        self._nvd = nvd_client
        self._epss = epss_client
        self._github = github_client
        self._osint = osint_client
        self._vector_store = vector_store
        self._llm_analysis = llm_analysis
        self._relevance_threshold = relevance_threshold

    async def execute(
        self,
        vulnerability: VulnerabilityRecord,
        *,
        skip_cache: bool = False,
    ) -> EnrichmentResult:
        """Execute enrichment for a single vulnerability.

        Args:
            vulnerability: VulnerabilityRecord to enrich
            skip_cache: If True, bypass cache and fetch fresh data

        Returns:
            EnrichmentResult with enriched data or error
        """
        cve_id = vulnerability.cve_id.value

        logger.info("enrichment_started", cve_id=cve_id)

        # Check cache first (unless skipped)
        if not skip_cache:
            cached = await self._vector_store.get_by_cve_id(cve_id)
            if cached:
                logger.info("enrichment_cache_hit", cve_id=cve_id)
                return EnrichmentResult(
                    cve_id=cve_id,
                    enrichment=cached,
                    from_cache=True,
                )

        try:
            # Step 1: Parallel retrieval from primary sources
            sources = await self._fetch_from_sources(cve_id)

            # Step 2: Calculate relevance score
            relevance_score = self._calculate_relevance(sources)

            # Step 3: OSINT fallback if relevance below threshold
            osint_used = False
            if relevance_score < self._relevance_threshold:
                logger.info(
                    "enrichment_osint_fallback",
                    cve_id=cve_id,
                    relevance=relevance_score,
                    threshold=self._relevance_threshold,
                )
                sources.osint = await self._fetch_osint_fallback(cve_id)
                osint_used = bool(sources.osint)

                # Recalculate relevance with OSINT
                if osint_used:
                    relevance_score = self._calculate_relevance(sources)

            # Step 3.5: LLM analysis (optional enhancement)
            llm_fields: dict[str, str | float | None] = {}
            if self._llm_analysis is not None:
                llm_fields = await self._run_llm_analysis(cve_id, sources, relevance_score)
                # LLM relevance overrides heuristic when available
                llm_rel = llm_fields.get("llm_relevance_assessment")
                if llm_rel is not None:
                    relevance_score = float(llm_rel)

            # Step 4: Build and store enrichment
            enrichment = self._build_enrichment(
                cve_id, sources, relevance_score, llm_fields=llm_fields
            )
            await self._vector_store.store_enrichment(enrichment)

            logger.info(
                "enrichment_complete",
                cve_id=cve_id,
                relevance=relevance_score,
                osint_used=osint_used,
                llm_used=bool(llm_fields),
            )

            return EnrichmentResult(
                cve_id=cve_id,
                enrichment=enrichment,
                osint_fallback_used=osint_used,
            )

        except Exception as e:
            logger.exception("enrichment_failed", cve_id=cve_id, error=str(e))
            return EnrichmentResult(
                cve_id=cve_id,
                enrichment=None,
                error=str(e),
            )

    async def execute_batch(
        self,
        vulnerabilities: list[VulnerabilityRecord],
        *,
        max_concurrent: int = 5,
        skip_cache: bool = False,
    ) -> BatchEnrichmentResult:
        """Execute enrichment for multiple vulnerabilities.

        Args:
            vulnerabilities: List of VulnerabilityRecord to enrich
            max_concurrent: Maximum concurrent enrichments
            skip_cache: If True, bypass cache

        Returns:
            BatchEnrichmentResult with all results and statistics
        """
        logger.info("batch_enrichment_started", count=len(vulnerabilities))

        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_one(vuln: VulnerabilityRecord) -> EnrichmentResult:
            async with semaphore:
                return await self.execute(vuln, skip_cache=skip_cache)

        tasks = [enrich_one(v) for v in vulnerabilities]
        results = await asyncio.gather(*tasks)

        # Calculate statistics
        stats = self._calculate_stats(list(results))

        logger.info(
            "batch_enrichment_complete",
            total=stats.total_processed,
            successful=stats.successful,
            failed=stats.failed,
        )

        return BatchEnrichmentResult(results=list(results), stats=stats)

    async def _fetch_from_sources(self, cve_id: str) -> EnrichmentSources:
        """Fetch enrichment data from all primary sources in parallel.

        Args:
            cve_id: CVE identifier

        Returns:
            EnrichmentSources with data from each source
        """
        # Parallel fetch from NVD, EPSS, GitHub
        nvd_task = self._safe_fetch(self._nvd.get_cve(cve_id), "nvd")
        epss_task = self._safe_fetch(self._epss.get_score(cve_id), "epss")
        github_task = self._safe_fetch(self._github.get_advisory_by_cve(cve_id), "github")

        nvd_result, epss_result, github_result = await asyncio.gather(
            nvd_task, epss_task, github_task
        )

        # _safe_fetch returns object; typed results at runtime
        return EnrichmentSources(
            nvd=nvd_result,  # type: ignore[arg-type]
            epss=epss_result,  # type: ignore[arg-type]
            github=github_result,  # type: ignore[arg-type]
        )

    async def _safe_fetch(self, coro: object, source_name: str) -> object:
        """Execute fetch with error handling.

        Args:
            coro: Coroutine to execute
            source_name: Name for logging

        Returns:
            Result or None on error
        """
        try:
            # coro typed as object; is awaitable coroutine at runtime
            return await coro  # type: ignore[misc]
        except Exception as e:
            logger.warning("enrichment_source_error", source=source_name, error=str(e))
            return None

    async def _fetch_osint_fallback(self, cve_id: str) -> list[OSINTResult]:
        """Fetch OSINT data as fallback.

        Args:
            cve_id: CVE identifier

        Returns:
            List of OSINT results
        """
        try:
            # Try exploit-specific search first
            results = await self._osint.search_exploit_info(cve_id)

            # If no exploit info, try general search
            if not results:
                results = await self._osint.search(
                    f"{cve_id} vulnerability security advisory",
                    max_results=5,
                    search_depth="advanced",
                )

        except Exception as e:
            logger.warning("osint_fallback_failed", cve_id=cve_id, error=str(e))
            return []
        else:
            return results

    def _calculate_relevance(self, sources: EnrichmentSources) -> float:
        """Calculate relevance score for retrieved data.

        Scoring:
        - NVD with description: +0.4
        - EPSS score available: +0.2
        - GitHub advisory: +0.2
        - OSINT results: +0.1 per result (max 0.2)

        Args:
            sources: EnrichmentSources with retrieved data

        Returns:
            Relevance score (0.0 to 1.0)
        """
        score = 0.0

        # NVD contribution
        if sources.nvd:
            if sources.nvd.description:
                score += 0.4
            else:
                score += 0.2

        # EPSS contribution
        if sources.epss:
            score += 0.2

        # GitHub contribution
        if sources.github:
            score += 0.2

        # OSINT contribution
        if sources.osint:
            osint_bonus = min(0.2, len(sources.osint) * 0.1)
            score += osint_bonus

        return min(1.0, score)

    async def _run_llm_analysis(
        self,
        cve_id: str,
        sources: EnrichmentSources,
        heuristic_relevance: float,
    ) -> dict[str, str | float | None]:
        """Run LLM analysis on enrichment context.

        Args:
            cve_id: CVE identifier
            sources: EnrichmentSources with retrieved data
            heuristic_relevance: Heuristic relevance score for context

        Returns:
            Dictionary with LLM analysis fields, empty on failure
        """
        context: dict[str, object] = {
            "heuristic_relevance": heuristic_relevance,
        }
        if sources.nvd and sources.nvd.description:
            context["nvd_description"] = sources.nvd.description
        if sources.epss:
            context["epss_score"] = sources.epss.score
        if sources.github and sources.github.summary:
            context["github_advisory"] = sources.github.summary
        if sources.osint:
            context["osint_results"] = [r.content for r in sources.osint]

        try:
            # self._llm_analysis is checked non-None by caller
            analysis = await self._llm_analysis.analyze_vulnerability(  # type: ignore[union-attr]
                cve_id, context
            )
        except Exception as e:
            logger.warning("llm_analysis_failed", cve_id=cve_id, error=str(e))
            return {}
        else:
            logger.info(
                "llm_analysis_complete",
                cve_id=cve_id,
                llm_relevance=analysis.relevance_assessment,
            )
            return {
                "llm_summary": analysis.summary,
                "llm_remediation": analysis.remediation_recommendation,
                "llm_relevance_assessment": analysis.relevance_assessment,
                "llm_reasoning": analysis.reasoning,
            }

    def _build_enrichment(
        self,
        cve_id: str,
        sources: EnrichmentSources,
        relevance_score: float,
        *,
        llm_fields: dict[str, str | float | None] | None = None,
    ) -> EnrichmentData:
        """Build EnrichmentData from sources.

        Args:
            cve_id: CVE identifier
            sources: EnrichmentSources with data
            relevance_score: Calculated relevance
            llm_fields: Optional LLM analysis fields to include

        Returns:
            EnrichmentData instance
        """
        kwargs: dict[str, object] = {
            "cve_id": cve_id,
            "nvd": sources.nvd,
            "epss": sources.epss,
            "github_advisory": sources.github,
            "osint_results": sources.osint,
            "relevance_score": relevance_score,
        }
        if llm_fields:
            kwargs.update(llm_fields)
        return EnrichmentData(**kwargs)  # type: ignore[arg-type]

    def _calculate_stats(self, results: list[EnrichmentResult]) -> EnrichmentStats:
        """Calculate statistics from enrichment results.

        Args:
            results: List of EnrichmentResult

        Returns:
            EnrichmentStats instance
        """
        total = len(results)
        successful = sum(1 for r in results if r.enrichment is not None)
        from_cache = sum(1 for r in results if r.from_cache)
        osint_count = sum(1 for r in results if r.osint_fallback_used)
        failed = sum(1 for r in results if r.error is not None)

        # Calculate average relevance
        relevance_scores = [
            r.enrichment.relevance_score for r in results if r.enrichment is not None
        ]
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0

        return EnrichmentStats(
            total_processed=total,
            successful=successful,
            from_cache=from_cache,
            osint_fallback_count=osint_count,
            failed=failed,
            avg_relevance_score=avg_relevance,
        )


def create_enrich_context_use_case(
    nvd_client: NVDClientPort,
    epss_client: EPSSClientPort,
    github_client: GitHubAdvisoryClientPort,
    osint_client: OSINTSearchClientPort,
    vector_store: VectorStorePort,
    *,
    llm_analysis: LLMAnalysisPort | None = None,
) -> EnrichContextUseCase:
    """Factory function to create EnrichContextUseCase.

    Args:
        nvd_client: NVD API client
        epss_client: EPSS API client
        github_client: GitHub Advisory client
        osint_client: Tavily OSINT client
        vector_store: ChromaDB adapter
        llm_analysis: Optional LLM analysis port for enhanced relevance scoring

    Returns:
        Configured EnrichContextUseCase
    """
    return EnrichContextUseCase(
        nvd_client=nvd_client,
        epss_client=epss_client,
        github_client=github_client,
        osint_client=osint_client,
        vector_store=vector_store,
        llm_analysis=llm_analysis,
    )


__all__ = [
    "BatchEnrichmentResult",
    "EnrichContextUseCase",
    "EnrichmentResult",
    "EnrichmentStats",
    "create_enrich_context_use_case",
]
