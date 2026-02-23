"""Wiring: build agent registry with all information agents registered by intent."""

from typing import TYPE_CHECKING

from app.agents.assessment import ConceptTestAgent, QuizAgent
from app.agents.information import AdministrationAgent, SyllabusAgent, TopicExpertAgent
from app.agents.monitoring import PerformanceMonitorAgent
from app.agents.shared_tools.question_bank import QuestionBank
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.types import Intent

if TYPE_CHECKING:
    from app.services.context.store import ContextStore
    from app.services.llm.provider import LLMProvider


def build_agent_registry(
    llm_provider: "LLMProvider | None" = None,
    context_store: "ContextStore | None" = None,
) -> AgentRegistry:
    """
    Create and populate the agent registry.
    Intents: syllabus → SyllabusAgent, admin → AdministrationAgent, topic → TopicExpertAgent,
    performance / assessment → PerformanceMonitorAgent, quiz → QuizAgent, concept_test → ConceptTestAgent
    (when context_store provided).
    """
    registry = AgentRegistry()
    registry.register(Intent.SYLLABUS, SyllabusAgent())
    registry.register(Intent.ADMIN, AdministrationAgent())
    registry.register(Intent.TOPIC, TopicExpertAgent(llm_provider=llm_provider))
    if context_store is not None:
        perf = PerformanceMonitorAgent(context_store)
        registry.register_capabilities(perf)
        registry.register(
            Intent.QUIZ,
            QuizAgent(
                context_store=context_store,
                question_bank=QuestionBank(),
                performance_monitor=perf,
            ),
        )
        registry.register(
            Intent.CONCEPT_TEST,
            ConceptTestAgent(
                context_store=context_store,
                llm_provider=llm_provider,
                performance_monitor=perf,
            ),
        )
    return registry
