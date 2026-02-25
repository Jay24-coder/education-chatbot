"""Dependency injection: orchestrator, ContextStore, LLMProvider, config. No direct LLM/DB in routers."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config.settings import settings
from app.orchestrator.context_manager import ContextManager
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.tracing import NoOpTracer
from app.orchestrator.types import Intent
from app.orchestrator.wiring import build_agent_registry
from app.services.context.memory_store import MemoryStore

if TYPE_CHECKING:
    from app.agents.assessment.concept_test_agent import ConceptTestAgent
    from app.agents.assessment.programming_test_agent import ProgrammingTestAgent
    from app.agents.monitoring.performance_monitor_agent import PerformanceMonitorAgent
    from app.agents.specialized.problem_solving_agent import ProblemSolvingAgent
    from app.agents.specialized.visualization_agent import VisualizationAgent
    from app.services.context.store import ContextStore
    from app.services.llm.provider import LLMProvider


@lru_cache(maxsize=1)
def get_context_store() -> "ContextStore":
    """Return the shared ContextStore (in-memory for Phase 1)."""
    return MemoryStore()


@lru_cache(maxsize=1)
def get_llm_provider() -> "LLMProvider | None":
    """Return LLM provider if configured (e.g. API key set), else None."""
    if not getattr(settings, "llm_api_key", None) or not settings.llm_api_key.strip():
        return None
    from app.services.llm.openai_provider import OpenAIProvider
    return OpenAIProvider()


@lru_cache(maxsize=1)
def get_context_manager() -> ContextManager:
    """Return ContextManager wrapping the shared ContextStore."""
    return ContextManager(get_context_store())


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    """Return the shared agent registry (quiz, concept test, performance when context_store is set)."""
    return build_agent_registry(
        llm_provider=get_llm_provider(),
        context_store=get_context_store(),
    )


@lru_cache(maxsize=1)
def get_orchestrator() -> OrchestratorAgent:
    """Return the OrchestratorAgent with registry, store, tracer, and context manager wired."""
    store = get_context_store()
    context_manager = get_context_manager()
    tracer = NoOpTracer()
    registry = get_agent_registry()
    return OrchestratorAgent(
        registry=registry,
        context_store=store,
        tracer=tracer,
        context_manager=context_manager,
    )


def get_quiz_agent():
    """Return QuizAgent from registry for assessment router; None if not registered."""
    return get_agent_registry().get_agent(Intent.QUIZ)


def get_concept_test_agent():
    """Return ConceptTestAgent from registry for assessment router; None if not registered."""
    return get_agent_registry().get_agent(Intent.CONCEPT_TEST)


def get_performance_monitor():
    """Return PerformanceMonitorAgent from registry for assessment router; None if not registered."""
    return get_agent_registry().get_agent(Intent.PERFORMANCE)


def get_programming_test_agent():
    """Return ProgrammingTestAgent from registry for assessment router; None if not registered."""
    return get_agent_registry().get_agent(Intent.PROGRAMMING_TEST)


def get_visualization_agent() -> "VisualizationAgent | None":
    """Return VisualizationAgent from registry for visualization router; None if not registered."""
    return get_agent_registry().get_agent(Intent.VISUALIZATION)


def get_problem_solving_agent() -> "ProblemSolvingAgent | None":
    """Return ProblemSolvingAgent from registry for problem-solving router; None if not registered."""
    return get_agent_registry().get_agent(Intent.PROBLEM_SOLVING)
