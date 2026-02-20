"""Shared types for orchestration: requests, responses, and intent."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Intent(str, Enum):
    """Classified intent for routing to the appropriate agent."""

    SYLLABUS = "syllabus"
    ADMIN = "admin"
    TOPIC = "topic"
    UNKNOWN = "unknown"


class UserRequest(BaseModel):
    """Incoming user request from the API."""

    message: str = Field(..., min_length=1, description="User message content")
    session_id: str | None = Field(default=None, description="Session for context")
    correlation_id: str | None = Field(default=None, description="Request correlation ID")
    user_id: str | None = Field(default=None, description="Optional user identifier")


class AgentRequest(BaseModel):
    """Request passed from orchestrator to an agent."""

    message: str = Field(..., min_length=1)
    session_id: str | None = None
    correlation_id: str | None = None
    intent: Intent = Intent.UNKNOWN
    context: dict[str, Any] = Field(default_factory=dict, description="Session/context snapshot")


class AgentResponse(BaseModel):
    """Response returned by an agent to the orchestrator."""

    content: str = Field(..., description="Agent response content")
    agent_id: str = Field(..., description="ID of the agent that produced the response")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
