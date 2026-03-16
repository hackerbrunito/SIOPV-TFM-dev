"""Unit tests for TavilyClient adapter.

Coverage targets:
- search(): not configured returns [], happy path, timeout returns [], HTTP error returns [],
            circuit open returns [], rate-limit (429) raises HTTPStatusError → returns []
- search_exploit_info(): not configured, happy path with relevance filter, circuit open
- _is_configured(): with/without API key
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from siopv.adapters.external_apis.tavily_client import TavilyClient, TavilyClientError
from siopv.domain.value_objects import OSINTResult
from siopv.infrastructure.resilience import CircuitBreakerError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(*, has_api_key: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.tavily_api_key = (
        MagicMock(get_secret_value=lambda: "tvly-test-key") if has_api_key else None
    )
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


def _tavily_payload(n: int = 2, score: float = 0.8) -> dict[str, object]:
    return {
        "results": [
            {
                "url": f"https://example.com/result-{i}",
                "title": f"Result {i}",
                "content": f"CVE description {i}",
                "score": score,
            }
            for i in range(n)
        ]
    }


@pytest.fixture
def mock_http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


def _make_tavily_client(
    mock_http_client: AsyncMock,
    *,
    has_api_key: bool = True,
    circuit_open: bool = False,
) -> TavilyClient:
    settings = _make_settings(has_api_key=has_api_key)
    with (
        patch("siopv.adapters.external_apis.tavily_client.RateLimiter") as mock_rl,
        patch("siopv.adapters.external_apis.tavily_client.CircuitBreaker") as mock_cb,
    ):
        mock_rl.return_value = AsyncMock(acquire=AsyncMock())
        mock_cb_instance = MagicMock()
        if circuit_open:
            mock_cb_instance.__aenter__ = AsyncMock(side_effect=CircuitBreakerError("tavily_api"))
        else:
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
        mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
        mock_cb.return_value = mock_cb_instance
        return TavilyClient(settings, client=mock_http_client)


@pytest.fixture
def tavily_client(mock_http_client: AsyncMock) -> TavilyClient:
    return _make_tavily_client(mock_http_client)


# ---------------------------------------------------------------------------
# _is_configured
# ---------------------------------------------------------------------------


class TestIsConfigured:
    def test_configured_with_key(self, mock_http_client: AsyncMock) -> None:
        client = _make_tavily_client(mock_http_client, has_api_key=True)
        assert client._is_configured() is True

    def test_not_configured_without_key(self, mock_http_client: AsyncMock) -> None:
        client = _make_tavily_client(mock_http_client, has_api_key=False)
        assert client._is_configured() is False


# ---------------------------------------------------------------------------
# search — happy path
# ---------------------------------------------------------------------------


class TestSearchHappyPath:
    @pytest.mark.asyncio
    async def test_returns_osint_results(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(200, _tavily_payload())

        results = await tavily_client.search("CVE-2021-44228")

        assert len(results) == 2
        assert all(isinstance(r, OSINTResult) for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_results(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(200, {"results": []})

        results = await tavily_client.search("CVE-2021-44228")

        assert results == []


# ---------------------------------------------------------------------------
# search — not configured
# ---------------------------------------------------------------------------


class TestSearchNotConfigured:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_api_key(self, mock_http_client: AsyncMock) -> None:
        client = _make_tavily_client(mock_http_client, has_api_key=False)

        results = await client.search("CVE-2021-44228")

        assert results == []
        mock_http_client.post.assert_not_called()


# ---------------------------------------------------------------------------
# search — error handling
# ---------------------------------------------------------------------------


class TestSearchErrors:
    @pytest.mark.asyncio
    async def test_returns_empty_on_timeout(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.side_effect = httpx.TimeoutException("timeout")

        results = await tavily_client.search("CVE-2021-44228")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_500(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(500)

        results = await tavily_client.search("CVE-2021-44228")

        assert results == []

    @pytest.mark.asyncio
    async def test_raises_on_401_invalid_key(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(401)

        with pytest.raises(TavilyClientError, match="Invalid Tavily API key"):
            await tavily_client.search("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_returns_empty_on_circuit_open(self, mock_http_client: AsyncMock) -> None:
        client = _make_tavily_client(mock_http_client, circuit_open=True)

        results = await client.search("CVE-2021-44228")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_429_rate_limit(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value = _make_response(429)

        results = await tavily_client.search("CVE-2021-44228")

        assert results == []


# ---------------------------------------------------------------------------
# search_exploit_info
# ---------------------------------------------------------------------------


class TestSearchExploitInfo:
    @pytest.mark.asyncio
    async def test_returns_filtered_results_above_threshold(
        self, tavily_client: TavilyClient, mock_http_client: AsyncMock
    ) -> None:
        # Mix of high-score and low-score results
        payload = {
            "results": [
                {
                    "url": "https://exploit-db.com/e1",
                    "title": "Exploit",
                    "content": "PoC",
                    "score": 0.9,
                },
                {
                    "url": "https://example.com/low",
                    "title": "Low",
                    "content": "unrelated",
                    "score": 0.1,
                },
            ]
        }
        mock_http_client.post.return_value = _make_response(200, payload)

        results = await tavily_client.search_exploit_info("CVE-2021-44228")

        # Only result with score >= 0.3 should be included
        assert len(results) == 1
        assert all(r.score >= tavily_client.MIN_RELEVANCE_SCORE for r in results)

    @pytest.mark.asyncio
    async def test_returns_empty_when_not_configured(self, mock_http_client: AsyncMock) -> None:
        client = _make_tavily_client(mock_http_client, has_api_key=False)

        results = await client.search_exploit_info("CVE-2021-44228")

        assert results == []
        mock_http_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_on_circuit_open(self, mock_http_client: AsyncMock) -> None:
        client = _make_tavily_client(mock_http_client, circuit_open=True)

        results = await client.search_exploit_info("CVE-2021-44228")

        assert results == []


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        settings = _make_settings()
        with (
            patch("siopv.adapters.external_apis.tavily_client.RateLimiter") as mock_rl,
            patch("siopv.adapters.external_apis.tavily_client.CircuitBreaker") as mock_cb,
        ):
            mock_rl.return_value = AsyncMock(acquire=AsyncMock())
            mock_cb_instance = MagicMock()
            mock_cb_instance.__aenter__ = AsyncMock(return_value=None)
            mock_cb_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cb.return_value = mock_cb_instance
            client = TavilyClient(settings)

        mock_owned = AsyncMock()
        client._owned_client = mock_owned

        await client.close()

        mock_owned.aclose.assert_awaited_once()
        assert client._owned_client is None
