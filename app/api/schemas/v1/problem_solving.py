"""Request/response models for the problem-solving API (v1)."""

from typing import Any

from pydantic import BaseModel, Field


class ProblemSolvingStartRequest(BaseModel):
    """JSON body for starting a problem-solving session with an image."""

    session_id: str = Field(..., min_length=1, description="Session ID for conversation state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    image_base64: str | None = Field(default=None, description="Base64-encoded problem image (for JSON upload)")
    message: str | None = Field(default=None, description="Optional message or caption with the image")


class ProblemSolvingStartResponse(BaseModel):
    """Response for problem-solving start (probe question or error)."""

    content: str = Field(..., description="Assistant response (probe question or error)")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProblemSolvingRespondRequest(BaseModel):
    """Request body for submitting a text answer in an existing problem-solving session."""

    session_id: str = Field(..., min_length=1, description="Session ID for problem-solving state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    answer: str = Field(..., description="Student's text answer or reply")


class ProblemSolvingRespondResponse(BaseModel):
    """Response for problem-solving respond (hint, concept, or next probe)."""

    content: str = Field(..., description="Assistant response")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
