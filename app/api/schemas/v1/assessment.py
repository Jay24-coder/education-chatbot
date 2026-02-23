"""Pydantic request/response models for the assessment API (v1)."""

from typing import Any

from pydantic import BaseModel, Field


# --- Quiz ---


class QuizStartRequest(BaseModel):
    """Request body for starting a quiz."""

    session_id: str = Field(..., min_length=1, description="Session ID for quiz state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    topic: str | None = Field(default=None, description="Topic (e.g. algebra, calculus)")
    difficulty: str | None = Field(default=None, description="Difficulty: beginner, intermediate, advanced")


class QuizAnswerRequest(BaseModel):
    """Request body for submitting a quiz answer."""

    session_id: str = Field(..., min_length=1, description="Session ID for quiz state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    answer: str = Field(..., description="Student's answer (option letter or text)")


class QuizResponse(BaseModel):
    """Response body for quiz start or answer."""

    content: str = Field(..., description="Question text or feedback and next question")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    completed: bool = Field(default=False, description="True when quiz is finalized")


# --- Concept test ---


class ConceptTestStartRequest(BaseModel):
    """Request body for starting a concept test."""

    session_id: str = Field(..., min_length=1, description="Session ID for concept test state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    topic: str | None = Field(default=None, description="Topic for the concept test")


class ConceptTestTurnRequest(BaseModel):
    """Request body for submitting a concept test answer (or finalizing)."""

    session_id: str = Field(..., min_length=1, description="Session ID for concept test state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    answer: str = Field(..., description="Student's answer, or 'done' / 'finish' to complete")


class ConceptTestResponse(BaseModel):
    """Response body for concept test start or turn."""

    content: str = Field(..., description="Question text, feedback, or final summary")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    completed: bool = Field(default=False, description="True when concept test is finalized")


# --- Performance ---


class PerformanceSummaryResponse(BaseModel):
    """Response body for GET performance summary."""

    avg_score: float = Field(..., ge=0, le=1, description="Average score (recent assessments)")
    weak_topics: list[str] = Field(default_factory=list, description="Topics to review")
    strong_topics: list[str] = Field(default_factory=list, description="Strong topics")
    alert_flag: bool = Field(default=False, description="True if user may need extra support")
