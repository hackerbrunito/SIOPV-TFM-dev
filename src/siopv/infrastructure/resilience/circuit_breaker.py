"""Circuit Breaker pattern implementation.

Provides fault tolerance for external API calls following the pattern:
- CLOSED: Normal operation, requests flow to the API
- OPEN: After N failures, circuit opens and returns fallback immediately
- HALF-OPEN: After timeout, allows one test request to check recovery

Based on specification section 4.1.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import ParamSpec, TypeVar

import structlog

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and request is rejected."""

    def __init__(self, service_name: str, time_until_retry: timedelta | None = None):
        self.service_name = service_name
        self.time_until_retry = time_until_retry
        msg = f"Circuit breaker open for {service_name}"
        if time_until_retry:
            msg += f" (retry in {time_until_retry.total_seconds():.0f}s)"
        super().__init__(msg)


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Usage:
        breaker = CircuitBreaker("nvd_api", failure_threshold=5, recovery_timeout=60)

        @breaker
        async def call_nvd_api():
            ...

        # Or manually:
        async with breaker:
            result = await call_nvd_api()
    """

    def __init__(
        self,
        service_name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1,
    ):
        """Initialize circuit breaker.

        Args:
            service_name: Name for logging and error messages
            failure_threshold: Consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before half-open state
            half_open_max_calls: Max concurrent calls in half-open state
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition."""
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            return CircuitState.HALF_OPEN
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False
        return datetime.now(UTC) - self._last_failure_time >= self.recovery_timeout

    def _time_until_retry(self) -> timedelta | None:
        """Calculate time remaining until circuit can be tested."""
        if self._last_failure_time is None:
            return None
        elapsed = datetime.now(UTC) - self._last_failure_time
        remaining = self.recovery_timeout - elapsed
        return remaining if remaining.total_seconds() > 0 else None

    async def _record_success(self) -> None:
        """Record successful call, potentially closing circuit."""
        async with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
                logger.info(
                    "circuit_breaker_closed",
                    service=self.service_name,
                    reason="successful_test_call",
                )
            self._state = CircuitState.CLOSED

    async def _record_failure(self, error: Exception) -> None:
        """Record failed call, potentially opening circuit."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(UTC)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_reopened",
                    service=self.service_name,
                    error=str(error),
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    service=self.service_name,
                    failure_count=self._failure_count,
                    error=str(error),
                )

    async def _check_state(self) -> None:
        """Check if request is allowed, raise if circuit open."""
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    self.service_name,
                    time_until_retry=self._time_until_retry(),
                )

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerError(
                        self.service_name,
                        time_until_retry=timedelta(seconds=1),
                    )
                self._half_open_calls += 1
                self._state = CircuitState.HALF_OPEN

    async def __aenter__(self) -> CircuitBreaker:
        """Async context manager entry - check circuit state."""
        await self._check_state()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        """Async context manager exit - record success or failure."""
        if exc_val is None:
            await self._record_success()
        elif not isinstance(exc_val, CircuitBreakerError) and isinstance(exc_val, Exception):
            await self._record_failure(exc_val)
        return False  # Don't suppress exceptions

    def __call__(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        """Decorator to wrap async function with circuit breaker.

        Usage:
            @circuit_breaker
            async def call_api():
                ...
        """

        @wraps(func)
        # ParamSpec wrapper; return always reached via decorated function
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore[return]
            async with self:
                return await func(*args, **kwargs)

        return wrapper

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info("circuit_breaker_reset", service=self.service_name)

    def get_stats(self) -> dict[str, object]:
        """Get circuit breaker statistics."""
        retry_time = self._time_until_retry()
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": self._last_failure_time.isoformat()
            if self._last_failure_time
            else None,
            "time_until_retry": retry_time.total_seconds() if retry_time is not None else None,
        }


__all__ = ["CircuitBreaker", "CircuitBreakerError", "CircuitState"]
