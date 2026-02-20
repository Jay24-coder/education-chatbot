"""Dependency injection: orchestrator, ContextStore, LLMProvider, config. No direct LLM/DB in routers."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config.settings import settings
from app.orchestrator.context_manager import ContextManager
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.tracing import NoOpTracer
from app.orchestrator.wiring import build_agent_registry
from app.services.context.memory_store import MemoryStore

if TYPE_CHECKING:
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
def get_orchestrator() -> OrchestratorAgent:
    """Return the OrchestratorAgent with registry, store, tracer, and context manager wired."""
    store = get_context_store()
    context_manager = get_context_manager()
    tracer = NoOpTracer()
    registry = build_agent_registry(llm_provider=get_llm_provider())
    return OrchestratorAgent(
        registry=registry,
        context_store=store,
        tracer=tracer,
        context_manager=context_manager,
    )
