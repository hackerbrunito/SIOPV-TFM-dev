"""GitHub Security Advisories GraphQL API client adapter.

Implements GitHubAdvisoryClientPort for fetching security advisories.
Provides package-specific vulnerability information not available in NVD.

API Documentation: https://docs.github.com/en/graphql/reference/objects#securityadvisory
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from siopv.adapters.external_apis.base_client import BaseAPIClient
from siopv.application.ports import GitHubAdvisoryClientPort
from siopv.domain.exceptions import ExternalAPIError
from siopv.domain.value_objects import GitHubAdvisory, validate_cve_id
from siopv.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    create_github_rate_limiter,
)
from siopv.infrastructure.types import JsonDict

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


# GraphQL query for fetching advisory by CVE ID
ADVISORY_BY_CVE_QUERY = """
query GetAdvisoryByCVE($cveId: String!) {
  securityAdvisories(first: 1, identifier: {type: CVE, value: $cveId}) {
    nodes {
      ghsaId
      summary
      severity
      publishedAt
      updatedAt
      identifiers {
        type
        value
      }
      vulnerabilities(first: 5) {
        nodes {
          package {
            ecosystem
            name
          }
          vulnerableVersionRange
          firstPatchedVersion {
            identifier
          }
        }
      }
    }
  }
}
"""

# GraphQL query for fetching advisories by package
ADVISORIES_BY_PACKAGE_QUERY = """
query GetAdvisoriesByPackage($ecosystem: SecurityAdvisoryEcosystem, $package: String!) {
  securityVulnerabilities(first: 20, ecosystem: $ecosystem, package: $package) {
    nodes {
      advisory {
        ghsaId
        summary
        severity
        publishedAt
        updatedAt
        identifiers {
          type
          value
        }
      }
      package {
        ecosystem
        name
      }
      vulnerableVersionRange
      firstPatchedVersion {
        identifier
      }
    }
  }
}
"""


class GitHubAdvisoryClientError(ExternalAPIError):
    """Error from GitHub Advisory API operations."""


class GitHubAdvisoryClient(BaseAPIClient[GitHubAdvisory], GitHubAdvisoryClientPort):
    """GitHub Security Advisories GraphQL API client implementation.

    Features:
    - GraphQL API for rich advisory data
    - Token-based authentication (optional but recommended)
    - Rate limiting (60 req/h without auth, 5000 req/h with auth)
    - Circuit breaker for fault tolerance
    """

    # HTTP status codes
    HTTP_FORBIDDEN = 403

    # Ecosystem mapping for GraphQL enum
    ECOSYSTEM_MAP: ClassVar[dict[str, str]] = {
        "npm": "NPM",
        "pip": "PIP",
        "pypi": "PIP",
        "maven": "MAVEN",
        "nuget": "NUGET",
        "rubygems": "RUBYGEMS",
        "go": "GO",
        "rust": "RUST",
        "composer": "COMPOSER",
        "actions": "ACTIONS",
        "erlang": "ERLANG",
        "pub": "PUB",
        "swift": "SWIFT",
    }

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        """Initialize GitHub Advisory client.

        Args:
            settings: Application settings with GitHub configuration
            client: Optional pre-configured httpx client (for testing)
        """
        self._token = settings.github_token.get_secret_value() if settings.github_token else None

        headers = {
            "User-Agent": "SIOPV/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        super().__init__(
            timeout=httpx.Timeout(
                connect=settings.github_timeout_connect,
                read=settings.github_timeout_read,
                write=settings.github_timeout_write,
                pool=settings.github_timeout_pool,
            ),
            headers=headers,
            cache_max_size=settings.api_client_cache_max_size,
            client=client,
            follow_redirects=False,
        )

        self._graphql_url = settings.github_graphql_url

        # Configure rate limiter based on token presence
        self._rate_limiter = create_github_rate_limiter(
            has_token=bool(self._token),
            rate_with_token=settings.github_rate_limit_with_token,
            rate_without_token=settings.github_rate_limit_without_token,
            period_seconds=settings.github_rate_limit_period_seconds,
            max_queue_size=settings.rate_limiter_max_queue_size,
        )

        # Configure circuit breaker
        self._circuit_breaker = CircuitBreaker(
            "github_api",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )

        logger.info(
            "github_advisory_client_initialized",
            graphql_url=self._graphql_url,
            has_token=bool(self._token),
        )

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _execute_graphql(self, query: str, variables: dict[str, Any]) -> JsonDict:
        """Execute GraphQL query with retry logic.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data dictionary

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        client = await self._get_client()

        payload = {"query": query, "variables": variables}

        logger.debug("github_graphql_request", variables=variables)

        response = await client.post(self._graphql_url, json=payload)

        # Check for rate limiting
        if response.status_code == self.HTTP_FORBIDDEN:
            remaining = response.headers.get("X-RateLimit-Remaining", "0")
            if remaining == "0":
                logger.warning("github_rate_limit_hit")
                msg = "Rate limit exceeded"
                raise httpx.HTTPStatusError(
                    msg,
                    request=response.request,
                    response=response,
                )

        response.raise_for_status()

        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
            logger.error("github_graphql_error", error=error_msg)
            msg = f"GraphQL error: {error_msg}"
            raise GitHubAdvisoryClientError(msg)

        result: JsonDict = data.get("data", {})
        return result

    async def get_advisory_by_cve(self, cve_id: str) -> GitHubAdvisory | None:
        """Fetch GitHub Security Advisory for a CVE.

        Args:
            cve_id: CVE identifier

        Returns:
            GitHubAdvisory with package-specific info, or None if not found
        """
        validate_cve_id(cve_id)

        # Check cache first
        cached = self._cache_get(cve_id)
        if cached is not None:
            logger.debug("github_cache_hit", cve_id=cve_id)
            return cached

        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Apply circuit breaker
            async with self._circuit_breaker:
                data = await self._execute_graphql(
                    ADVISORY_BY_CVE_QUERY,
                    {"cveId": cve_id},
                )

            advisories = data.get("securityAdvisories", {}).get("nodes", [])

            if not advisories:
                logger.debug("github_advisory_not_found", cve_id=cve_id)
                return None

            # Parse and cache result
            advisory = GitHubAdvisory.from_graphql_response(advisories[0])
            self._cache_set(cve_id, advisory)

        except CircuitBreakerError:
            logger.warning("github_circuit_open", cve_id=cve_id)
            msg = f"GitHub API circuit breaker open for {cve_id}"
            raise GitHubAdvisoryClientError(msg) from None

        except httpx.TimeoutException as e:
            logger.exception("github_timeout", cve_id=cve_id, error=str(e))
            msg = f"GitHub API timeout for {cve_id}"
            raise GitHubAdvisoryClientError(msg) from e

        except httpx.HTTPStatusError as e:
            logger.exception(
                "github_http_error",
                cve_id=cve_id,
                status_code=e.response.status_code,
            )
            msg = f"GitHub API error {e.response.status_code} for {cve_id}"
            raise GitHubAdvisoryClientError(msg) from e

        except GitHubAdvisoryClientError:
            raise

        except Exception as e:
            logger.exception("github_unexpected_error", cve_id=cve_id, error=str(e))
            msg = f"Unexpected error fetching advisory for {cve_id}: {e}"
            raise GitHubAdvisoryClientError(msg) from e
        else:
            logger.info(
                "github_advisory_fetched",
                cve_id=cve_id,
                ghsa_id=advisory.ghsa_id,
            )
            return advisory

    async def get_advisories_for_package(
        self,
        package_name: str,
        ecosystem: str | None = None,
    ) -> list[GitHubAdvisory]:
        """Fetch all advisories affecting a package.

        Args:
            package_name: Package name to search
            ecosystem: Optional ecosystem filter (npm, pip, maven, etc.)

        Returns:
            List of GitHubAdvisory objects
        """
        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()

            # Map ecosystem to GraphQL enum
            graphql_ecosystem = None
            if ecosystem:
                graphql_ecosystem = self.ECOSYSTEM_MAP.get(ecosystem.lower())

            # Apply circuit breaker
            async with self._circuit_breaker:
                data = await self._execute_graphql(
                    ADVISORIES_BY_PACKAGE_QUERY,
                    {"ecosystem": graphql_ecosystem, "package": package_name},
                )

            vulnerabilities = data.get("securityVulnerabilities", {}).get("nodes", [])

            if not vulnerabilities:
                logger.debug(
                    "github_no_advisories_for_package",
                    package=package_name,
                    ecosystem=ecosystem,
                )
                return []

            # Parse results
            advisories = []
            for vuln in vulnerabilities:
                advisory_data = vuln.get("advisory", {})
                if advisory_data:
                    # Merge vulnerability info into advisory data
                    advisory_data["vulnerabilities"] = {
                        "nodes": [
                            {
                                "package": vuln.get("package"),
                                "vulnerableVersionRange": vuln.get("vulnerableVersionRange"),
                                "firstPatchedVersion": vuln.get("firstPatchedVersion"),
                            }
                        ]
                    }
                    advisory = GitHubAdvisory.from_graphql_response(advisory_data)
                    advisories.append(advisory)

        except CircuitBreakerError:
            logger.warning("github_circuit_open_package", package=package_name)
            return []

        except Exception as e:
            logger.exception(
                "github_package_error",
                package=package_name,
                error=str(e),
            )
            return []
        else:
            logger.info(
                "github_package_advisories_fetched",
                package=package_name,
                count=len(advisories),
            )
            return advisories


__all__ = ["GitHubAdvisoryClient", "GitHubAdvisoryClientError"]
