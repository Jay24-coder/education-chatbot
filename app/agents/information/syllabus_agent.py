"""Syllabus agent: curriculum data, course info, prerequisites, syllabus search."""

from app.agents.base.base_agent import AbstractBaseAgent
from app.orchestrator.types import AgentRequest, AgentResponse, Intent


# In-memory stub: course outline and prerequisites (replace with DB later)
_STUB_COURSE = {
    "name": "Introduction to Computer Science",
    "code": "CS101",
    "outline": "Programming fundamentals, data structures, algorithms, and software design.",
    "prerequisites": ["Basic algebra", "No prior programming required"],
    "topics": [
        "Variables and types",
        "Control flow",
        "Functions",
        "Lists and dictionaries",
        "Object-oriented programming",
        "Basic algorithms",
        "Testing and debugging",
    ],
}


def get_course_info() -> str:
    """Return high-level course information."""
    c = _STUB_COURSE
    return (
        f"**{c['name']}** ({c['code']})\n\n"
        f"Outline: {c['outline']}\n\n"
        f"Topics covered: {', '.join(c['topics'])}."
    )


def get_prerequisites() -> str:
    """Return course prerequisites."""
    c = _STUB_COURSE
    return (
        f"Prerequisites for {c['name']} ({c['code']}): "
        f"{', '.join(c['prerequisites'])}."
    )


def search_syllabus(message: str) -> str:
    """Search syllabus/topics by keyword; return matching info."""
    msg_lower = message.lower()
    c = _STUB_COURSE
    # Match topics
    matches = [t for t in c["topics"] if msg_lower in t.lower()]
    if matches:
        return (
            f"Relevant syllabus topics: {', '.join(matches)}. "
            f"Full outline: {c['outline']}"
        )
    if any(k in msg_lower for k in ("syllabus", "curriculum", "outline", "topics")):
        return get_course_info()
    if "prerequisite" in msg_lower:
        return get_prerequisites()
    return get_course_info()


class SyllabusAgent(AbstractBaseAgent):
    """Agent for syllabus, curriculum, and course info queries."""

    def __init__(self) -> None:
        super().__init__(agent_id="syllabus", capabilities=[Intent.SYLLABUS.value])

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Answer syllabus/course/prerequisite questions from stub data."""
        msg = (request.message or "").strip().lower()
        if not msg:
            content = get_course_info()
        elif "prerequisite" in msg:
            content = get_prerequisites()
        else:
            content = search_syllabus(request.message or "")

        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.SYLLABUS.value, "correlation_id": request.correlation_id},
            error_message=None,
        )
