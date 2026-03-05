"""Conversation listing and message history endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.v1.conversations import (
    ConversationListResponse,
    ConversationMessage,
    ConversationMessagesResponse,
    ConversationSummary,
)
from app.db.pool import get_engine
from app.db.repositories.conversations import ConversationsRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversations_repo() -> ConversationsRepository:
    """Provide ConversationsRepository for HTTP handlers."""
    engine = get_engine()
    return ConversationsRepository(engine)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List recent conversations for a user",
)
async def list_conversations(
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of conversations"),
    repo: ConversationsRepository = Depends(get_conversations_repo),
) -> ConversationListResponse:
    records = await repo.list_for_user(user_id=user_id, limit=limit)

    # For now, derive a simple title from the first message content if available.
    # Title generation can be moved to a dedicated job later.
    summaries: List[ConversationSummary] = []
    for record in records:
        # Fallback title based on session id if nothing else is available.
        title = f"Conversation {record.id}"
        summaries.append(
            ConversationSummary(
                id=record.id,
                session_id=record.session_id,
                title=title,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )

    return ConversationListResponse(conversations=summaries)


@router.get(
    "/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
    summary="Get recent messages for a conversation",
)
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of messages"),
    repo: ConversationsRepository = Depends(get_conversations_repo),
) -> ConversationMessagesResponse:
    conversation = await repo.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    records = await repo.get_recent_messages(conversation_id=conversation_id, limit=limit)

    # Repository returns newest first; reverse to oldest → newest for the UI.
    ordered_records = list(reversed(records))

    messages: List[ConversationMessage] = [
        ConversationMessage(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in ordered_records
    ]

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
    )

