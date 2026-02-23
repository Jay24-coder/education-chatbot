"""Performance Monitor Agent: logs assessment results and returns human-readable progress summaries."""

from typing import TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.orchestrator.types import AgentRequest, AgentResponse, AssessmentResult, Intent

if TYPE_CHECKING:
    from app.services.context.store import ContextStore


def _result_to_dict(result: AssessmentResult) -> dict:
    """Convert AssessmentResult to the dict shape expected by ContextStore.append_assessment_result."""
    return {
        "type": (result.type or "").strip().lower() or "quiz",
        "topic": result.topic or "",
        "score": result.score,
        "timestamp": result.timestamp,
        "session_id": result.session_id,
        "metadata": result.metadata or {},
    }


def format_performance_response(summary: dict) -> str:
    """
    Format performance summary as human-readable text. Flags weak topics.
    summary: dict with avg_score, weak_topics, strong_topics, alert_flag.
    """
    avg = summary.get("avg_score", 0.0)
    weak = summary.get("weak_topics") or []
    strong = summary.get("strong_topics") or []
    alert = summary.get("alert_flag", False)

    lines = [
        "**Your performance summary**",
        f"- **Average score (recent):** {avg:.0%}",
    ]
    if strong:
        lines.append(f"- **Strong topics:** {', '.join(strong)}")
    if weak:
        lines.append(f"- **Topics to review:** {', '.join(weak)}")
    if alert:
        lines.append("\nConsider spending more time on the topics listed above.")
    if not weak and not strong and avg == 0.0:
        lines.append("\nNo assessment data yet. Complete a quiz or concept test to see your progress.")
    return "\n".join(lines)


class PerformanceMonitorAgent(AbstractBaseAgent):
    """
    Agent for PERFORMANCE intent (e.g. 'show my progress').
    Logs assessment results to ContextStore and returns formatted performance summaries.
    """

    def __init__(self, context_store: "ContextStore") -> None:
        super().__init__(
            agent_id="performance_monitor",
            capabilities=[Intent.PERFORMANCE.value, Intent.ASSESSMENT.value],
        )
        self._store = context_store

    def log_result(self, user_id: str, result: AssessmentResult) -> None:
        """
        Write an assessment result to the ContextStore and recompute the user's summary.
        Used by Quiz/Concept Test agents to record scores.
        """
        self._store.append_assessment_result(user_id, _result_to_dict(result))
        self._store.update_summary(user_id)

    def get_summary(self, user_id: str) -> dict:
        """
        Read performance metrics from ContextStore: recomputes summary then returns
        avg_score, weak_topics, strong_topics, alert_flag.
        """
        self._store.update_summary(user_id)
        return self._store.get_performance_summary(user_id)

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Handle PERFORMANCE intent (e.g. 'show my progress').
        Resolves user_id from request context or session_id, then returns formatted summary.
        """
        user_id = (request.context or {}).get("user_id") or request.session_id or "default"
        summary = self.get_summary(user_id)
        content = format_performance_response(summary)
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={
                "intent": Intent.PERFORMANCE.value,
                "correlation_id": request.correlation_id,
                "weak_topics": summary.get("weak_topics", []),
                "alert_flag": summary.get("alert_flag", False),
            },
            error_message=None,
        )
