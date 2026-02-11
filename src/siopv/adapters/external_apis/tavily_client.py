"""Tavily Search API client adapter.

Implements OSINTSearchClientPort for OSINT fallback searches.
Used when NVD/GitHub don't provide sufficient context (CRAG pattern).

API Documentation: https://docs.tavily.com/
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

from siopv.application.ports import OSINTSearchClientPort
from siopv.domain.exceptions import ExternalAPIError
from siopv.domain.value_objects import OSINTResult
from siopv.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    RateLimiter,
)
from siopv.infrastructure.types import JsonDict

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


class TavilyClientError(ExternalAPIError):
    """Error from Tavily API operations."""


class TavilyClient(OSINTSearchClientPort):
    """Tavily Search API client implementation.

    Features:
    - Async HTTP with httpx
    - AI-optimized search results
    - Configurable search depth
    - Circuit breaker for fault tolerance
    """

    TAVILY_API_URL = "https://api.tavily.com/search"

    # HTTP status codes
    HTTP_UNAUTHORIZED = 401
    HTTP_TOO_MANY_REQUESTS = 429

    # Thresholds
    MIN_RELEVANCE_SCORE = 0.3

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        """Initialize Tavily client.

        Args:
            settings: Application settings with Tavily configuration
            client: Optional pre-configured httpx client (for testing)
        """
        self._api_key = (
            settings.tavily_api_key.get_secret_value() if settings.tavily_api_key else None
        )

        # Configure rate limiter (conservative default)
        self._rate_limiter = RateLimiter(
            "tavily_api",
            requests_per_second=1.0,  # Conservative
            burst_size=5,
        )

        # Configure circuit breaker
        self._circuit_breaker = CircuitBreaker(
            "tavily_api",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )

        # HTTP client configuration
        self._timeout = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)
        self._external_client = client
        self._owned_client: httpx.AsyncClient | None = None

        logger.info(
            "tavily_client_initialized",
            has_api_key=bool(self._api_key),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._external_client:
            return self._external_client

        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "User-Agent": "SIOPV/1.0",
                    "Content-Type": "application/json",
                },
            )

        return self._owned_client

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owned_client:
            await self._owned_client.aclose()
            self._owned_client = None

    def _is_configured(self) -> bool:
        """Check if Tavily API key is configured."""
        return self._api_key is not None

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _execute_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        include_domains: list[str] | None = None,
    ) -> list[dict[str, object]]:
        """Execute Tavily search with retry logic.

        Args:
            query: Search query
            max_results: Maximum results to return
            search_depth: "basic" or "advanced"
            include_domains: Optional domain filter

        Returns:
            List of search result dictionaries
        """
        if not self._is_configured():
            logger.warning("tavily_not_configured")
            return []

        client = await self._get_client()

        payload: JsonDict = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": False,
        }

        if include_domains:
            payload["include_domains"] = include_domains

        logger.debug("tavily_search_request", query=query[:100])

        response = await client.post(self.TAVILY_API_URL, json=payload)

        if response.status_code == self.HTTP_UNAUTHORIZED:
            logger.error("tavily_invalid_api_key")
            msg = "Invalid Tavily API key"
            raise TavilyClientError(msg)

        if response.status_code == self.HTTP_TOO_MANY_REQUESTS:
            logger.warning("tavily_rate_limit_hit")
            msg = "Rate limit exceeded"
            raise httpx.HTTPStatusError(
                msg,
                request=response.request,
                response=response,
            )

        response.raise_for_status()

        data = response.json()
        results: list[dict[str, object]] = data.get("results", [])
        return results

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> list[OSINTResult]:
        """Search for vulnerability information.

        Args:
            query: Search query (typically CVE ID + context)
            max_results: Maximum results to return
            search_depth: "basic" or "advanced" search

        Returns:
            List of OSINTResult objects with search results
        """
        if not self._is_configured():
            logger.warning("tavily_search_skipped_not_configured")
            return []

        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Apply circuit breaker
            async with self._circuit_breaker:
                raw_results = await self._execute_search(
                    query,
                    max_results=max_results,
                    search_depth=search_depth,
                )

            # Parse results
            results = [OSINTResult.from_tavily_result(r) for r in raw_results]

        except CircuitBreakerError:
            logger.warning("tavily_circuit_open", query=query[:50])
            return []

        except httpx.TimeoutException as e:
            logger.exception("tavily_timeout", query=query[:50], error=str(e))
            return []

        except httpx.HTTPStatusError as e:
            logger.exception(
                "tavily_http_error",
                query=query[:50],
                status_code=e.response.status_code,
            )
            return []

        except TavilyClientError:
            raise

        except Exception as e:
            logger.exception("tavily_unexpected_error", query=query[:50], error=str(e))
            return []
        else:
            logger.info(
                "tavily_search_complete",
                query=query[:50],
                results_count=len(results),
            )
            return results

    async def search_exploit_info(self, cve_id: str) -> list[OSINTResult]:
        """Search specifically for exploit information.

        Constructs targeted query for PoC, exploits, and attack vectors.

        Args:
            cve_id: CVE identifier

        Returns:
            List of OSINTResult objects
        """
        # Construct exploit-focused query
        query = f"{cve_id} exploit proof of concept PoC attack"

        # Use security-focused domains
        security_domains = [
            "exploit-db.com",
            "github.com",
            "packetstormsecurity.com",
            "cvedetails.com",
            "vuldb.com",
            "rapid7.com",
            "tenable.com",
        ]

        if not self._is_configured():
            logger.warning("tavily_exploit_search_skipped_not_configured")
            return []

        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Apply circuit breaker
            async with self._circuit_breaker:
                raw_results = await self._execute_search(
                    query,
                    max_results=10,
                    search_depth="advanced",
                    include_domains=security_domains,
                )

            # Parse and filter results
            results = []
            for r in raw_results:
                result = OSINTResult.from_tavily_result(r)
                # Only include results with reasonable relevance
                if result.score >= self.MIN_RELEVANCE_SCORE:
                    results.append(result)

        except CircuitBreakerError:
            logger.warning("tavily_circuit_open_exploit", cve_id=cve_id)
            return []

        except Exception as e:
            logger.exception("tavily_exploit_search_error", cve_id=cve_id, error=str(e))
            return []
        else:
            logger.info(
                "tavily_exploit_search_complete",
                cve_id=cve_id,
                results_count=len(results),
            )
            return results


__all__ = ["TavilyClient", "TavilyClientError"]
