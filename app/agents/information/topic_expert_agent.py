"""Topic expert agent: concept explanations, related topics, difficulty assessment."""

from typing import TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.orchestrator.types import AgentRequest, AgentResponse, Intent

if TYPE_CHECKING:
    from app.services.llm.provider import LLMProvider


# Small in-memory KB for stub mode (when LLM not configured)
_STUB_CONCEPTS: dict[str, dict[str, str | list[str]]] = {
    "variable": {
        "explanation": "A variable is a named container for a value. It lets you store and reuse data in your program.",
        "related": ["data types", "assignment", "scope"],
        "difficulty": "beginner",
    },
    "function": {
        "explanation": "A function is a reusable block of code that takes inputs (parameters) and can return a value.",
        "related": ["parameters", "return", "modularity"],
        "difficulty": "beginner",
    },
    "algorithm": {
        "explanation": "An algorithm is a step-by-step procedure to solve a problem or perform a computation.",
        "related": ["complexity", "sorting", "search"],
        "difficulty": "intermediate",
    },
    "oop": {
        "explanation": "Object-oriented programming (OOP) organizes code around objects that combine data and behavior.",
        "related": ["class", "inheritance", "encapsulation"],
        "difficulty": "intermediate",
    },
}


def _find_concept_key(message: str) -> str | None:
    """Find a concept key from message (simple keyword match)."""
    msg_lower = message.lower()
    for key in _STUB_CONCEPTS:
        if key in msg_lower or key.replace("_", " ") in msg_lower:
            return key
    if "object" in msg_lower and ("orient" in msg_lower or "oop" in msg_lower):
        return "oop"
    return None


def explain_concept_stub(concept_key: str) -> str:
    """Return explanation from stub KB."""
    entry = _STUB_CONCEPTS.get(concept_key)
    if not entry:
        return f"Concept '{concept_key}' not in knowledge base. Known: {', '.join(_STUB_CONCEPTS.keys())}."
    return str(entry["explanation"])


def get_related_topics_stub(concept_key: str) -> str:
    """Return related topics from stub KB."""
    entry = _STUB_CONCEPTS.get(concept_key)
    if not entry:
        return f"Concept '{concept_key}' not in knowledge base."
    related = entry.get("related", [])
    return f"Related topics: {', '.join(related)}."


def assess_difficulty_stub(concept_key: str) -> str:
    """Return difficulty from stub KB."""
    entry = _STUB_CONCEPTS.get(concept_key)
    if not entry:
        return f"Concept '{concept_key}' not in knowledge base."
    return f"Difficulty: {entry.get('difficulty', 'unknown')}."


class TopicExpertAgent(AbstractBaseAgent):
    """Agent for concept explanations, related topics, and difficulty. Uses LLM when available."""

    def __init__(self, llm_provider: "LLMProvider | None" = None) -> None:
        super().__init__(agent_id="topic_expert", capabilities=[Intent.TOPIC.value])
        self._llm = llm_provider

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Answer concept/topic questions; use LLM if configured else stub KB."""
        msg = (request.message or "").strip()
        concept_key = _find_concept_key(msg)

        if self._llm and msg:
            try:
                content = await self._llm.complete(
                    f"Explain this concept briefly for a student (1–3 sentences): {msg}",
                    temperature=0.3,
                )
                content = (content or "").strip() or explain_concept_stub(concept_key or "variable")
            except Exception:
                content = explain_concept_stub(concept_key or "variable") if concept_key else (
                    "I couldn't generate an explanation right now. "
                    "Try asking about: variable, function, algorithm, oop."
                )
        else:
            if concept_key:
                if "related" in msg.lower():
                    content = get_related_topics_stub(concept_key)
                elif "difficult" in msg.lower():
                    content = assess_difficulty_stub(concept_key)
                else:
                    content = explain_concept_stub(concept_key)
            else:
                content = (
                    "I can explain concepts like: variable, function, algorithm, OOP. "
                    "Ask 'what is X?' or 'explain X'. Known stub concepts: "
                    f"{', '.join(_STUB_CONCEPTS.keys())}."
                )

        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.TOPIC.value, "correlation_id": request.correlation_id},
            error_message=None,
        )
