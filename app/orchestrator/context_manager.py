"""Context Manager: student/session state and conversation history using ContextStore."""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.context.store import ContextStore


class ContextManager:
    """
    Manages student/session state and conversation history via ContextStore.
    Use persist_turn() after each chat turn so conversation context persists across requests.
    """

    def __init__(self, store: "ContextStore") -> None:
        self._store = store

    def get_session_context(self, session_id: str, key: str | None = None) -> dict[str, Any]:
        """Get session state for routing/agents. If key is None, returns full session dict."""
        if not session_id:
            return {}
        return self._store.get(session_id, key=key)

    def get_conversation_history(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get conversation history (list of {role, content}). limit caps number of messages."""
        if not session_id:
            return []
        return self._store.get_history(session_id, limit=limit)

    def persist_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_content: str,
    ) -> None:
        """Append user and assistant messages to conversation history for the session."""
        if not session_id:
            return
        self._store.append_message(session_id, "user", user_message)
        self._store.append_message(session_id, "assistant", assistant_content)

    def set_state(self, session_id: str, key: str, value: Any) -> None:
        """Set a value in the session state (e.g. student preferences)."""
        if session_id:
            self._store.set(session_id, key, value)

    def set_state_many(self, session_id: str, data: dict[str, Any]) -> None:
        """Set multiple session state keys at once."""
        if session_id and data:
            self._store.set_many(session_id, data)

    def delete_session(self, session_id: str, key: str | None = None) -> None:
        """Delete a session key or the entire session (key=None)."""
        if session_id:
            self._store.delete(session_id, key=key)
