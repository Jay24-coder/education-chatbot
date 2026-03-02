"""Shared types for orchestration: requests, responses, and intent."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssessmentResult(BaseModel):
    """Result of a quiz or concept test for performance logging."""

    user_id: str = Field(..., description="User identifier")
    session_id: str | None = Field(default=None, description="Session when assessment was taken")
    type: str = Field(..., description="Assessment type: 'quiz' or 'concept_test'")
    topic: str = Field(default="", description="Topic or subject area")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score 0–1")
    timestamp: str | None = Field(default=None, description="When the assessment was completed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional extra data")


class Intent(str, Enum):
    """Classified intent for routing to the appropriate agent."""

    SYLLABUS = "syllabus"
    ADMIN = "admin"
    TOPIC = "topic"
    QUIZ = "quiz"
    CONCEPT_TEST = "concept_test"
    PROGRAMMING_TEST = "programming_test"
    ASSESSMENT = "assessment"
    PERFORMANCE = "performance"
    VISUALIZATION = "visualization"
    PROBLEM_SOLVING = "problem_solving"
    UNKNOWN = "unknown"


class UserRequest(BaseModel):
    """Incoming user request from the API."""

    message: str = Field(..., min_length=1, description="User message content")
    session_id: str | None = Field(default=None, description="Session for context")
    correlation_id: str | None = Field(default=None, description="Request correlation ID")
    user_id: str = Field(..., min_length=1, description="User identifier")


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
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional keys for assessment: result_type, score, topic",
    )
    error_message: str | None = None
