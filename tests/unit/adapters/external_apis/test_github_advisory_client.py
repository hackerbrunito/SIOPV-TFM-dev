"""Unit tests for GitHubAdvisoryClient adapter.

Coverage targets:
- get_advisory_by_cve(): happy path, cache hit, empty nodes, HTTP error, timeout,
  circuit open, GraphQL error
- get_advisories_for_package(): results, empty, circuit open (returns [])
- clear_cache()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from siopv.adapters.external_apis.github_advisory_client import (
    GitHubAdvisoryClient,
    GitHubAdvisoryClientError,
)
from siopv.domain.value_objects import GitHubAdvisory
from siopv.infrastructure.resilience import CircuitBreakerError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(*, has_token: bool = False) -> MagicMock:
    settings = MagicMock()
    settings.github_graphql_url = "https://api.github.com/graphql"
    settings.github_token = (
        MagicMock(get_secret_value=lambda: "ghp_test_token") if has_token else None
    )
    settings.github_timeout_connect = 5.0
    settings.github_timeout_read = 30.0
    settings.github_timeout_write = 5.0
    settings.github_timeout_pool = 5.0
    settings.github_rate_limit_with_token = 5000
    settings.github_rate_limit_without_token = 60
    settings.github_rate_limit_period_seconds = 3600.0
    settings.rate_limiter_max_queue_size = 100
    settings.circuit_breaker_failure_threshold = 5
    settings.circuit_breaker_recovery_timeout = 30
    settings.api_client_cache_max_size = 1000
    return settings


def _make_response(status_code: int = 200, json_data: object = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.request = MagicMock()
    response.headers = {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=response.request,
            response=response,
        )
    return response


def _advisory_graphql_payload(cve_id: str = "CVE-2021-44228") -> dict[str, object]:
    return {
        "data": {
            "securityAdvisories": {
                "nodes": [
                    {
                        "ghsaId": "GHSA-jfh8-c2jp-hdp8",
                        "summary": "Remote code execution in Log4j",
                        "severity": "CRITICAL",
                        "publishedAt": "2021-12-10T00:00:00Z",
                        "updatedAt": "2021-12-12T00:00:00Z",
                        "identifiers": [
                            {"type": "CVE", "value": cve_id},
                            {"type": "GHSA", "value": "GHSA-jfh8-c2jp-hdp8"},
                        ],
                        "vulnerabilities": {
                            "nodes": [
                                {
                                    "package": {"ecosystem": "MAVEN", "name": "log4j-core"},
                                    "vulnerableVersionRange": "< 2.15.0",
                                    "firstPatchedVersion": {"identifier": "2.15.0"},
                                }
                            ]
                        },
                    }
                ]
            }
        }
    }


def _package_graphql_payload() -> dict[str, object]:
    return {
        "data": {
            "securityVulnerabilities": {
                "nodes": [
                    {
                        "advisory": {
                            "ghsaId": "GHSA-jfh8-c2jp-hdp8",
                            "summary": "Remote code execution in Log4j",
                            "severity": "CRITICAL",
                            "publishedAt": "2021-12-10T00:00:00Z",
                            "updatedAt": "2021-12-12T00:00:00Z",
                            "identifiers": [{"type": "CVE", "value": "CVE-2021-44228"}],
                        },
                        "package": {"ecosystem": "MAVEN", "name": "log4j-core"},
                        "vulnerableVersionRange": "< 2.15.0",
                        "firstPatchedVersion": {"identifier": "2.15.0"},
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def github_client(mock_http_client: AsyncMock) -> GitHubAdvisoryClient:
    settings = _make_settings()
    with (
        patch(
            "siopv.adapters.external_apis.github_advisory_client.create_github_rate_limiter"
        ) as mock_rl,
        patch("siopv.adapters.external_apis.github_advisory_client.CircuitBreaker") as mock_cb,
    ):
        mock_rl.return_value = AsyncMock(acquire=AsyncMock())
        mock_cb_instance = MagicMock()
        mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
        mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cb.return_value = mock_cb_instance
        return GitHubAdvisoryClient(settings, client=mock_http_client)


# ---------------------------------------------------------------------------
# get_advisory_by_cve — happy path
# ---------------------------------------------------------------------------


class TestGetAdvisoryByCveHappyPath:
    @pytest.mark.asyncio
    async def test_returns_advisory(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(200, _advisory_graphql_payload())

        result = await github_client.get_advisory_by_cve("CVE-2021-44228")

        assert isinstance(result, GitHubAdvisory)
        assert result.ghsa_id == "GHSA-jfh8-c2jp-hdp8"

    @pytest.mark.asyncio
    async def test_caches_result(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(200, _advisory_graphql_payload())

        await github_client.get_advisory_by_cve("CVE-2021-44228")
        await github_client.get_advisory_by_cve("CVE-2021-44228")

        assert mock_http_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_no_nodes(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        payload: dict[str, object] = {"data": {"securityAdvisories": {"nodes": []}}}
        mock_http_client.post.return_value = _make_response(200, payload)

        result = await github_client.get_advisory_by_cve("CVE-9999-9999")

        assert result is None


# ---------------------------------------------------------------------------
# get_advisory_by_cve — error handling
# ---------------------------------------------------------------------------


class TestGetAdvisoryByCveErrors:
    @pytest.mark.asyncio
    async def test_raises_on_timeout(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.side_effect = httpx.TimeoutException("timeout")

        with pytest.raises(GitHubAdvisoryClientError, match="timeout"):
            await github_client.get_advisory_by_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_on_http_error(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(500)

        with pytest.raises(GitHubAdvisoryClientError):
            await github_client.get_advisory_by_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_on_circuit_open(self, mock_http_client: AsyncMock) -> None:
        settings = _make_settings()
        with (
            patch(
                "siopv.adapters.external_apis.github_advisory_client.create_github_rate_limiter"
            ) as mock_rl,
            patch("siopv.adapters.external_apis.github_advisory_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(side_effect=CircuitBreakerError("github_api"))
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = GitHubAdvisoryClient(settings, client=mock_http_client)

        with pytest.raises(GitHubAdvisoryClientError, match="circuit breaker open"):
            await client.get_advisory_by_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_on_graphql_errors(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        payload = {"errors": [{"message": "Unauthorized"}]}
        mock_http_client.post.return_value = _make_response(200, payload)

        with pytest.raises(GitHubAdvisoryClientError, match="GraphQL error"):
            await github_client.get_advisory_by_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_on_rate_limit_forbidden(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        response = _make_response(403)
        response.headers = {"X-RateLimit-Remaining": "0"}
        mock_http_client.post.return_value = response

        with pytest.raises(GitHubAdvisoryClientError):
            await github_client.get_advisory_by_cve("CVE-2021-44228")


# ---------------------------------------------------------------------------
# get_advisories_for_package
# ---------------------------------------------------------------------------


class TestGetAdvisoriesForPackage:
    @pytest.mark.asyncio
    async def test_returns_advisory_list(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(200, _package_graphql_payload())

        results = await github_client.get_advisories_for_package("log4j-core", ecosystem="maven")

        assert len(results) == 1
        assert isinstance(results[0], GitHubAdvisory)

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        payload: dict[str, object] = {"data": {"securityVulnerabilities": {"nodes": []}}}
        mock_http_client.post.return_value = _make_response(200, payload)

        results = await github_client.get_advisories_for_package("nonexistent-package")

        assert results == []

    @pytest.mark.asyncio
    async def test_ecosystem_mapped_correctly(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(200, _package_graphql_payload())

        await github_client.get_advisories_for_package("requests", ecosystem="pip")

        call_args = mock_http_client.post.call_args
        payload = (
            call_args.kwargs.get("json") or call_args.args[1]
            if len(call_args.args) > 1
            else call_args.kwargs["json"]
        )
        assert payload["variables"]["ecosystem"] == "PIP"

    @pytest.mark.asyncio
    async def test_returns_empty_on_circuit_open(self, mock_http_client: AsyncMock) -> None:
        settings = _make_settings()
        with (
            patch(
                "siopv.adapters.external_apis.github_advisory_client.create_github_rate_limiter"
            ) as mock_rl,
            patch("siopv.adapters.external_apis.github_advisory_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(side_effect=CircuitBreakerError("github_api"))
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = GitHubAdvisoryClient(settings, client=mock_http_client)

        results = await client.get_advisories_for_package("log4j-core")
        assert results == []


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_clear_cache(self, github_client: GitHubAdvisoryClient) -> None:
        github_client._cache["CVE-2021-44228"] = MagicMock()
        github_client.clear_cache()
        assert len(github_client._cache) == 0

    def test_with_token_stored(self) -> None:
        settings = _make_settings(has_token=True)
        with (
            patch(
                "siopv.adapters.external_apis.github_advisory_client.create_github_rate_limiter"
            ) as mock_rl,
            patch("siopv.adapters.external_apis.github_advisory_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = GitHubAdvisoryClient(settings)
        assert client._token == "ghp_test_token"


# ---------------------------------------------------------------------------
# Owned client lifecycle (lines 178-203)
# ---------------------------------------------------------------------------


class TestOwnedClient:
    @pytest.mark.asyncio
    async def test_creates_owned_client_without_external(self) -> None:
        """Test _get_client creates owned client when no external client provided."""
        settings = _make_settings(has_token=True)
        with (
            patch(
                "siopv.adapters.external_apis.github_advisory_client.create_github_rate_limiter"
            ) as mock_rl,
            patch("siopv.adapters.external_apis.github_advisory_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = GitHubAdvisoryClient(settings)

        http_client = await client._get_client()
        assert http_client is not None
        assert client._owned_client is http_client
        # Second call returns same instance
        assert await client._get_client() is http_client
        await client.close()

    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        """Test close() shuts down the owned client."""
        settings = _make_settings()
        with (
            patch(
                "siopv.adapters.external_apis.github_advisory_client.create_github_rate_limiter"
            ) as mock_rl,
            patch("siopv.adapters.external_apis.github_advisory_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = GitHubAdvisoryClient(settings)

        # Create owned client
        await client._get_client()
        assert client._owned_client is not None
        await client.close()
        assert client._owned_client is None

    @pytest.mark.asyncio
    async def test_close_noop_when_no_owned_client(
        self, github_client: GitHubAdvisoryClient
    ) -> None:
        """Test close() does nothing when using external client."""
        await github_client.close()  # Should not raise


# ---------------------------------------------------------------------------
# Unexpected error in get_advisory_by_cve (lines 315-318)
# ---------------------------------------------------------------------------


class TestGetAdvisoryByCveUnexpectedError:
    @pytest.mark.asyncio
    async def test_wraps_unexpected_exception(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        """Test unexpected exceptions are wrapped in GitHubAdvisoryClientError."""
        mock_http_client.post.side_effect = RuntimeError("unexpected failure")

        with pytest.raises(GitHubAdvisoryClientError, match="Unexpected error"):
            await github_client.get_advisory_by_cve("CVE-2024-0001")


# ---------------------------------------------------------------------------
# Error paths in get_advisories_for_package (lines 389-395)
# ---------------------------------------------------------------------------


class TestGetAdvisoriesForPackageErrors:
    @pytest.mark.asyncio
    async def test_returns_empty_on_unexpected_exception(
        self, github_client: GitHubAdvisoryClient, mock_http_client: AsyncMock
    ) -> None:
        """Test unexpected exceptions return empty list (not raise)."""
        mock_http_client.post.side_effect = RuntimeError("unexpected")

        results = await github_client.get_advisories_for_package("broken-pkg")
        assert results == []
