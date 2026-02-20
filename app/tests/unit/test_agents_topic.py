"""Unit tests for TopicExpertAgent (stub mode, no LLM)."""

import pytest

from app.agents.information.topic_expert_agent import (
    TopicExpertAgent,
    explain_concept_stub,
    get_related_topics_stub,
    assess_difficulty_stub,
    _find_concept_key,
)
from app.orchestrator.types import AgentRequest, Intent


class TestTopicStubHelpers:
    """Tests for stub KB helpers."""

    def test_find_concept_key_variable(self):
        assert _find_concept_key("what is a variable?") == "variable"

    def test_find_concept_key_algorithm(self):
        assert _find_concept_key("explain algorithm") == "algorithm"

    def test_find_concept_key_oop(self):
        assert _find_concept_key("object oriented programming") == "oop"
        assert _find_concept_key("explain oop") == "oop"

    def test_explain_concept_stub_variable(self):
        out = explain_concept_stub("variable")
        assert "variable" in out.lower()
        assert "container" in out.lower() or "value" in out.lower()

    def test_get_related_topics_stub(self):
        out = get_related_topics_stub("variable")
        assert "Related" in out or "related" in out
        assert "data types" in out or "assignment" in out

    def test_assess_difficulty_stub(self):
        out = assess_difficulty_stub("variable")
        assert "difficulty" in out.lower()
        assert "beginner" in out.lower()


class TestTopicExpertAgent:
    """Tests for TopicExpertAgent in stub mode (no LLM)."""

    @pytest.mark.asyncio
    async def test_agent_id_and_capabilities(self, topic_agent: TopicExpertAgent):
        assert topic_agent.agent_id == "topic_expert"
        assert Intent.TOPIC.value in topic_agent.get_capabilities()

    @pytest.mark.asyncio
    async def test_health_check(self, topic_agent: TopicExpertAgent):
        assert topic_agent.health_check() is True

    @pytest.mark.asyncio
    async def test_process_request_explain_concept(self, topic_agent: TopicExpertAgent):
        req = AgentRequest(message="Explain what a variable is", intent=Intent.TOPIC)
        resp = await topic_agent.process_request(req)
        assert resp.agent_id == "topic_expert"
        assert resp.success is True
        assert "variable" in resp.content.lower() or "container" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_process_request_related_topics(self, topic_agent: TopicExpertAgent):
        req = AgentRequest(
            message="What topics are related to variables?",
            intent=Intent.TOPIC,
        )
        resp = await topic_agent.process_request(req)
        assert resp.success is True
        assert "related" in resp.content.lower() or "data types" in resp.content

    @pytest.mark.asyncio
    async def test_process_request_unknown_concept_returns_guidance(
        self, topic_agent: TopicExpertAgent
    ):
        req = AgentRequest(
            message="Explain quantum entanglement",
            intent=Intent.TOPIC,
        )
        resp = await topic_agent.process_request(req)
        assert resp.success is True
        assert "variable" in resp.content.lower() or "function" in resp.content.lower() or "concept" in resp.content.lower()
