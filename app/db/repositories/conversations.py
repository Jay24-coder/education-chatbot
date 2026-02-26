"""Conversation and message persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class ConversationRecord:
    id: int
    user_id: Optional[str]
    created_at: Any
    updated_at: Any


@dataclass
class MessageRecord:
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: Any


class ConversationsRepository:
    """Repository for conversations and messages."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_conversation(self, user_id: Optional[str] = None) -> ConversationRecord:
        query = text(
            """
            INSERT INTO conversations (user_id)
            VALUES (:user_id)
            RETURNING id, user_id, created_at, updated_at
            """
        )
        async with self._engine.begin() as conn:
            row = (await conn.execute(query, {"user_id": user_id})).one()

        return ConversationRecord(
            id=row.id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> MessageRecord:
        query = text(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (:conversation_id, :role, :content)
            RETURNING id, conversation_id, role, content, created_at
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
                    },
                )
            ).one()

        return MessageRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
        )

    async def get_conversation(self, conversation_id: int) -> Optional[ConversationRecord]:
        query = text(
            """
            SELECT id, user_id, created_at, updated_at
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
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 50,
    ) -> List[MessageRecord]:
        query = text(
            """
            SELECT id, conversation_id, role, content, created_at
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
                created_at=row.created_at,
            )
            for row in rows
        ]

