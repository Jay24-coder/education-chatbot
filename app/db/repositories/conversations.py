"""Conversation and message persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.observability.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ConversationRecord:
    id: int
    session_id: Optional[str]
    user_id: Optional[str]
    created_at: Any
    updated_at: Any


@dataclass
class MessageRecord:
    id: int
    conversation_id: int
    role: str
    content: str
    summary: Optional[str]
    correlation_id: Optional[str]
    created_at: Any


class ConversationsRepository:
    """Repository for conversations and messages."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_conversation(
        self,
        session_id: Optional[str] = None,
        *,
        user_id: str,
    ) -> ConversationRecord:
        query = text(
            """
            INSERT INTO conversations (session_id, user_id)
            VALUES (:session_id, :user_id)
            RETURNING id, session_id, user_id, created_at, updated_at
            """
        )
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    query,
                    {"session_id": session_id, "user_id": user_id},
                )
            ).one()

        return ConversationRecord(
            id=row.id,
            session_id=row.session_id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_session_id(self, session_id: str) -> Optional[ConversationRecord]:
        query = text(
            """
            SELECT id, session_id, user_id, created_at, updated_at
            FROM conversations
            WHERE session_id = :session_id
            """
        )
        async with self._engine.connect() as conn:
            result = await conn.execute(query, {"session_id": session_id})
            row = result.one_or_none()

        if row is None:
            return None

        return ConversationRecord(
            id=row.id,
            session_id=row.session_id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_or_create_conversation(
        self,
        session_id: str,
        user_id: str,
    ) -> ConversationRecord:
        insert_query = text(
            """
            INSERT INTO conversations (session_id, user_id)
            VALUES (:session_id, :user_id)
            ON CONFLICT (session_id) DO NOTHING
            RETURNING id, session_id, user_id, created_at, updated_at
            """
        )
        select_query = text(
            """
            SELECT id, session_id, user_id, created_at, updated_at
            FROM conversations
            WHERE session_id = :session_id
            """
        )
        async with self._engine.begin() as conn:
            result = await conn.execute(
                insert_query,
                {"session_id": session_id, "user_id": user_id},
            )
            row = result.one_or_none()
            if row is None:
                result = await conn.execute(select_query, {"session_id": session_id})
                row = result.one_or_none()

        if row is None:
            raise RuntimeError(
                f"get_or_create_conversation: no row after insert/select for session_id={session_id!r}"
            )

        return ConversationRecord(
            id=row.id,
            session_id=row.session_id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        *,
        summary: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> MessageRecord:
        query = text(
            """
            INSERT INTO messages (conversation_id, role, content, summary, correlation_id)
            VALUES (:conversation_id, :role, :content, :summary, :correlation_id)
            RETURNING id, conversation_id, role, content, summary, correlation_id, created_at
            """
        )
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    query,
                    {
                        "conversation_id": conversation_id,
                        "role": role,
                        "content": content,
                        "summary": summary,
                        "correlation_id": correlation_id,
                    },
                )
            ).one()

        logger.info(
            "message_persisted",
            conversation_id=conversation_id,
            role=role,
            has_summary_param=summary is not None,
            has_summary_db=row.summary is not None,
            summary_param_preview=(summary[:120] if summary else None),
            summary_db_preview=(row.summary[:120] if row.summary else None),
            correlation_id=correlation_id,
        )

        return MessageRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            role=row.role,
            content=row.content,
            summary=row.summary,
            correlation_id=row.correlation_id,
            created_at=row.created_at,
        )

    async def get_conversation(self, conversation_id: int) -> Optional[ConversationRecord]:
        query = text(
            """
            SELECT id, session_id, user_id, created_at, updated_at
            FROM conversations
            WHERE id = :conversation_id
            """
        )
        async with self._engine.connect() as conn:
            result = await conn.execute(query, {"conversation_id": conversation_id})
            row = result.one_or_none()

        if row is None:
            return None

        return ConversationRecord(
            id=row.id,
            session_id=row.session_id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = 50,
    ) -> List[ConversationRecord]:
        """Return recent conversations for a user, ordered by most recently updated."""
        query = text(
            """
            SELECT id, session_id, user_id, created_at, updated_at
            FROM conversations
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            LIMIT :limit
            """
        )
        async with self._engine.connect() as conn:
            result = await conn.execute(
                query,
                {"user_id": user_id, "limit": limit},
            )
            rows = result.fetchall()

        return [
            ConversationRecord(
                id=row.id,
                session_id=row.session_id,
                user_id=row.user_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 50,
    ) -> List[MessageRecord]:
        query = text(
            """
            SELECT id, conversation_id, role, content, summary, correlation_id, created_at
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        async with self._engine.connect() as conn:
            result = await conn.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "limit": limit,
                },
            )
            rows = result.fetchall()

        return [
            MessageRecord(
                id=row.id,
                conversation_id=row.conversation_id,
                role=row.role,
                content=row.content,
                summary=row.summary,
                correlation_id=row.correlation_id,
                created_at=row.created_at,
            )
            for row in rows
        ]

