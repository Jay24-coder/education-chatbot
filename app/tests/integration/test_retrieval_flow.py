"""Integration tests: retrieval flow — request -> intent -> agent -> response content."""

import pytest

from app.orchestrator.orchestrator_agent import classify_intent
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.routing import select_agent
from app.orchestrator.types import AgentRequest, Intent, UserRequest
from app.orchestrator.wiring import build_agent_registry


class TestRetrievalFlow:
    """End-to-end flow: classify -> select agent -> process -> content."""

    @pytest.mark.asyncio
    async def test_syllabus_flow_returns_curriculum_content(self, agent_registry: AgentRegistry):
        message = "What topics are covered in the course?"
        intent = classify_intent(message)
        assert intent == Intent.SYLLABUS
        agent = select_agent(agent_registry, intent)
        assert agent is not None
        req = AgentRequest(message=message, intent=intent)
        resp = await agent.process_request(req)
        assert resp.agent_id == "syllabus"
        assert "topics" in resp.content.lower() or "Variables" in resp.content or "outline" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_admin_flow_returns_policy_or_deadline(self, agent_registry: AgentRegistry):
        message = "What is the late submission policy?"
        intent = classify_intent(message)
        assert intent == Intent.ADMIN
        agent = select_agent(agent_registry, intent)
        assert agent is not None
        req = AgentRequest(message=message, intent=intent)
        resp = await agent.process_request(req)
        assert resp.agent_id == "administration"
        assert "Late" in resp.content or "10%" in resp.content or "policy" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_topic_flow_returns_concept_explanation(self, agent_registry: AgentRegistry):
        message = "Explain the concept of a function"
        intent = classify_intent(message)
        assert intent == Intent.TOPIC
        agent = select_agent(agent_registry, intent)
        assert agent is not None
        req = AgentRequest(message=message, intent=intent)
        resp = await agent.process_request(req)
        assert resp.agent_id == "topic_expert"
        assert "function" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_unknown_flow_no_agent_fallback_handled_by_orchestrator(self):
        from app.orchestrator.orchestrator_agent import OrchestratorAgent
        from app.orchestrator.tracing import NoOpTracer
        from app.services.context.memory_store import MemoryStore

        registry = build_agent_registry(llm_provider=None)
        store = MemoryStore()
        orch = OrchestratorAgent(
            registry=registry,
            context_store=store,
            tracer=NoOpTracer(),
        )
        req = UserRequest(message="random gibberish xyz")
        intent = classify_intent(req.message)
        assert intent == Intent.UNKNOWN
        resp = await orch.route_request(req)
        assert resp.agent_id == "orchestrator"
        assert resp.metadata.get("fallback") is True
