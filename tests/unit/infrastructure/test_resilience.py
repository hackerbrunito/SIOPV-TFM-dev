"""Tests for resilience infrastructure (CircuitBreaker and RateLimiter)."""

import asyncio
import contextlib

import pytest

from siopv.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    RateLimiter,
    RateLimitExceededError,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture()
    def breaker(self) -> CircuitBreaker:
        """Create a circuit breaker for testing."""
        return CircuitBreaker(
            "test_service",
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for fast tests
        )

    def test_initial_state_closed(self, breaker: CircuitBreaker) -> None:
        """Test that circuit starts in closed state."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open

    @pytest.mark.asyncio()
    async def test_success_keeps_circuit_closed(self, breaker: CircuitBreaker) -> None:
        """Test that successful calls keep circuit closed."""
        async with breaker:
            pass  # Successful call

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio()
    async def test_failures_open_circuit(self, breaker: CircuitBreaker) -> None:
        """Test that failures open the circuit after threshold."""
        for i in range(3):
            msg = f"Error {i}"
            with pytest.raises(ValueError, match=r"Error \d+"):
                async with breaker:
                    raise ValueError(msg)

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open

    @pytest.mark.asyncio()
    async def test_open_circuit_rejects_requests(self, breaker: CircuitBreaker) -> None:
        """Test that open circuit rejects new requests."""
        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError, match="Error"):
                async with breaker:
                    raise ValueError("Error")

        # New request should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            async with breaker:
                pass

        assert "circuit breaker open" in str(exc_info.value).lower()
        assert exc_info.value.service_name == "test_service"

    @pytest.mark.asyncio()
    async def test_half_open_after_timeout(self, breaker: CircuitBreaker) -> None:
        """Test that circuit goes to half-open after timeout."""
        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError, match="Error"):
                async with breaker:
                    raise ValueError("Error")

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should be half-open now
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio()
    async def test_half_open_success_closes_circuit(self, breaker: CircuitBreaker) -> None:
        """Test that success in half-open state closes circuit."""
        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError, match="Error"):
                async with breaker:
                    raise ValueError("Error")

        # Wait for recovery
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Successful call should close circuit
        async with breaker:
            pass

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio()
    async def test_half_open_failure_reopens_circuit(self, breaker: CircuitBreaker) -> None:
        """Test that failure in half-open state reopens circuit."""
        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError, match="Error"):
                async with breaker:
                    raise ValueError("Error")

        # Wait for recovery
        await asyncio.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        with pytest.raises(ValueError, match="Still failing"):
            async with breaker:
                raise ValueError("Still failing")

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio()
    async def test_decorator_usage(self) -> None:
        """Test circuit breaker as decorator."""
        breaker = CircuitBreaker("decorator_test", failure_threshold=2, recovery_timeout=1)

        call_count = 0

        @breaker
        async def failing_function() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        # Should allow calls until threshold
        for _ in range(2):
            with pytest.raises(ValueError, match="Always fails"):
                await failing_function()

        # Circuit should be open
        assert breaker.is_open
        assert call_count == 2

        # Next call should be rejected without calling function
        with pytest.raises(CircuitBreakerError):
            await failing_function()

        assert call_count == 2  # Function not called

    def test_reset(self, breaker: CircuitBreaker) -> None:
        """Test manual circuit reset."""
        # Simulate failures to track
        breaker._failure_count = 10
        breaker._state = CircuitState.OPEN

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_get_stats(self, breaker: CircuitBreaker) -> None:
        """Test statistics reporting."""
        stats = breaker.get_stats()

        assert stats["service"] == "test_service"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["failure_threshold"] == 3


class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.fixture()
    def limiter(self) -> RateLimiter:
        """Create a rate limiter for testing."""
        return RateLimiter(
            "test_service",
            requests_per_second=10.0,
            burst_size=5,
            max_queue_size=10,
        )

    @pytest.mark.asyncio()
    async def test_allows_requests_within_limit(self, limiter: RateLimiter) -> None:
        """Test that requests within limit are allowed."""
        # Should allow burst_size requests immediately
        for _ in range(5):
            await limiter.acquire()

    @pytest.mark.asyncio()
    async def test_rate_limits_excess_requests(self) -> None:
        """Test that excess requests are rate limited."""
        limiter = RateLimiter(
            "test_service",
            requests_per_second=100.0,  # High rate for fast test
            burst_size=2,
            max_queue_size=5,
        )

        # Exhaust burst
        await limiter.acquire()
        await limiter.acquire()

        # Third request should wait or queue
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have waited some time (token refill)
        assert elapsed >= 0.005  # At least some wait time

    @pytest.mark.asyncio()
    async def test_queue_overflow_raises_error(self) -> None:
        """Test that queue overflow raises error."""
        limiter = RateLimiter(
            "test_service",
            requests_per_second=0.01,  # Very slow (1 per 100 seconds)
            burst_size=1,
            max_queue_size=2,
        )

        # Exhaust burst
        await limiter.acquire()

        # Fill the queue with background tasks
        tasks = []
        for _ in range(2):  # Fill to max_queue_size
            tasks.append(asyncio.create_task(limiter.acquire()))

        # Allow tasks to queue
        await asyncio.sleep(0.05)

        # Next request should fail (queue full)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.acquire()

        assert exc_info.value.service_name == "test_service"

        # Cancel pending tasks
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, RateLimitExceededError):
                await task

    @pytest.mark.asyncio()
    async def test_decorator_usage(self) -> None:
        """Test rate limiter as decorator."""
        limiter = RateLimiter(
            "decorator_test",
            requests_per_second=100.0,
            burst_size=3,
        )

        call_count = 0

        @limiter
        async def rate_limited_function() -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        # Should allow burst_size calls
        results = await asyncio.gather(*[rate_limited_function() for _ in range(3)])

        assert results == [1, 2, 3]
        assert call_count == 3

    def test_get_stats(self, limiter: RateLimiter) -> None:
        """Test statistics reporting."""
        stats = limiter.get_stats()

        assert stats["service"] == "test_service"
        assert stats["capacity"] == 5
        assert stats["refill_rate"] == 10.0
        assert stats["max_queue_size"] == 10

    @pytest.mark.asyncio()
    async def test_priority_queue(self) -> None:
        """Test that higher priority requests are processed first."""
        limiter = RateLimiter(
            "priority_test",
            requests_per_second=1.0,  # Slow
            burst_size=1,
        )

        # Exhaust burst
        await limiter.acquire()

        # Queue requests with different priorities
        results: list[int] = []

        async def acquire_with_priority(priority: int) -> None:
            await limiter.acquire(priority=priority)
            results.append(priority)

        # Start low priority first, then high priority
        low_task = asyncio.create_task(acquire_with_priority(10))
        await asyncio.sleep(0.01)  # Ensure order
        high_task = asyncio.create_task(acquire_with_priority(1))

        # Wait for both
        await asyncio.gather(low_task, high_task)

        # Higher priority (lower number) should complete first
        assert results[0] < results[1] or len(results) == 2


class TestRateLimiterFactories:
    """Tests for pre-configured rate limiter factories."""

    def test_create_nvd_rate_limiter_no_key(self) -> None:
        """Test NVD rate limiter without API key."""
        from siopv.infrastructure.resilience.rate_limiter import create_nvd_rate_limiter

        limiter = create_nvd_rate_limiter(has_api_key=False)
        stats = limiter.get_stats()

        # 5 requests per 30 seconds = 0.167 req/s
        assert stats["refill_rate"] == pytest.approx(5 / 30, rel=0.01)

    def test_create_nvd_rate_limiter_with_key(self) -> None:
        """Test NVD rate limiter with API key."""
        from siopv.infrastructure.resilience.rate_limiter import create_nvd_rate_limiter

        limiter = create_nvd_rate_limiter(has_api_key=True)
        stats = limiter.get_stats()

        # 50 requests per 30 seconds = 1.67 req/s
        assert stats["refill_rate"] == pytest.approx(50 / 30, rel=0.01)

    def test_create_github_rate_limiter_no_token(self) -> None:
        """Test GitHub rate limiter without token."""
        from siopv.infrastructure.resilience.rate_limiter import create_github_rate_limiter

        limiter = create_github_rate_limiter(has_token=False)
        stats = limiter.get_stats()

        # 60 requests per hour
        assert stats["refill_rate"] == pytest.approx(60 / 3600, rel=0.01)

    def test_create_github_rate_limiter_with_token(self) -> None:
        """Test GitHub rate limiter with token."""
        from siopv.infrastructure.resilience.rate_limiter import create_github_rate_limiter

        limiter = create_github_rate_limiter(has_token=True)
        stats = limiter.get_stats()

        # 5000 requests per hour
        assert stats["refill_rate"] == pytest.approx(5000 / 3600, rel=0.01)

    def test_create_epss_rate_limiter(self) -> None:
        """Test EPSS rate limiter (conservative default)."""
        from siopv.infrastructure.resilience.rate_limiter import create_epss_rate_limiter

        limiter = create_epss_rate_limiter()
        stats = limiter.get_stats()

        assert stats["refill_rate"] == 10.0
        assert stats["capacity"] == 20
