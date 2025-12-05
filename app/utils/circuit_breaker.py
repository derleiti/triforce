"""Circuit breaker pattern implementation with feature flag support.

Enable via environment variable: HTTP_BREAKER=true
"""

import time
import asyncio
import logging
from typing import Callable, Awaitable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold reached, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, failures: int = 5, cooldown: int = 30):
        """Initialize circuit breaker.

        Args:
            failures: Number of consecutive failures before opening circuit
            cooldown: Seconds to wait before attempting to close circuit
        """
        self.failures = failures
        self.cooldown = cooldown
        self._count = 0
        self._opened_at: float | None = None

    def open(self) -> None:
        """Open the circuit breaker."""
        self._opened_at = time.time()
        logger.error(
            "Circuit breaker opened after %d failures (cooldown: %ds)",
            self._count,
            self.cooldown
        )

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if not self._opened_at:
            return False

        elapsed = time.time() - self._opened_at
        if elapsed >= self.cooldown:
            # Transition to half-open state
            logger.info("Circuit breaker entering half-open state")
            self._opened_at = None  # Will test on next request
            return False

        return True

    def record(self, ok: bool) -> None:
        """Record request success/failure.

        Args:
            ok: True if request succeeded, False if failed
        """
        if ok:
            self._count = 0
            if self._opened_at:
                logger.info("Circuit breaker closed after successful request")
                self._opened_at = None
        else:
            self._count += 1
            if self._count >= self.failures and not self._opened_at:
                self.open()


async def with_breaker(
    breaker: CircuitBreaker,
    coro: Callable[..., Awaitable[T]],
    *args: Any,
    **kwargs: Any
) -> T:
    """Execute coroutine with circuit breaker protection.

    Args:
        breaker: CircuitBreaker instance
        coro: Async function to execute
        *args: Positional arguments for coro
        **kwargs: Keyword arguments for coro

    Returns:
        Result from coro

    Raises:
        RuntimeError: If circuit is open
        Exception: Any exception from coro
    """
    if breaker.is_open():
        raise RuntimeError("circuit_open")

    try:
        result = await coro(*args, **kwargs)
        breaker.record(True)
        return result
    except Exception:
        breaker.record(False)
        raise
