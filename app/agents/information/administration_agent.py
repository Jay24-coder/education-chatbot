"""Administration agent: policy, deadlines, and procedure information."""

from app.agents.base.base_agent import AbstractBaseAgent
from app.orchestrator.types import AgentRequest, AgentResponse, Intent


# In-memory stub: policies, deadlines, procedures (replace with DB later)
_STUB_POLICIES = [
    {"name": "Attendance", "summary": "Students must attend at least 80% of classes."},
    {"name": "Late submission", "summary": "Assignments lose 10% per day late, up to 3 days; after that not accepted."},
    {"name": "Academic integrity", "summary": "No plagiarism; use of AI must be disclosed per course guidelines."},
]
_STUB_DEADLINES = [
    {"item": "Assignment 1", "due": "Week 3 Friday 23:59"},
    {"item": "Assignment 2", "due": "Week 6 Friday 23:59"},
    {"item": "Final project", "due": "Week 12 Monday 23:59"},
]
_STUB_PROCEDURES = [
    {"name": "Extension request", "steps": "Email instructor before due date with reason; approval at discretion."},
    {"name": "Grade appeal", "steps": "Submit in writing within 2 weeks of grade release; include justification."},
]


def get_policy(keyword: str) -> str:
    """Return policy matching keyword."""
    kw = keyword.lower()
    for p in _STUB_POLICIES:
        if kw in p["name"].lower() or kw in p["summary"].lower():
            return f"**{p['name']}**: {p['summary']}"
    return "No matching policy found. Known policies: Attendance, Late submission, Academic integrity."


def get_deadlines() -> str:
    """Return all deadlines."""
    lines = [f"- **{d['item']}**: {d['due']}" for d in _STUB_DEADLINES]
    return "Deadlines:\n" + "\n".join(lines)


def explain_procedure(name: str) -> str:
    """Explain a procedure by name or keyword."""
    name_lower = name.lower()
    for p in _STUB_PROCEDURES:
        if name_lower in p["name"].lower():
            return f"**{p['name']}**: {p['steps']}"
    return "Procedure not found. Known: Extension request, Grade appeal."


class AdministrationAgent(AbstractBaseAgent):
    """Agent for administration, policies, deadlines, and procedures."""

    def __init__(self) -> None:
        super().__init__(agent_id="administration", capabilities=[Intent.ADMIN.value])

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Answer policy/deadline/procedure questions from stub data."""
        msg = (request.message or "").strip().lower()
        if "deadline" in msg or "due" in msg or "submit" in msg:
            content = get_deadlines()
        elif "policy" in msg or "attendance" in msg or "late" in msg or "integrity" in msg:
            content = get_policy(msg)
        elif "procedure" in msg or "extension" in msg or "appeal" in msg:
            content = explain_procedure(msg)
        else:
            content = (
                "I can help with: **deadlines** (assignment due dates), "
                "**policies** (attendance, late submission, academic integrity), "
                "and **procedures** (extension request, grade appeal). What do you need?"
            )

        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.ADMIN.value, "correlation_id": request.correlation_id},
            error_message=None,
        )
