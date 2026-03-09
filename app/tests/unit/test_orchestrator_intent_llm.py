import pytest

from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.types import UserRequest


class _FakeLLM:
    def __init__(self, reply: str | Exception):
        self._reply = reply

    async def complete(self, prompt: str, *, model=None, temperature=0.0, timeout_seconds=None) -> str:
        if isinstance(self._reply, Exception):
            raise self._reply
        return str(self._reply)


@pytest.mark.asyncio
async def test_llm_first_routes_by_llm_intent_even_if_message_unknown_to_keywords(
    agent_registry, memory_store, tracer
):
    orch = OrchestratorAgent(
        registry=agent_registry,
        context_store=memory_store,
        tracer=tracer,
        llm_provider=_FakeLLM("syllabus"),
        intent_detection_mode="llm_first",
        intent_model_id="test-model",
        intent_llm_timeout_seconds=1.0,
    )
    req = UserRequest(message="blorp blarp", user_id="test-user")
    resp = await orch.route_request(req)
    assert resp.success is True
    assert resp.agent_id == "syllabus"
    assert resp.metadata.get("fallback") is not True


@pytest.mark.asyncio
async def test_llm_first_falls_back_to_keyword_when_llm_returns_unknown(
    agent_registry, memory_store, tracer
):
    orch = OrchestratorAgent(
        registry=agent_registry,
        context_store=memory_store,
        tracer=tracer,
        llm_provider=_FakeLLM("unknown"),
        intent_detection_mode="llm_first",
        intent_model_id="test-model",
        intent_llm_timeout_seconds=1.0,
    )
    req = UserRequest(message="Explain what a variable is", user_id="test-user")
    resp = await orch.route_request(req)
    assert resp.success is True
    assert resp.agent_id == "topic_expert"


@pytest.mark.asyncio
async def test_llm_first_falls_back_to_keyword_when_llm_returns_malformed_output(
    agent_registry, memory_store, tracer
):
    orch = OrchestratorAgent(
        registry=agent_registry,
        context_store=memory_store,
        tracer=tracer,
        llm_provider=_FakeLLM("syllabus please"),
        intent_detection_mode="llm_first",
        intent_model_id="test-model",
        intent_llm_timeout_seconds=1.0,
    )
    req = UserRequest(message="Explain recursion", user_id="test-user")
    resp = await orch.route_request(req)
    assert resp.success is True
    assert resp.agent_id == "topic_expert"


@pytest.mark.asyncio
async def test_llm_first_falls_back_to_keyword_when_llm_raises(
    agent_registry, memory_store, tracer
):
    orch = OrchestratorAgent(
        registry=agent_registry,
        context_store=memory_store,
        tracer=tracer,
        llm_provider=_FakeLLM(RuntimeError("boom")),
        intent_detection_mode="llm_first",
        intent_model_id="test-model",
        intent_llm_timeout_seconds=1.0,
    )
    req = UserRequest(message="What is the syllabus?", user_id="test-user")
    resp = await orch.route_request(req)
    assert resp.success is True
    assert resp.agent_id == "syllabus"

