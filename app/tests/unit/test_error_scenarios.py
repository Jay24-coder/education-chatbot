"""Unit tests for error scenarios and fallbacks: unknown intent, timeouts, invalid input."""

import asyncio
import pytest

from app.orchestrator.orchestrator_agent import (
    OrchestratorAgent,
    classify_intent,
    validate_and_sanitize_request,
)
from app.orchestrator.types import Intent, UserRequest
from app.orchestrator.wiring import build_agent_registry
from app.orchestrator.tracing import NoOpTracer
from app.services.context.memory_store import MemoryStore
from app.utils.errors import ValidationError, TimeoutError as AppTimeoutError
from app.orchestrator.policies import with_timeout


class TestUnknownIntentFallback:
    """Unknown intent returns fallback message, not 500."""

    @pytest.mark.asyncio
    async def test_unknown_intent_classified(self):
        assert classify_intent("hello") == Intent.UNKNOWN
        assert classify_intent("xyz random") == Intent.UNKNOWN

    @pytest.mark.asyncio
    async def test_route_unknown_returns_success_with_fallback_message(self):
        registry = build_agent_registry(llm_provider=None)
        store = MemoryStore()
        orch = OrchestratorAgent(
            registry=registry,
            context_store=store,
            tracer=NoOpTracer(),
        )
        resp = await orch.route_request(UserRequest(message="hello world", user_id="test-user"))
        assert resp.success is True
        assert resp.agent_id == "orchestrator"
        assert resp.metadata.get("fallback") is True
        assert len(resp.content) > 0


class TestInvalidInput:
    """Invalid input raises ValidationError or returns 422 from API."""

    def test_empty_message_raises_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_and_sanitize_request(UserRequest(message="   ", user_id="test-user"))
        assert exc_info.value.code == "EMPTY_MESSAGE"

    def test_message_too_long_raises_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_and_sanitize_request(UserRequest(message="x" * 33_000, user_id="test-user"))
        assert exc_info.value.code == "MESSAGE_TOO_LONG"


class TestTimeoutFallback:
    """Timeout on agent call raises TimeoutError (orchestrator can catch and fallback)."""

    @pytest.mark.asyncio
    async def test_with_timeout_raises_on_slow_work(self):
        async def slow() -> str:
            await asyncio.sleep(10.0)
            return "done"

        with pytest.raises(AppTimeoutError) as exc_info:
            await with_timeout(slow(), timeout_seconds=0.02, timeout_message="Agent timed out")
        assert exc_info.value.code == "TIMEOUT"
