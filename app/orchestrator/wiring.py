"""Wiring: build agent registry with all information agents registered by intent."""

from typing import TYPE_CHECKING

from app.agents.information import AdministrationAgent, SyllabusAgent, TopicExpertAgent
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.types import Intent

if TYPE_CHECKING:
    from app.services.llm.provider import LLMProvider


def build_agent_registry(llm_provider: "LLMProvider | None" = None) -> AgentRegistry:
    """
    Create and populate the agent registry with Syllabus, Administration, and Topic Expert agents.
    Intents are mapped: syllabus → SyllabusAgent, admin → AdministrationAgent, topic → TopicExpertAgent.
    TopicExpertAgent uses LLM when provided; otherwise uses in-memory stub KB.
    """
    registry = AgentRegistry()
    registry.register(Intent.SYLLABUS, SyllabusAgent())
    registry.register(Intent.ADMIN, AdministrationAgent())
    registry.register(Intent.TOPIC, TopicExpertAgent(llm_provider=llm_provider))
    return registry
