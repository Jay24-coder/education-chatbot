"""Unit tests for orchestrator policies: timeout, retry, circuit breaker."""

import asyncio
import pytest

from app.orchestrator.policies import with_timeout, with_retry
from app.utils.errors import TimeoutError as AppTimeoutError


class TestWithTimeout:
    """Tests for with_timeout(coro, timeout_seconds, ...)."""

    @pytest.mark.asyncio
    async def test_returns_result_when_completes_in_time(self):
        async def fast() -> str:
            return "ok"

        result = await with_timeout(fast(), timeout_seconds=1.0)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_timeout_when_exceeds(self):
        async def slow() -> str:
            await asyncio.sleep(2.0)
            return "ok"

        with pytest.raises(AppTimeoutError) as exc_info:
            await with_timeout(slow(), timeout_seconds=0.05, timeout_message="Too slow")
        assert exc_info.value.code == "TIMEOUT"
        assert "Too slow" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_propagates_other_exceptions(self):
        async def fail() -> str:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await with_timeout(fail(), timeout_seconds=1.0)


class TestWithRetry:
    """Tests for with_retry(fn, ...)."""

    @pytest.mark.asyncio
    async def test_returns_result_on_first_success(self):
        calls = 0

        async def once() -> int:
            nonlocal calls
            calls += 1
            return 42

        result = await with_retry(once, max_retries=2)
        assert result == 42
        assert calls == 1

    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self):
        calls = 0

        async def fail_twice() -> int:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise RuntimeError("temp")
            return 43

        result = await with_retry(
            fail_twice,
            max_retries=3,
            initial_delay=0.01,
            max_delay=0.1,
            jitter=False,
        )
        assert result == 43
        assert calls == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        calls = 0

        async def always_fail() -> int:
            nonlocal calls
            calls += 1
            raise RuntimeError("nope")

        with pytest.raises(RuntimeError, match="nope"):
            await with_retry(
                always_fail,
                max_retries=2,
                initial_delay=0.01,
                max_delay=0.05,
                jitter=False,
            )
        assert calls == 3  # initial + 2 retries
