"""Postgres + Redis-backed implementation of ContextStore."""

from __future__ import annotations

from typing import Any, Optional

from app.db.repositories.conversations import ConversationsRepository
from app.db.repositories.jobs import JobsRepository
from app.infra.redis import cache as redis_cache
from app.services.context.store import ContextStore


class PostgresContextStore:
    """ContextStore backed by Postgres (conversations/jobs) plus Redis cache."""

    def __init__(
        self,
        conversations_repo: ConversationsRepository,
        jobs_repo: Optional[JobsRepository] = None,
        *,
        conversation_ttl_sec: int = 300,
        job_status_ttl_sec: int = 300,
    ) -> None:
        self._conversations_repo = conversations_repo
        self._jobs_repo = jobs_repo
        self._conversation_ttl_sec = conversation_ttl_sec
        self._job_status_ttl_sec = job_status_ttl_sec

    # --- Session state (non-conversation) ---
    # For now, keep minimal implementation in Postgres-backed store by delegating
    # to an in-memory dict. This can be moved to Postgres later if needed.

    def _ensure_session(self, session_id: str) -> None:
        if not hasattr(self, "_sessions"):
            self._sessions: dict[str, dict[str, Any]] = {}
        if session_id not in self._sessions:
            self._sessions[session_id] = {}

    def get(self, session_id: str, key: str | None = None) -> dict[str, Any]:
        self._ensure_session(session_id)
        session = self._sessions.get(session_id, {})
        if key is None:
            return dict(session)
        return {key: session[key]} if key in session else {}

    def set(self, session_id: str, key: str, value: Any) -> None:
        self._ensure_session(session_id)
        self._sessions[session_id][key] = value

    def set_many(self, session_id: str, data: dict[str, Any]) -> None:
        self._ensure_session(session_id)
        self._sessions[session_id].update(data)

    # --- Conversation history ---

    async def append_message(self, session_id: str, role: str, content: str) -> None:  # type: ignore[override]
        # Use session_id as conversation identifier at this layer.
        conv_id = int(session_id)

        # Append to Postgres
        await self._conversations_repo.append_message(conv_id, role, content)

        # Invalidate or refresh cache
        await redis_cache.invalidate_conversation(session_id)

    async def get_history(  # type: ignore[override]
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        # Try cache first
        cached = await redis_cache.get_cached_conversation(session_id)
        if cached is not None:
            messages = cached
        else:
            conv_id = int(session_id)
            repo_limit = limit or 50
            records = await self._conversations_repo.get_recent_messages(conv_id, limit=repo_limit)
            messages = [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
                for m in records
            ]
            await redis_cache.set_cached_conversation(
                session_id,
                messages,
                ttl_sec=self._conversation_ttl_sec,
            )

        if limit is not None:
            return messages[-limit:]
        return messages

    async def delete(self, session_id: str, key: str | None = None) -> None:  # type: ignore[override]
        if key is None:
            # Only clear Redis cache. Actual row deletion is left to a dedicated cleanup job.
            await redis_cache.invalidate_conversation(session_id)
            if hasattr(self, "_sessions"):
                self._sessions.pop(session_id, None)
        else:
            self._ensure_session(session_id)
            self._sessions[session_id].pop(key, None)

    # --- Performance / assessment metrics (Phase 2) ---

    def append_assessment_result(self, user_id: str, result: dict[str, Any]) -> None:
        # For now, keep metrics in-memory even when using Postgres context.
        if not hasattr(self, "_perf_store"):
            self._perf_store: dict[str, list[dict[str, Any]]] = {}
        if user_id not in self._perf_store:
            self._perf_store[user_id] = []
        self._perf_store[user_id].append(result)

    def get_performance_summary(self, user_id: str) -> dict[str, Any]:
        # Minimal placeholder; can later be wired to Postgres tables.
        return {}

    def update_summary(self, user_id: str) -> None:
        # Placeholder for future Postgres-backed summaries.
        return


assert isinstance(PostgresContextStore, ContextStore)  # type: ignore[arg-type]

