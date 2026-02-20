"""In-memory implementation of ContextStore."""

from typing import Any

from app.services.context.store import ContextStore


class MemoryStore:
    """Minimal in-memory ContextStore for session and conversation state."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}

    def get(self, session_id: str, key: str | None = None) -> dict[str, Any]:
        session = self._sessions.get(session_id, {})
        if key is None:
            return dict(session)
        return {key: session[key]} if key in session else {}

    def set(self, session_id: str, key: str, value: Any) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        self._sessions[session_id][key] = value

    def set_many(self, session_id: str, data: dict[str, Any]) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        self._sessions[session_id].update(data)

    def append_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].append({"role": role, "content": content})

    def get_history(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        history = self._history.get(session_id, [])
        if limit is not None:
            history = history[-limit:]
        return list(history)

    def delete(self, session_id: str, key: str | None = None) -> None:
        if key is None:
            self._sessions.pop(session_id, None)
            self._history.pop(session_id, None)
        elif session_id in self._sessions:
            self._sessions[session_id].pop(key, None)
