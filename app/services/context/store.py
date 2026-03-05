"""ContextStore protocol: shared state/context interface for session and conversation.

Session state key conventions (use existing get/set API; keys are namespaced to avoid collisions):

- programming_test:state
  Value shape: challenge id, language, started_at.
  Implemented as: {"challenge": {"id": str, "topic": str, "difficulty": str}, "language": str, "started_at": str}.
  challenge.id identifies the active challenge; language is e.g. "python"; started_at is ISO8601.

- problem_solving:state
  Value shape: stage, topic, difficulty, attempts.
  Implemented as: {"guardrail": {"stage": str, "attempts": int, "confidence_flags": list, "topic": str | null, "difficulty": str | null}, "problem_text": str}.
  guardrail holds the guardrail state machine state; problem_text is the extracted problem statement.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ContextStore(Protocol):
    """Protocol for storing and retrieving session/conversation context."""

    def get(self, session_id: str, key: str | None = None) -> dict[str, Any]:
        """
        Get context for a session. If key is None, return full session context.
        Otherwise return a single key's value wrapped in a dict, or empty dict if missing.
        """
        ...

    def set(self, session_id: str, key: str, value: Any) -> None:
        """Set a value in the session context."""
        ...

    def set_many(self, session_id: str, data: dict[str, Any]) -> None:
        """Set multiple keys in the session context."""
        ...

    def append_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Append a message to conversation history for the session."""
        ...

    def get_history(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Get conversation history (e.g. list of {role, content}). limit caps length."""
        ...

    def delete(self, session_id: str, key: str | None = None) -> None:
        """Delete a key or the entire session if key is None."""
        ...

    # --- Performance / assessment metrics (Phase 2) ---

    def append_assessment_result(self, user_id: str, result: dict[str, Any]) -> None:
        """
        Append an assessment result for a user. Result must include 'type': 'quiz' or 'concept_test';
        typically also topic, score, timestamp, session_id, metadata.
        """
        ...

    def get_performance_summary(self, user_id: str) -> dict[str, Any]:
        """
        Get the performance summary for a user: avg_score, weak_topics, strong_topics, alert_flag.
        Returns default summary dict if user has no data.
        """
        ...

    def update_summary(self, user_id: str) -> None:
        """
        Recompute and persist the performance summary for a user from their metrics
        (e.g. avg_score, weak/strong topics, alert_flag from recent results).
        """
        ...
