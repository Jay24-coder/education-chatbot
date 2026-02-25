"""Wiring: build agent registry with all information agents registered by intent."""

from typing import TYPE_CHECKING

from app.agents.assessment import ConceptTestAgent, ProgrammingTestAgent, QuizAgent
from app.agents.information import AdministrationAgent, SyllabusAgent, TopicExpertAgent
from app.agents.monitoring import PerformanceMonitorAgent
from app.agents.specialized import ProblemSolvingAgent, VisualizationAgent
from app.agents.shared_tools.programming_bank import ProgrammingQuestionBank
from app.agents.shared_tools.question_bank import QuestionBank
from app.agents.shared_tools.code_execution import execute_in_docker
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
    performance / assessment → PerformanceMonitorAgent, quiz → QuizAgent, concept_test → ConceptTestAgent,
    programming_test → ProgrammingTestAgent, visualization → VisualizationAgent,
    problem_solving → ProblemSolvingAgent (programming_test and problem_solving when context_store provided).
    """
    registry = AgentRegistry()
    registry.register(Intent.SYLLABUS, SyllabusAgent())
    registry.register(Intent.ADMIN, AdministrationAgent())
    registry.register(Intent.TOPIC, TopicExpertAgent(llm_provider=llm_provider))
    registry.register(Intent.VISUALIZATION, VisualizationAgent(llm_provider=llm_provider))
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
        registry.register(
            Intent.PROGRAMMING_TEST,
            ProgrammingTestAgent(
                context_store=context_store,
                programming_bank=ProgrammingQuestionBank(),
                performance_monitor=perf,
                executor=execute_in_docker,
            ),
        )
        registry.register(
            Intent.PROBLEM_SOLVING,
            ProblemSolvingAgent(
                context_store=context_store,
                llm_provider=llm_provider,
            ),
        )
    return registry
