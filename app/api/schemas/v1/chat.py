"""Pydantic request/response models for the chat API (v1)."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str = Field(..., min_length=1, description="User message content")
    session_id: str | None = Field(default=None, description="Session ID for conversation context")
    user_id: str | None = Field(default=None, description="Optional user identifier")


class ChatResponse(BaseModel):
    """Response body for the chat endpoint."""

    content: str = Field(..., description="Assistant response content")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, description="Request correlation ID")
