"""Unit tests for OrchestratorAgent: route_request flow and fallbacks."""

import pytest

from app.orchestrator.context_manager import ContextManager
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.types import UserRequest
from app.utils.errors import ValidationError


class TestOrchestratorAgentRouteRequest:
    """Tests for route_request: intent -> agent -> response."""

    @pytest.mark.asyncio
    async def test_route_syllabus_returns_syllabus_content(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        req = UserRequest(message="What is the syllabus?", user_id="test-user")
        resp = await orch.route_request(req)
        assert resp.success is True
        assert resp.agent_id == "syllabus"
        assert "Introduction" in resp.content or "CS101" in resp.content

    @pytest.mark.asyncio
    async def test_route_admin_returns_admin_content(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        req = UserRequest(message="What are the deadlines?", user_id="test-user")
        resp = await orch.route_request(req)
        assert resp.success is True
        assert resp.agent_id == "administration"

    @pytest.mark.asyncio
    async def test_route_topic_returns_topic_content(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        req = UserRequest(message="Explain what a variable is", user_id="test-user")
        resp = await orch.route_request(req)
        assert resp.success is True
        assert resp.agent_id == "topic_expert"

    @pytest.mark.asyncio
    async def test_route_unknown_intent_returns_fallback(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        req = UserRequest(message="hello world", user_id="test-user")
        resp = await orch.route_request(req)
        assert resp.success is True
        assert resp.agent_id == "orchestrator"
        assert resp.metadata.get("fallback") is True
        assert "didn't quite understand" in resp.content or "syllabus" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_route_empty_message_raises_validation(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        req = UserRequest(message="   ", user_id="test-user")
        with pytest.raises(ValidationError) as exc_info:
            await orch.route_request(req)
        assert exc_info.value.code == "EMPTY_MESSAGE"

    @pytest.mark.asyncio
    async def test_route_correlation_id_in_metadata(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        req = UserRequest(message="syllabus?", correlation_id="corr-123", user_id="test-user")
        resp = await orch.route_request(req)
        assert resp.metadata.get("correlation_id") == "corr-123"

    @pytest.mark.asyncio
    async def test_all_agents_returns_registered_agents(
        self, agent_registry, memory_store, tracer
    ):
        orch = OrchestratorAgent(
            registry=agent_registry,
            context_store=memory_store,
            tracer=tracer,
        )
        agents = orch.all_agents()
        assert len(agents) >= 3
        ids = {a.agent_id for a in agents}
        assert "syllabus" in ids
        assert "administration" in ids
        assert "topic_expert" in ids
