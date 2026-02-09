"""FIRST EPSS (Exploit Prediction Scoring System) API client adapter.

Implements EPSSClientPort for fetching exploit probability scores.
EPSS provides daily-updated probability of exploitation within 30 days.

API Documentation: https://www.first.org/epss/api
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from siopv.application.ports import EPSSClientPort
from siopv.domain.exceptions import ExternalAPIError
from siopv.domain.value_objects import EPSSScore
from siopv.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    create_epss_rate_limiter,
)
from siopv.infrastructure.types import JsonDict

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


class EPSSClientError(ExternalAPIError):
    """Error from EPSS API operations."""


class EPSSClient(EPSSClientPort):
    """FIRST EPSS API client implementation.

    Features:
    - Async HTTP with httpx
    - Batch queries for efficiency
    - Circuit breaker for fault tolerance
    - No authentication required
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        """Initialize EPSS client.

        Args:
            settings: Application settings with EPSS configuration
            client: Optional pre-configured httpx client (for testing)
        """
        self._base_url = settings.epss_base_url

        # Configure rate limiter (conservative, no documented limit)
        self._rate_limiter = create_epss_rate_limiter()

        # Configure circuit breaker
        self._circuit_breaker = CircuitBreaker(
            "epss_api",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )

        # HTTP client configuration
        self._timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
        self._external_client = client
        self._owned_client: httpx.AsyncClient | None = None

        # Simple in-memory cache
        self._cache: dict[str, EPSSScore] = {}

        logger.info("epss_client_initialized", base_url=self._base_url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._external_client:
            return self._external_client

        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": "SIOPV/1.0", "Accept": "application/json"},
                follow_redirects=True,
            )

        return self._owned_client

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owned_client:
            await self._owned_client.aclose()
            self._owned_client = None

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )  # type: ignore[misc]
    async def _fetch_epss(self, cve_id: str) -> JsonDict | None:
        """Fetch EPSS data from API with retry logic.

        Args:
            cve_id: CVE identifier

        Returns:
            EPSS data dictionary or None if not found
        """
        client = await self._get_client()
        url = f"{self._base_url}?cve={cve_id}"

        logger.debug("epss_api_request", cve_id=cve_id)

        response = await client.get(url)
        response.raise_for_status()

        data: JsonDict = response.json()
        epss_data: list[JsonDict] = data.get("data", [])

        if not epss_data:
            logger.debug("epss_cve_not_found", cve_id=cve_id)
            return None

        result: JsonDict = epss_data[0]
        return result

    async def get_score(self, cve_id: str) -> EPSSScore | None:
        """Fetch EPSS score for a CVE.

        Args:
            cve_id: CVE identifier

        Returns:
            EPSSScore with probability and percentile, or None if not found
        """
        # Check cache first
        if cve_id in self._cache:
            logger.debug("epss_cache_hit", cve_id=cve_id)
            return self._cache[cve_id]

        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Apply circuit breaker
            async with self._circuit_breaker:
                data = await self._fetch_epss(cve_id)

            if data is None:
                return None

            # Parse and cache result
            score = EPSSScore.from_api_response(data)
            self._cache[cve_id] = score

        except CircuitBreakerError:
            logger.warning("epss_circuit_open", cve_id=cve_id)
            msg = f"EPSS API circuit breaker open for {cve_id}"
            raise EPSSClientError(msg) from None

        except httpx.TimeoutException as e:
            logger.exception("epss_timeout", cve_id=cve_id, error=str(e))
            msg = f"EPSS API timeout for {cve_id}"
            raise EPSSClientError(msg) from e

        except httpx.HTTPStatusError as e:
            logger.exception(
                "epss_http_error",
                cve_id=cve_id,
                status_code=e.response.status_code,
            )
            msg = f"EPSS API error {e.response.status_code} for {cve_id}"
            raise EPSSClientError(msg) from e

        except Exception as e:
            logger.exception("epss_unexpected_error", cve_id=cve_id, error=str(e))
            msg = f"Unexpected error fetching EPSS for {cve_id}: {e}"
            raise EPSSClientError(msg) from e
        else:
            logger.info(
                "epss_score_fetched",
                cve_id=cve_id,
                score=score.score,
                percentile=score.percentile,
            )
            return score

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )  # type: ignore[misc]
    async def _fetch_epss_batch(self, cve_ids: list[str]) -> list[JsonDict]:
        """Fetch EPSS data for multiple CVEs in a single request.

        The EPSS API supports comma-separated CVE IDs for batch queries.

        Args:
            cve_ids: List of CVE identifiers

        Returns:
            List of EPSS data dictionaries
        """
        client = await self._get_client()
        # EPSS API accepts comma-separated CVE IDs
        cve_param = ",".join(cve_ids)
        url = f"{self._base_url}?cve={cve_param}"

        logger.debug("epss_batch_request", count=len(cve_ids))

        response = await client.get(url)
        response.raise_for_status()

        data: JsonDict = response.json()
        result: list[JsonDict] = data.get("data", [])
        return result

    async def get_scores_batch(self, cve_ids: list[str]) -> dict[str, EPSSScore | None]:
        """Fetch EPSS scores for multiple CVEs.

        Uses batch API for efficiency.

        Args:
            cve_ids: List of CVE identifiers

        Returns:
            Dictionary mapping cve_id to EPSSScore or None
        """
        results: dict[str, EPSSScore | None] = {}

        # Check cache first
        uncached_ids = []
        for cve_id in cve_ids:
            if cve_id in self._cache:
                results[cve_id] = self._cache[cve_id]
            else:
                uncached_ids.append(cve_id)
                results[cve_id] = None  # Default to None

        if not uncached_ids:
            logger.debug("epss_batch_all_cached", count=len(cve_ids))
            return results

        try:
            # Apply rate limiting (count as single request)
            await self._rate_limiter.acquire()

            # Apply circuit breaker
            async with self._circuit_breaker:
                # Batch in chunks of 100 (API limit)
                chunk_size = 100
                for i in range(0, len(uncached_ids), chunk_size):
                    chunk = uncached_ids[i : i + chunk_size]
                    epss_data = await self._fetch_epss_batch(chunk)

                    # Process results
                    for item in epss_data:
                        cve_id_value: str | None = item.get("cve")
                        if cve_id_value:
                            score = EPSSScore.from_api_response(item)
                            self._cache[cve_id_value] = score
                            results[cve_id_value] = score

            logger.info(
                "epss_batch_complete",
                total=len(cve_ids),
                fetched=sum(1 for v in results.values() if v is not None),
            )

        except CircuitBreakerError:
            logger.warning("epss_circuit_open_batch")

        except Exception as e:
            logger.exception("epss_batch_error", error=str(e))

        return results

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.debug("epss_cache_cleared")


__all__ = ["EPSSClient", "EPSSClientError"]
