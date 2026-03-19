"""Rate limiter implementation using Token Bucket algorithm.

Coordinates API calls to respect rate limits:
- NVD: 5 req/30s (without key), 50 req/30s (with key)
- GitHub: 60 req/h (without auth), 5000 req/h (with auth)
- EPSS: No documented limit, use conservative default

Based on specification section 4.3.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import ParamSpec, TypeVar

import structlog

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded and queue is full."""

    def __init__(self, service_name: str, wait_time: float):
        self.service_name = service_name
        self.wait_time = wait_time
        super().__init__(f"Rate limit exceeded for {service_name}. Wait {wait_time:.1f}s")


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Tokens are added at a fixed rate up to a maximum capacity.
    Each request consumes one token.
    """

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: datetime = field(init=False)

    def __post_init__(self) -> None:
        """Initialize with full bucket."""
        self.tokens = self.capacity
        self.last_refill = datetime.now(UTC)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.now(UTC)
        elapsed = (now - self.last_refill).total_seconds()
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if insufficient
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self, tokens: float = 1.0) -> float:
        """Calculate wait time until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if tokens available now)
        """
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """Rate limiter for external API calls.

    Implements token bucket algorithm with optional request queuing.

    Usage:
        limiter = RateLimiter("nvd_api", requests_per_second=50/30)

        @limiter
        async def call_nvd():
            ...

        # Or with priority:
        await limiter.acquire(priority=10)  # Higher priority = sooner execution
    """

    def __init__(
        self,
        service_name: str,
        *,
        requests_per_second: float | None = None,
        requests_per_period: int | None = None,
        period_seconds: float = 1.0,
        burst_size: int | None = None,
        max_queue_size: int = 100,
    ):
        """Initialize rate limiter.

        Args:
            service_name: Name for logging
            requests_per_second: Rate as requests/second
            requests_per_period: Alternative: requests per period
            period_seconds: Period duration if using requests_per_period
            burst_size: Maximum burst capacity (defaults to rate)
            max_queue_size: Maximum queued requests before rejection
        """
        self.service_name = service_name
        self.max_queue_size = max_queue_size

        # Calculate rate
        if requests_per_second is not None:
            rate = requests_per_second
        elif requests_per_period is not None:
            rate = requests_per_period / period_seconds
        else:
            rate = 1.0  # Default: 1 request/second

        # Initialize token bucket
        capacity = float(burst_size) if burst_size else max(rate, 1.0)
        self._bucket = TokenBucket(capacity=capacity, refill_rate=rate)

        self._queue: asyncio.PriorityQueue[tuple[int, float, asyncio.Event]] = (
            asyncio.PriorityQueue(maxsize=max_queue_size)
        )
        self._lock = asyncio.Lock()
        self._queue_processor_task: asyncio.Task[None] | None = None

        logger.debug(
            "rate_limiter_initialized",
            service=service_name,
            rate=rate,
            capacity=capacity,
        )

    async def acquire(self, *, priority: int = 0, timeout: float | None = None) -> None:
        """Acquire permission to make a request.

        Args:
            priority: Request priority (lower = higher priority)
            timeout: Maximum wait time in seconds

        Raises:
            RateLimitExceededError: If queue full or timeout exceeded
            asyncio.TimeoutError: If timeout exceeded while waiting
        """
        async with self._lock:
            if self._bucket.consume():
                logger.debug("rate_limit_token_consumed", service=self.service_name)
                return

        # Need to wait - check queue capacity
        if self._queue.qsize() >= self.max_queue_size:
            wait_time = self._bucket.wait_time()
            raise RateLimitExceededError(self.service_name, wait_time)

        # Queue the request
        event = asyncio.Event()
        await self._queue.put((priority, asyncio.get_running_loop().time(), event))

        # Start queue processor if not running
        self._ensure_processor_running()

        # Wait for turn
        if timeout:
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except TimeoutError:
                logger.warning(
                    "rate_limit_timeout",
                    service=self.service_name,
                    queue_size=self._queue.qsize(),
                )
                raise
        else:
            await event.wait()

    def _ensure_processor_running(self) -> None:
        """Ensure queue processor task is running."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self) -> None:
        """Process queued requests as tokens become available."""
        while not self._queue.empty():
            # Wait for token
            wait_time = self._bucket.wait_time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            async with self._lock:
                if self._bucket.consume() and not self._queue.empty():
                    try:
                        _, _, event = self._queue.get_nowait()
                        event.set()
                        logger.debug(
                            "rate_limit_queued_request_released",
                            service=self.service_name,
                            remaining_queue=self._queue.qsize(),
                        )
                    except asyncio.QueueEmpty:
                        break

    def __call__(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        """Decorator to wrap async function with rate limiting.

        Usage:
            @rate_limiter
            async def call_api():
                ...
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            await self.acquire()
            return await func(*args, **kwargs)

        return wrapper

    def get_stats(self) -> dict[str, object]:
        """Get rate limiter statistics."""
        return {
            "service": self.service_name,
            "available_tokens": self._bucket.tokens,
            "capacity": self._bucket.capacity,
            "refill_rate": self._bucket.refill_rate,
            "queue_size": self._queue.qsize(),
            "max_queue_size": self.max_queue_size,
        }


# Pre-configured rate limiters for known APIs
def create_nvd_rate_limiter(
    *,
    has_api_key: bool = False,
    rate_with_key: int = 50,
    rate_without_key: int = 5,
    period_seconds: float = 30.0,
    max_queue_size: int = 100,
) -> RateLimiter:
    """Create rate limiter for NVD API.

    Args:
        has_api_key: True if using NVD API key (higher rate)
        rate_with_key: Requests per period with API key
        rate_without_key: Requests per period without API key
        period_seconds: Rate limit period in seconds
        max_queue_size: Maximum queued requests before rejection

    Returns:
        Configured RateLimiter
    """
    requests = rate_with_key if has_api_key else rate_without_key
    return RateLimiter(
        "nvd_api",
        requests_per_period=requests,
        period_seconds=period_seconds,
        burst_size=requests,
        max_queue_size=max_queue_size,
    )


def create_github_rate_limiter(
    *,
    has_token: bool = False,
    rate_with_token: int = 5000,
    rate_without_token: int = 60,
    period_seconds: float = 3600.0,
    max_queue_size: int = 100,
) -> RateLimiter:
    """Create rate limiter for GitHub API.

    Args:
        has_token: True if using personal access token
        rate_with_token: Requests per period with token
        rate_without_token: Requests per period without token
        period_seconds: Rate limit period in seconds
        max_queue_size: Maximum queued requests before rejection

    Returns:
        Configured RateLimiter
    """
    requests = rate_with_token if has_token else rate_without_token
    return RateLimiter(
        "github_api",
        requests_per_period=requests,
        period_seconds=period_seconds,
        burst_size=min(requests, max_queue_size),
        max_queue_size=max_queue_size,
    )


def create_epss_rate_limiter(
    *,
    rps: float = 10.0,
    burst_size: int = 20,
    max_queue_size: int = 100,
) -> RateLimiter:
    """Create conservative rate limiter for EPSS API.

    Args:
        rps: Requests per second
        burst_size: Maximum burst capacity
        max_queue_size: Maximum queued requests before rejection

    Returns:
        Configured RateLimiter
    """
    return RateLimiter(
        "epss_api",
        requests_per_second=rps,
        burst_size=burst_size,
        max_queue_size=max_queue_size,
    )


__all__ = [
    "RateLimitExceededError",
    "RateLimiter",
    "create_epss_rate_limiter",
    "create_github_rate_limiter",
    "create_nvd_rate_limiter",
]
