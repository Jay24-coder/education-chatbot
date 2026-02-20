"""ContextStore protocol: shared state/context interface for session and conversation."""

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

    def append_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to conversation history for the session."""
        ...

    def get_history(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Get conversation history (e.g. list of {role, content}). limit caps length."""
        ...

    def delete(self, session_id: str, key: str | None = None) -> None:
        """Delete a key or the entire session if key is None."""
        ...
