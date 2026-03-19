"""Unit tests for EPSSClient adapter.

Coverage targets:
- get_score(): happy path, cache hit, not found (empty data), timeout, HTTP error, circuit open
- get_scores_batch(): all cached, partial fetch, circuit open (returns partial), chunk logic
- clear_cache()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from siopv.adapters.external_apis.epss_client import EPSSClient, EPSSClientError
from siopv.domain.value_objects import EPSSScore
from siopv.infrastructure.resilience import CircuitBreakerError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.epss_base_url = "https://api.first.org/data/v1/epss"
    settings.epss_timeout_connect = 5.0
    settings.epss_timeout_read = 15.0
    settings.epss_timeout_write = 5.0
    settings.epss_timeout_pool = 5.0
    settings.epss_batch_chunk_size = 100
    settings.epss_rate_limit_rps = 10.0
    settings.epss_burst_size = 20
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
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=response.request,
            response=response,
        )
    return response


def _epss_payload(cve_id: str = "CVE-2021-44228") -> dict[str, object]:
    return {
        "status": "OK",
        "data": [{"cve": cve_id, "epss": "0.97565", "percentile": "0.99986", "date": "2024-01-01"}],
    }


@pytest.fixture
def mock_http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def epss_client(mock_http_client: AsyncMock) -> EPSSClient:
    settings = _make_settings()
    with (
        patch("siopv.adapters.external_apis.epss_client.create_epss_rate_limiter") as mock_rl,
        patch("siopv.adapters.external_apis.epss_client.CircuitBreaker") as mock_cb,
    ):
        mock_rl.return_value = AsyncMock(acquire=AsyncMock())
        mock_cb_instance = MagicMock()
        mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
        mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cb.return_value = mock_cb_instance
        return EPSSClient(settings, client=mock_http_client)


# ---------------------------------------------------------------------------
# get_score — happy path
# ---------------------------------------------------------------------------


class TestGetScoreHappyPath:
    @pytest.mark.asyncio
    async def test_returns_epss_score(
        self, epss_client: EPSSClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, _epss_payload())

        result = await epss_client.get_score("CVE-2021-44228")

        assert isinstance(result, EPSSScore)
        assert abs(result.score - 0.97565) < 1e-5
        assert abs(result.percentile - 0.99986) < 1e-5

    @pytest.mark.asyncio
    async def test_caches_result(
        self, epss_client: EPSSClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, _epss_payload())

        await epss_client.get_score("CVE-2021-44228")
        await epss_client.get_score("CVE-2021-44228")

        assert mock_http_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, epss_client: EPSSClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, {"status": "OK", "data": []})

        result = await epss_client.get_score("CVE-9999-9999")

        assert result is None


# ---------------------------------------------------------------------------
# get_score — error handling
# ---------------------------------------------------------------------------


class TestGetScoreErrors:
    @pytest.mark.asyncio
    async def test_raises_on_timeout(
        self, epss_client: EPSSClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(EPSSClientError, match="timeout"):
            await epss_client.get_score("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_on_http_error(
        self, epss_client: EPSSClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(500)

        with pytest.raises(EPSSClientError):
            await epss_client.get_score("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_raises_on_circuit_open(self, mock_http_client: AsyncMock) -> None:
        settings = _make_settings()
        with (
            patch("siopv.adapters.external_apis.epss_client.create_epss_rate_limiter") as mock_rl,
            patch("siopv.adapters.external_apis.epss_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(side_effect=CircuitBreakerError("epss_api"))
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = EPSSClient(settings, client=mock_http_client)

        with pytest.raises(EPSSClientError, match="circuit breaker open"):
            await client.get_score("CVE-2021-44228")


# ---------------------------------------------------------------------------
# get_scores_batch
# ---------------------------------------------------------------------------


class TestGetScoresBatch:
    @pytest.mark.asyncio
    async def test_returns_all_cached(self, epss_client: EPSSClient) -> None:
        cve_id = "CVE-2021-44228"
        score = EPSSScore(score=0.5, percentile=0.8)
        epss_client._cache[cve_id] = score

        results = await epss_client.get_scores_batch([cve_id])

        assert results[cve_id] == score

    @pytest.mark.asyncio
    async def test_fetches_uncached(
        self, epss_client: EPSSClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.get.return_value = _make_response(200, _epss_payload())

        results = await epss_client.get_scores_batch(["CVE-2021-44228"])

        assert "CVE-2021-44228" in results
        assert isinstance(results["CVE-2021-44228"], EPSSScore)

    @pytest.mark.asyncio
    async def test_circuit_open_returns_partial(self, mock_http_client: AsyncMock) -> None:
        settings = _make_settings()
        with (
            patch("siopv.adapters.external_apis.epss_client.create_epss_rate_limiter") as mock_rl,
            patch("siopv.adapters.external_apis.epss_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(side_effect=CircuitBreakerError("epss_api"))
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = EPSSClient(settings, client=mock_http_client)

        # Should not raise; returns dict with None values
        results = await client.get_scores_batch(["CVE-2021-44228"])
        assert "CVE-2021-44228" in results
        assert results["CVE-2021-44228"] is None

    @pytest.mark.asyncio
    async def test_empty_list(self, epss_client: EPSSClient) -> None:
        results = await epss_client.get_scores_batch([])
        assert results == {}


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_clear_cache(self, epss_client: EPSSClient) -> None:
        epss_client._cache["CVE-2021-44228"] = MagicMock()
        epss_client.clear_cache()
        assert len(epss_client._cache) == 0

    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        settings = _make_settings()
        with (
            patch("siopv.adapters.external_apis.epss_client.create_epss_rate_limiter") as mock_rl,
            patch("siopv.adapters.external_apis.epss_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = EPSSClient(settings)

        mock_owned = AsyncMock()
        client._owned_client = mock_owned

        await client.close()

        mock_owned.aclose.assert_awaited_once()
        assert client._owned_client is None
