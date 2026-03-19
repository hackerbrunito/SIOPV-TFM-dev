"""NVD (National Vulnerability Database) API client adapter.

Implements NVDClientPort for fetching CVE details from NVD API 2.0.
Includes rate limiting, circuit breaker, and caching.

API Documentation: https://nvd.nist.gov/developers/vulnerabilities
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from siopv.adapters.external_apis.base_client import BaseAPIClient
from siopv.application.ports import NVDClientPort
from siopv.domain.exceptions import ExternalAPIError
from siopv.domain.value_objects import NVDEnrichment, validate_cve_id
from siopv.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    create_nvd_rate_limiter,
)
from siopv.infrastructure.types import JsonDict

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


class NVDClientError(ExternalAPIError):
    """Error from NVD API operations."""


class NVDClient(BaseAPIClient[NVDEnrichment], NVDClientPort):
    """NVD API 2.0 client implementation.

    Features:
    - Async HTTP with httpx
    - Rate limiting (5 req/30s without key, 50 req/30s with key)
    - Circuit breaker for fault tolerance
    - Retry with exponential backoff
    - Response caching (in-memory with LRU eviction)
    """

    # HTTP status codes
    HTTP_NOT_FOUND = 404
    HTTP_FORBIDDEN = 403

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        """Initialize NVD client.

        Args:
            settings: Application settings with NVD configuration
            client: Optional pre-configured httpx client (for testing)
        """
        self._api_key = settings.nvd_api_key.get_secret_value() if settings.nvd_api_key else None

        headers = {"User-Agent": "SIOPV/1.0"}
        if self._api_key:
            headers["apiKey"] = self._api_key

        super().__init__(
            timeout=httpx.Timeout(
                connect=settings.nvd_timeout_connect,
                read=settings.nvd_timeout_read,
                write=settings.nvd_timeout_write,
                pool=settings.nvd_timeout_pool,
            ),
            headers=headers,
            cache_max_size=settings.api_client_cache_max_size,
            client=client,
        )

        self._base_url = settings.nvd_base_url
        self._max_concurrent = settings.nvd_max_concurrent

        # Configure rate limiter based on API key presence
        self._rate_limiter = create_nvd_rate_limiter(
            has_api_key=bool(self._api_key),
            rate_with_key=settings.nvd_rate_limit_with_key,
            rate_without_key=settings.nvd_rate_limit_without_key,
            period_seconds=settings.nvd_rate_limit_period_seconds,
            max_queue_size=settings.rate_limiter_max_queue_size,
        )

        # Configure circuit breaker
        self._circuit_breaker = CircuitBreaker(
            "nvd_api",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )

        logger.info(
            "nvd_client_initialized",
            base_url=self._base_url,
            has_api_key=bool(self._api_key),
        )

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch_cve(self, cve_id: str) -> JsonDict | None:
        """Fetch CVE data from NVD API with retry logic.

        Args:
            cve_id: CVE identifier

        Returns:
            CVE data dictionary or None if not found
        """
        client = await self._get_client()
        url = f"{self._base_url}?cveId={cve_id}"

        logger.debug("nvd_api_request", cve_id=cve_id)

        response = await client.get(url)

        if response.status_code == self.HTTP_NOT_FOUND:
            logger.debug("nvd_cve_not_found", cve_id=cve_id)
            return None

        if response.status_code == self.HTTP_FORBIDDEN:
            logger.warning("nvd_rate_limit_hit", cve_id=cve_id)
            msg = "Rate limit exceeded"
            raise httpx.HTTPStatusError(
                msg,
                request=response.request,
                response=response,
            )

        response.raise_for_status()

        data: JsonDict = response.json()
        vulnerabilities: list[JsonDict] = data.get("vulnerabilities", [])

        if not vulnerabilities:
            return None

        result: JsonDict = vulnerabilities[0]
        return result

    async def get_cve(self, cve_id: str) -> NVDEnrichment | None:
        """Fetch CVE details from NVD API.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2021-44228")

        Returns:
            NVDEnrichment with CVE details, or None if not found

        Raises:
            NVDClientError: On API errors after retries exhausted
        """
        validate_cve_id(cve_id)

        # Check cache first
        cached = self._cache_get(cve_id)
        if cached is not None:
            logger.debug("nvd_cache_hit", cve_id=cve_id)
            return cached

        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Apply circuit breaker
            async with self._circuit_breaker:
                data = await self._fetch_cve(cve_id)

            if data is None:
                return None

            # Parse and cache result
            enrichment = NVDEnrichment.from_nvd_response(data)
            self._cache_set(cve_id, enrichment)

        except CircuitBreakerError:
            logger.warning("nvd_circuit_open", cve_id=cve_id)
            msg = f"NVD API circuit breaker open for {cve_id}"
            raise NVDClientError(msg) from None

        except httpx.TimeoutException as e:
            logger.exception("nvd_timeout", cve_id=cve_id, error=str(e))
            msg = f"NVD API timeout for {cve_id}"
            raise NVDClientError(msg) from e

        except httpx.HTTPStatusError as e:
            logger.exception(
                "nvd_http_error",
                cve_id=cve_id,
                status_code=e.response.status_code,
            )
            msg = f"NVD API error {e.response.status_code} for {cve_id}"
            raise NVDClientError(msg) from e

        except Exception as e:
            logger.exception("nvd_unexpected_error", cve_id=cve_id, error=str(e))
            msg = f"Unexpected error fetching {cve_id}: {e}"
            raise NVDClientError(msg) from e
        else:
            logger.info("nvd_cve_fetched", cve_id=cve_id)
            return enrichment

    async def get_cves_batch(
        self, cve_ids: list[str], *, max_concurrent: int | None = None
    ) -> dict[str, NVDEnrichment | None]:
        """Fetch multiple CVEs with rate limiting.

        Args:
            cve_ids: List of CVE identifiers
            max_concurrent: Maximum concurrent requests (defaults to settings value)

        Returns:
            Dictionary mapping cve_id to NVDEnrichment or None
        """
        concurrency = max_concurrent if max_concurrent is not None else self._max_concurrent
        results: dict[str, NVDEnrichment | None] = {}
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(cve_id: str) -> tuple[str, NVDEnrichment | None]:
            async with semaphore:
                try:
                    enrichment = await self.get_cve(cve_id)
                except NVDClientError:
                    return cve_id, None
                else:
                    return cve_id, enrichment

        tasks = [fetch_one(cve_id) for cve_id in cve_ids]
        completed = await asyncio.gather(*tasks)

        for cve_id, enrichment in completed:
            results[cve_id] = enrichment

        logger.info(
            "nvd_batch_complete",
            total=len(cve_ids),
            successful=sum(1 for v in results.values() if v is not None),
        )

        return results

    async def health_check(self) -> bool:
        """Check if NVD API is reachable.

        Returns:
            True if API responds, False otherwise
        """
        try:
            client = await self._get_client()
            # Use a known CVE for health check, reuse configured timeout
            response = await client.get(
                f"{self._base_url}?cveId=CVE-2021-44228",
                timeout=self._timeout,
            )
        except Exception as e:
            logger.warning("nvd_health_check_failed", error=str(e))
            return False
        else:
            return response.status_code in (200, 404)


__all__ = ["NVDClient", "NVDClientError"]
