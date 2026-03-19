"""Base API client with shared HTTP client management, caching, and resilience.

Extracts common boilerplate from EPSS, NVD, and GitHub advisory clients:
- httpx.AsyncClient lifecycle (_get_client / close)
- In-memory cache with configurable max-size eviction
- Timeout construction from settings
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Generic, TypeVar

import httpx
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class BaseAPIClient(Generic[T]):
    """Base class for external API clients with shared infrastructure.

    Provides:
    - HTTP client lifecycle management (lazy creation, close)
    - In-memory cache with max-size LRU eviction
    - Timeout configuration from settings
    """

    def __init__(
        self,
        *,
        timeout: httpx.Timeout,
        headers: dict[str, str],
        cache_max_size: int,
        client: httpx.AsyncClient | None = None,
        follow_redirects: bool = True,
    ) -> None:
        self._timeout = timeout
        self._headers = headers
        self._cache_max_size = cache_max_size
        self._external_client = client
        self._owned_client: httpx.AsyncClient | None = None
        self._follow_redirects = follow_redirects
        self._cache: OrderedDict[str, T] = OrderedDict()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._external_client:
            return self._external_client

        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=self._follow_redirects,
            )

        return self._owned_client

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owned_client:
            await self._owned_client.aclose()
            self._owned_client = None

    def _cache_get(self, key: str) -> T | None:
        """Get a value from cache, returning None if not found."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _cache_set(self, key: str, value: T) -> None:
        """Set a value in cache with LRU eviction if max size exceeded."""
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_max_size:
            self._cache.popitem(last=False)

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()


__all__ = ["BaseAPIClient"]
