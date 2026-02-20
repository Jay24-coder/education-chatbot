"""Outbound call policies: timeouts, retries with jitter, optional circuit breaker."""

import asyncio
import random
import time
from typing import Any, Awaitable, Callable, TypeVar

from app.config.resiliency import resiliency_config
from app.utils.errors import TimeoutError as AppTimeoutError

T = TypeVar("T")


async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    timeout_message: str = "Operation timed out",
) -> T:
    """Run a coroutine with a timeout. Raises app.utils.errors.TimeoutError on timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise AppTimeoutError(timeout_message, code="TIMEOUT")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    max_retries: int | None = None,
    initial_delay: float | None = None,
    max_delay: float | None = None,
    exponential_base: float | None = None,
    jitter: bool | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """
    Run an async callable with retries and exponential backoff (with optional jitter).
    Uses resiliency_config.retries when args are None.
    """
    cfg = resiliency_config.retries
    n = max_retries if max_retries is not None else cfg.max_retries
    delay_init = initial_delay if initial_delay is not None else cfg.initial_delay
    delay_max = max_delay if max_delay is not None else cfg.max_delay
    base = exponential_base if exponential_base is not None else cfg.exponential_base
    use_jitter = jitter if jitter is not None else cfg.jitter

    last_exception: Exception | None = None
    for attempt in range(n + 1):
        try:
            return await fn()
        except retry_on as e:
            last_exception = e
            if attempt == n:
                raise
            delay = min(delay_init * (base**attempt), delay_max)
            if use_jitter:
                delay = delay * (0.5 + random.random())
            await asyncio.sleep(delay)
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("with_retry: unexpected exit")


class CircuitBreaker:
    """Simple in-memory circuit breaker: closed -> open -> half-open -> closed."""

    def __init__(
        self,
        failure_threshold: int | None = None,
        success_threshold: int | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        cfg = resiliency_config.circuit_breaker
        self.failure_threshold = failure_threshold or cfg.failure_threshold
        self.success_threshold = success_threshold or cfg.success_threshold
        self.timeout_seconds = timeout_seconds or cfg.timeout
        self._failures = 0
        self._successes = 0
        self._state: str = "closed"  # closed | open | half_open
        self._open_until: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Execute fn through the circuit breaker; raises if circuit is open."""
        now = time.monotonic()
        async with self._lock:
            if self._state == "open":
                if now < self._open_until:
                    raise AppTimeoutError("Circuit breaker is open", code="CIRCUIT_OPEN")
                self._state = "half_open"
                self._successes = 0
        try:
            result = await fn()
        except Exception:
            async with self._lock:
                self._failures += 1
                if self._state == "half_open" or self._failures >= self.failure_threshold:
                    self._state = "open"
                    self._open_until = time.monotonic() + self.timeout_seconds
                    self._failures = 0
            raise
        async with self._lock:
            self._successes += 1
            if self._state == "half_open" and self._successes >= self.success_threshold:
                self._state = "closed"
                self._failures = 0
            elif self._state == "closed":
                self._failures = 0
        return result
