"""Orchestrator agent: request classification, routing, delegation, and response aggregation."""

import re
from typing import Any, TYPE_CHECKING

from app.observability.logging import get_logger
from app.orchestrator.policies import with_timeout
from app.orchestrator.routing import select_agent
from app.orchestrator.types import AgentRequest, AgentResponse, Intent, UserRequest
from app.utils.errors import OrchestratorError, ValidationError

if TYPE_CHECKING:
    from app.agents.base.base_agent import BaseAgent
    from app.orchestrator.context_manager import ContextManager
    from app.orchestrator.registry import AgentRegistry
    from app.orchestrator.tracing import Tracer
    from app.services.context.store import ContextStore

logger = get_logger(__name__)

# Max user message length to avoid abuse and oversized payloads
MAX_MESSAGE_LENGTH = 32_768

# Default fallback when intent is unknown or no agent is registered
DEFAULT_FALLBACK_MESSAGE = (
    "I didn't quite understand that. You can ask about the syllabus, "
    "administration (policies, deadlines), or specific course topics."
)

# Keyword rules for rule-based intent classification (order can matter for overlap)
_INTENT_KEYWORDS: list[tuple[Intent, list[str]]] = [
    (Intent.SYLLABUS, ["syllabus", "curriculum", "course outline", "prerequisites", "topics covered", "topics are covered", "covered in the course", "course info"]),
    (Intent.ADMIN, ["deadline", "policy", "administration", "procedure", "submit", "assignment due", "grades", "attendance"]),
    (Intent.TOPIC, ["explain", "concept", "topic", "what is", "how does", "definition", "example", "related to"]),
    (Intent.PERFORMANCE, ["progress", "my progress", "show my progress", "performance", "how am i doing", "my scores", "assessment results"]),
    (Intent.QUIZ, ["quiz", "start a quiz", "take a quiz", "give me a quiz", "quiz on", "start quiz"]),
    (Intent.CONCEPT_TEST, ["concept test", "test my understanding", "concept test on", "start concept test"]),
    (
        Intent.PROGRAMMING_TEST,
        [
            "programming test",
            "coding test",
            "coding challenge",
            "code challenge",
            "programming challenge",
            "code exercise",
            "test my coding",
        ],
    ),
    (Intent.VISUALIZATION, ["draw", "visualize", "diagram", "graph of", "plot"]),
    (
        Intent.PROBLEM_SOLVING,
        [
            "problem solving",
            "help me solve",
            "solve this problem",
            "work through this",
            "step by step solution",
            "walk me through",
            "guide me through solving",
        ],
    ),
]


def _normalize(text: str) -> str:
    """Normalize message for classification: lowercase, collapse whitespace."""
    return " ".join(re.split(r"\s+", text.strip().lower()))


def classify_intent(message: str) -> Intent:
    """
    Map user message to intent (syllabus / admin / topic / unknown).

    Uses simple keyword matching. Can be extended to use LLMProvider for
    ambiguous or long messages.
    """
    normalized = _normalize(message)
    if not normalized:
        return Intent.UNKNOWN
    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw in normalized for kw in keywords):
            return intent
    return Intent.UNKNOWN


def validate_and_sanitize_request(request: UserRequest) -> UserRequest:
    """
    Validate and sanitize user request. Raises ValidationError if invalid.
    Returns a sanitized copy (stripped message, length capped).
    """
    msg = (request.message or "").strip()
    if not msg:
        raise ValidationError("Message cannot be empty", code="EMPTY_MESSAGE")
    if len(msg) > MAX_MESSAGE_LENGTH:
        raise ValidationError(
            f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH} characters",
            code="MESSAGE_TOO_LONG",
        )
    return request.model_copy(update={"message": msg})


def _fallback_response(
    correlation_id: str | None,
    fallback_message: str = DEFAULT_FALLBACK_MESSAGE,
) -> AgentResponse:
    """Build a single fallback AgentResponse for unknown intent or missing agent."""
    return AgentResponse(
        content=fallback_message,
        agent_id="orchestrator",
        success=True,
        metadata={"correlation_id": correlation_id, "fallback": True},
        error_message=None,
    )


