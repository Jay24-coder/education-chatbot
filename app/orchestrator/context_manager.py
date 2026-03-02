"""Context Manager: student/session state and conversation history using ContextStore."""

import asyncio
import inspect
from typing import Any, TYPE_CHECKING

from app.observability.logging import get_logger
from app.utils.errors import OrchestratorError

if TYPE_CHECKING:
    from app.services.context.store import ContextStore


logger = get_logger(__name__)


class ContextManager:
    """
    Manages student/session state and conversation history via ContextStore.
    Use persist_turn() after each chat turn so conversation context persists across requests.
    """

    def __init__(self, store: "ContextStore") -> None:
        self._store = store

    def _maybe_schedule(
        self,
        result: Any,
        *,
        session_id: str,
        role: str,
        correlation_id: str | None = None,
    ) -> None:
        """
        If result is an awaitable (e.g. coroutine from an async ContextStore),
        execute it and log failures in a structured way.
        """
        if not inspect.isawaitable(result):
            return

        async def _run_with_logging() -> None:
            try:
                await result
                logger.info(
                    "context_persist_success",
                    session_id=session_id or None,
                    role=role,
                    correlation_id=correlation_id,
                )
            except Exception as e:  # pragma: no cover - defensive logging
                logger.error(
                    "context_persist_failed",
                    session_id=session_id or None,
                    role=role,
                    correlation_id=correlation_id,
                    error=str(e),
                    exc_info=True,
                )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (e.g. synchronous test context); block until done.
            asyncio.run(_run_with_logging())
        else:
            loop.create_task(_run_with_logging())

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
        user_id: str,
        user_message: str,
        assistant_content: str,
        correlation_id: str | None = None,
    ) -> None:
        """Append user and assistant messages to conversation history for the session."""
        if not session_id:
            return
        user_result = self._store.append_message(session_id, user_id, "user", user_message)
        self._maybe_schedule(
            user_result,
            session_id=session_id,
            role="user",
            correlation_id=correlation_id,
        )
        assistant_result = self._store.append_message(session_id, user_id, "assistant", assistant_content)
        self._maybe_schedule(
            assistant_result,
            session_id=session_id,
            role="assistant",
            correlation_id=correlation_id,
        )

    async def persist_turn_strict(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_content: str,
        correlation_id: str | None = None,
    ) -> None:
        """
        Persist user and assistant messages in a blocking way.

        Any error during persistence is treated as a hard failure and surfaced as
        an OrchestratorError so the chat flow stops and the client sees a clear
        "temporarily down" style message.
        """
        if not session_id:
            return

        try:
            user_result = self._store.append_message(session_id, user_id, "user", user_message)
            if inspect.isawaitable(user_result):
                await user_result

            assistant_result = self._store.append_message(
                session_id, user_id, "assistant", assistant_content
            )
            if inspect.isawaitable(assistant_result):
                await assistant_result

            logger.info(
                "context_persist_success",
                session_id=session_id or None,
                role="user+assistant",
                correlation_id=correlation_id,
            )
        except Exception as e:  # pragma: no cover - defensive propagation
            logger.error(
                "context_persist_failed",
                session_id=session_id or None,
                role="user+assistant",
                correlation_id=correlation_id,
                error=str(e),
                exc_info=True,
            )
            raise OrchestratorError(
                "Sorry, we are temporarily down. Please try again later.",
                code="PERSISTENCE_ERROR",
            ) from e

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
