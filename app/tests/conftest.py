"""Pytest configuration and shared fixtures for app tests."""

import pytest

from app.agents.information import AdministrationAgent, SyllabusAgent, TopicExpertAgent
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.tracing import NoOpTracer
from app.orchestrator.types import Intent
from app.orchestrator.wiring import build_agent_registry
from app.services.context.memory_store import MemoryStore


@pytest.fixture
def memory_store() -> MemoryStore:
    """Fresh in-memory context store per test."""
    return MemoryStore()


@pytest.fixture
def agent_registry() -> AgentRegistry:
    """Registry with Syllabus, Administration, Topic agents (no LLM)."""
    return build_agent_registry(llm_provider=None)


@pytest.fixture
def syllabus_agent() -> SyllabusAgent:
    return SyllabusAgent()


@pytest.fixture
def administration_agent() -> AdministrationAgent:
    return AdministrationAgent()


@pytest.fixture
def topic_agent() -> TopicExpertAgent:
    return TopicExpertAgent(llm_provider=None)


@pytest.fixture
def tracer():
    return NoOpTracer()
