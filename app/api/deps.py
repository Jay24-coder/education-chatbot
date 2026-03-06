"""Dependency injection: orchestrator, ContextStore, LLMProvider, config. No direct LLM/DB in routers."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config.settings import settings
from app.db.pool import get_engine
from app.db.repositories.conversations import ConversationsRepository
from app.db.repositories.jobs import JobsRepository
from app.orchestrator.context_manager import ContextManager
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.tracing import NoOpTracer
from app.orchestrator.types import Intent
from app.orchestrator.wiring import build_agent_registry
from app.services.context.memory_store import MemoryStore
from app.services.context.postgres_store import PostgresContextStore

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
    """Return the shared ContextStore.

    When settings.context_store_mode == "persistent", use PostgresContextStore;
    otherwise fall back to in-memory MemoryStore (default behavior).
    """
    mode = (getattr(settings, "context_store_mode", "memory") or "memory").lower()
    if mode != "persistent":
        return MemoryStore()

    engine = get_engine()
    conversations_repo = ConversationsRepository(engine)
    jobs_repo = JobsRepository(engine)
    return PostgresContextStore(
        conversations_repo=conversations_repo,
        jobs_repo=jobs_repo,
    )


@lru_cache(maxsize=1)
def get_llm_provider() -> "LLMProvider | None":
    """Return LLM provider if configured (e.g. API key set), else None."""
    provider = (getattr(settings, "llm_provider", None) or "openai").strip().lower()

    if provider in {"openai"}:
        if not settings.llm_api_key.strip():
            return None
        from app.services.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()

    if provider in {"google", "gemini"}:
        api_key = (settings.google_api_key or settings.llm_api_key).strip()
        if not api_key:
            return None
        from app.services.llm.google_provider import GoogleProvider

        return GoogleProvider(api_key=api_key)

    # Unknown provider: keep app running without LLM configured.
    return None


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
