"""Integration tests: context persistence across chat turns (session + history)."""

import pytest

from app.orchestrator.context_manager import ContextManager
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.types import UserRequest
from app.services.context.memory_store import MemoryStore


class TestContextPersistence:
    """Conversation context persists across turns via ContextManager + MemoryStore."""

    @pytest.mark.asyncio
    async def test_persist_turn_after_syllabus_then_history_has_messages(self):
        store = MemoryStore()
        cm = ContextManager(store)
        from app.orchestrator.wiring import build_agent_registry
        from app.orchestrator.tracing import NoOpTracer

        registry = build_agent_registry(llm_provider=None)
        orch = OrchestratorAgent(
            registry=registry,
            context_store=store,
            tracer=NoOpTracer(),
            context_manager=cm,
        )
        session_id = "persist-session-1"

        req1 = UserRequest(message="What is the syllabus?", session_id=session_id, user_id="test-user")
        resp1 = await orch.route_request(req1)
        assert resp1.success is True

        history = store.get_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user" and "syllabus" in history[0]["content"].lower()
        assert history[1]["role"] == "assistant"

        req2 = UserRequest(message="What are the prerequisites?", session_id=session_id, user_id="test-user")
        resp2 = await orch.route_request(req2)
        assert resp2.success is True

        history2 = store.get_history(session_id)
        assert len(history2) == 4
        assert history2[2]["role"] == "user" and "prerequisite" in history2[2]["content"].lower()

    @pytest.mark.asyncio
    async def test_session_context_available_to_agent_request(self):
        store = MemoryStore()
        store.set("s1", "preference", "brief")
        cm = ContextManager(store)
        from app.orchestrator.wiring import build_agent_registry
        from app.orchestrator.tracing import NoOpTracer

        registry = build_agent_registry(llm_provider=None)
        orch = OrchestratorAgent(
            registry=registry,
            context_store=store,
            tracer=NoOpTracer(),
            context_manager=cm,
        )
        req = UserRequest(message="syllabus?", session_id="s1", user_id="test-user")
        resp = await orch.route_request(req)
        assert resp.success is True
        context = store.get("s1")
        assert context.get("preference") == "brief"