def _aggregate_responses(responses: list[AgentResponse]) -> AgentResponse:
    """
    Aggregate multiple agent responses into one. For Phase 1 only single-agent
    responses are used; this stub returns the first response or a fallback.
    """
    if not responses:
        return _fallback_response(None)
    if len(responses) == 1:
        return responses[0]
    # Multi-agent path: concatenate content; first agent wins metadata for now
    first = responses[0]
    content = "\n\n".join(r.content for r in responses)
    return first.model_copy(
        update={
            "content": content,
            "metadata": {**first.metadata, "aggregated_count": len(responses)},
        }
    )


class OrchestratorAgent:
    """
    Routes user requests to the correct agent: classify intent, select agent,
    delegate, and return a single AgentResponse. Uses registry, ContextStore,
    Tracer, and policies (timeout/retry).
    """

    def __init__(
        self,
        registry: "AgentRegistry",
        context_store: "ContextStore",
        tracer: "Tracer",
        *,
        context_manager: "ContextManager | None" = None,
        agent_timeout_seconds: float = 30.0,
        fallback_message: str = DEFAULT_FALLBACK_MESSAGE,
    ) -> None:
        self._registry = registry
        self._context_store = context_store
        self._tracer = tracer
        self._context_manager = context_manager
        self._agent_timeout_seconds = agent_timeout_seconds
        self._fallback_message = fallback_message

    def all_agents(self) -> list["BaseAgent"]:
        """Return all registered agents (e.g. for health checks)."""
        return self._registry.all_agents()

    async def route_request(self, request: UserRequest) -> AgentResponse:
        """
        Classify intent, select agent, delegate, and return a single response.
        Correlation ID is set on tracer and included in logs/metadata.
        """
        request = validate_and_sanitize_request(request)
        correlation_id = request.correlation_id
        if correlation_id:
            self._tracer.set_correlation_id(correlation_id)

        logger.info(
            "orchestrator_route_start",
            correlation_id=correlation_id,
            session_id=request.session_id,
            message_length=len(request.message),
        )
        span = self._tracer.start_span("orchestrator.route", correlation_id=correlation_id)
        try:
            span.set_attribute("message_length", len(request.message))
            intent = classify_intent(request.message)
            span.set_attribute("intent", intent.value)

            agent: "BaseAgent | None" = select_agent(self._registry, intent)
            if agent is None or intent == Intent.UNKNOWN:
                span.set_attribute("fallback", True)
                logger.info(
                    "orchestrator_fallback",
                    correlation_id=correlation_id,
                    intent=intent.value,
                    reason="no_agent" if agent is None else "unknown_intent",
                )
                fallback = _aggregate_responses([
                    _fallback_response(correlation_id, self._fallback_message),
                ])
                if self._context_manager and request.session_id:
                    self._context_manager.persist_turn(
                        request.session_id, request.message, fallback.content
                    )
                return fallback

            session_id = request.session_id or ""
            context: dict[str, Any] = {}
            if session_id:
                context = self._context_store.get(session_id)

            agent_request = AgentRequest(
                message=request.message,
                session_id=request.session_id,
                correlation_id=correlation_id,
                intent=intent,
                context=context,
            )

            async def _call_agent() -> AgentResponse:
                return await agent.process_request(agent_request)

            response = await with_timeout(
                _call_agent(),
                timeout_seconds=self._agent_timeout_seconds,
                timeout_message="Agent processing timed out",
            )
            span.set_attribute("agent_id", response.agent_id)
            logger.info(
                "orchestrator_route_done",
                correlation_id=correlation_id,
                intent=intent.value,
                agent_id=response.agent_id,
            )
            result = _aggregate_responses([response])
            if self._context_manager and session_id:
                self._context_manager.persist_turn(
                    session_id, request.message, result.content
                )
            return result
        except ValidationError:
            raise
        except OrchestratorError:
            raise
        except Exception as e:
            span.set_attribute("error", str(e))
            raise OrchestratorError(
                f"Orchestrator failed: {e!s}",
                code="ORCHESTRATOR_ERROR",
            ) from e
        finally:
            span.end()
