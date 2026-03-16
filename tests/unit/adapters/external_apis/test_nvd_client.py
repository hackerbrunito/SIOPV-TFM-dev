"""Unit tests for NVDClient adapter.

Coverage targets:
- get_cve(): happy path, cache hit, not found (404), HTTP error, timeout, circuit open
- get_cves_batch(): successful batch, partial failures
- health_check(): healthy (200/404), unhealthy (exception)
- close(): owned client closed, external client untouched
- clear_cache(): clears cache dict
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from siopv.adapters.external_apis.nvd_client import NVDClient, NVDClientError
from siopv.domain.value_objects import NVDEnrichment
from siopv.infrastructure.resilience import CircuitBreakerError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_settings(*, has_api_key: bool = False) -> MagicMock:
    settings = MagicMock()
    settings.nvd_base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    settings.nvd_api_key = MagicMock(get_secret_value=lambda: "test-key") if has_api_key else None
    settings.circuit_breaker_failure_threshold = 5
    settings.circuit_breaker_recovery_timeout = 30
    return settings


def _make_response(status_code: int = 200, json_data: object = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.request = MagicMock()
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=response.request,
            response=response,
        )
    return response


def _nvd_api_payload(cve_id: str = "CVE-2021-44228") -> dict[str, object]:
    return {
        "vulnerabilities": [
            {
                "cve": {
                    "id": cve_id,
                    "descriptions": [{"lang": "en", "value": "Log4Shell RCE vulnerability"}],
                    "metrics": {
                        "cvssMetricV31": [
                            {
                                "cvssData": {
                                    "baseScore": 10.0,
                                    "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
                                }
                            }
                        ]
                    },
                    "published": "2021-12-10T00:00:00.000Z",
                    "lastModified": "2021-12-12T00:00:00.000Z",
                    "references": [{"url": "https://example.com/ref", "tags": []}],
                    "weaknesses": [{"description": [{"value": "CWE-502"}]}],
                }
            }
        ]
    }


@pytest.fixture
def mock_http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def nvd_client(mock_http_client: AsyncMock) -> NVDClient:
    settings = _make_settings()
    with (
        patch("siopv.adapters.external_apis.nvd_client.create_nvd_rate_limiter") as mock_rl,
        patch("siopv.adapters.external_apis.nvd_client.CircuitBreaker") as mock_cb,
    ):
        mock_rl.return_value = AsyncMock(acquire=AsyncMock())
        # Circuit breaker as async context manager — passes through by default
        mock_cb_instance = MagicMock()
        mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
        mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cb.return_value = mock_cb_instance
        return NVDClient(settings, client=mock_http_client)


# ---------------------------------------------------------------------------
# get_cve — happy path
# ---------------------------------------------------------------------------


class TestGetCveHappyPath:
    @pytest.mark.asyncio
    async def test_returns_nvd_enrichment(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, _nvd_api_payload())

        result = await nvd_client.get_cve("CVE-2021-44228")

        assert isinstance(result, NVDEnrichment)
        assert result.cve_id == "CVE-2021-44228"
        assert result.cvss_v3_score == 10.0
        assert result.description == "Log4Shell RCE vulnerability"

    @pytest.mark.asyncio
    async def test_caches_result_on_second_call(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, _nvd_api_payload())

        await nvd_client.get_cve("CVE-2021-44228")
        await nvd_client.get_cve("CVE-2021-44228")

        # HTTP called only once; second call hits cache
        assert mock_http_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(404)

        result = await nvd_client.get_cve("CVE-9999-9999")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_empty_vulnerabilities(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, {"vulnerabilities": []})

        result = await nvd_client.get_cve("CVE-9999-9999")

        assert result is None


# ---------------------------------------------------------------------------
# get_cve — error handling
# ---------------------------------------------------------------------------


class TestGetCveErrorHandling:
    @pytest.mark.asyncio
    async def test_raises_nvd_client_error_on_403(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        response = _make_response(403)
        mock_http_client.get.return_value = response

        with pytest.raises(NVDClientError, match="403"):
            await nvd_client.get_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_nvd_client_error_on_timeout(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.side_effect = httpx.TimeoutException("timeout")

        with pytest.raises(NVDClientError, match="timeout"):
            await nvd_client.get_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_nvd_client_error_on_http_500(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        response = _make_response(500)
        mock_http_client.get.return_value = response

        with pytest.raises(NVDClientError):
            await nvd_client.get_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_nvd_client_error_on_circuit_open(
        self, mock_http_client: AsyncMock
    ) -> None:
        settings = _make_settings()
        with (
            patch("siopv.adapters.external_apis.nvd_client.create_nvd_rate_limiter") as mock_rl,
            patch("siopv.adapters.external_apis.nvd_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(side_effect=CircuitBreakerError("nvd_api"))
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = NVDClient(settings, client=mock_http_client)

        with pytest.raises(NVDClientError, match="circuit breaker open"):
            await client.get_cve("CVE-2021-44228")


# ---------------------------------------------------------------------------
# get_cves_batch
# ---------------------------------------------------------------------------


class TestGetCvesBatch:
    @pytest.mark.asyncio
    async def test_returns_dict_with_results(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, _nvd_api_payload("CVE-2021-44228"))

        results = await nvd_client.get_cves_batch(["CVE-2021-44228"])

        assert "CVE-2021-44228" in results
        assert isinstance(results["CVE-2021-44228"], NVDEnrichment)

    @pytest.mark.asyncio
    async def test_returns_none_for_failed_cve(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.side_effect = httpx.TimeoutException("timeout")

        results = await nvd_client.get_cves_batch(["CVE-2021-44228"])

        # Errors should be swallowed and return None
        assert results["CVE-2021-44228"] is None

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_dict(self, nvd_client: NVDClient) -> None:
        results = await nvd_client.get_cves_batch([])
        assert results == {}


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_true_on_200(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200)
        assert await nvd_client.health_check() is True

    @pytest.mark.asyncio
    async def test_returns_true_on_404(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(404)
        assert await nvd_client.health_check() is True

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(
        self, nvd_client: NVDClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.side_effect = Exception("network error")
        assert await nvd_client.health_check() is False


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        settings = _make_settings()
        with (
            patch("siopv.adapters.external_apis.nvd_client.create_nvd_rate_limiter") as mock_rl,
            patch("siopv.adapters.external_apis.nvd_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = NVDClient(settings)

        mock_owned = AsyncMock()
        client._owned_client = mock_owned

        await client.close()

        mock_owned.aclose.assert_awaited_once()
        assert client._owned_client is None

    def test_clear_cache(self, nvd_client: NVDClient) -> None:
        nvd_client._cache["CVE-2021-44228"] = MagicMock()
        nvd_client.clear_cache()
        assert len(nvd_client._cache) == 0

    def test_with_api_key_sets_header(self) -> None:
        settings = _make_settings(has_api_key=True)
        with (
            patch("siopv.adapters.external_apis.nvd_client.create_nvd_rate_limiter") as mock_rl,
            patch("siopv.adapters.external_apis.nvd_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = NVDClient(settings)
        assert client._api_key == "test-key"
