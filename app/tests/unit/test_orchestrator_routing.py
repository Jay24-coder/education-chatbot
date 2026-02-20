"""Unit tests for orchestrator routing: select_agent by intent."""

import pytest

from app.orchestrator.registry import AgentRegistry
from app.orchestrator.routing import select_agent
from app.orchestrator.types import Intent


class TestSelectAgent:
    """Tests for select_agent(registry, intent)."""

    def test_select_agent_syllabus_returns_syllabus_agent(self, agent_registry: AgentRegistry):
        agent = select_agent(agent_registry, Intent.SYLLABUS)
        assert agent is not None
        assert agent.agent_id == "syllabus"

    def test_select_agent_admin_returns_administration_agent(
        self, agent_registry: AgentRegistry
    ):
        agent = select_agent(agent_registry, Intent.ADMIN)
        assert agent is not None
        assert agent.agent_id == "administration"

    def test_select_agent_topic_returns_topic_expert_agent(self, agent_registry: AgentRegistry):
        agent = select_agent(agent_registry, Intent.TOPIC)
        assert agent is not None
        assert agent.agent_id == "topic_expert"

    def test_select_agent_unknown_returns_none(self, agent_registry: AgentRegistry):
        agent = select_agent(agent_registry, Intent.UNKNOWN)
        assert agent is None

    def test_select_agent_empty_registry_returns_none(self):
        empty_registry = AgentRegistry()
        assert select_agent(empty_registry, Intent.SYLLABUS) is None
        assert select_agent(empty_registry, Intent.UNKNOWN) is None
