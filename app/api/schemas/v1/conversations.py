"""Pydantic models for conversation listing and message history."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    """Minimal information about a conversation for sidebar listing."""

    id: int = Field(..., description="Conversation identifier")
    session_id: str | None = Field(
        default=None, description="Session ID associated with this conversation"
    )
    title: str = Field(..., description="Conversation title or first user message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ConversationListResponse(BaseModel):
    """Envelope for a list of conversations."""

    conversations: List[ConversationSummary] = Field(
        default_factory=list, description="Recent conversations for the user"
    )


class ConversationMessage(BaseModel):
    """Single message within a conversation."""

    id: int = Field(..., description="Message identifier")
    conversation_id: int = Field(..., description="Conversation identifier")
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")


class ConversationMessagesResponse(BaseModel):
    """Envelope for conversation message history."""

    conversation_id: int = Field(..., description="Conversation identifier")
    messages: List[ConversationMessage] = Field(
        default_factory=list, description="Messages ordered from oldest to newest"
    )

