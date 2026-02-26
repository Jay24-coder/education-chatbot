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


# --- Programming test ---


class ProgrammingTestStartRequest(BaseModel):
    """Request body for starting a programming test."""

    session_id: str = Field(..., min_length=1, description="Session ID for programming test state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    topic: str | None = Field(default=None, description="Optional topic filter for the challenge bank")
    language: str | None = Field(default=None, description="Preferred programming language (e.g. python)")


class ProgrammingTestSubmitRequest(BaseModel):
    """Request body for submitting a programming solution."""

    session_id: str = Field(..., min_length=1, description="Session ID for programming test state")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    code: str = Field(..., description="Student's solution code")


class ProgrammingTestCaseResult(BaseModel):
    """Per-test-case execution result for a programming challenge."""

    test_case_id: str = Field(..., description="Identifier of the test case")
    passed: bool = Field(..., description="True if the test case passed")
    actual_output: str | None = Field(default=None, description="Actual output from executing the code")
    expected_output: str | None = Field(default=None, description="Expected output for the test case")
    error: str | None = Field(default=None, description="Error message if execution failed")
    execution_time_ms: float | None = Field(default=None, description="Execution time in milliseconds, if available")


class ProgrammingTestResponse(BaseModel):
    """Response body for programming test start or submission."""

    content: str = Field(..., description="Problem statement, feedback, or final summary")
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    completed: bool = Field(default=False, description="True when the programming test is finalized")
    test_case_results: list[ProgrammingTestCaseResult] = Field(
        default_factory=list,
        description="Per-test-case execution results when code has been run",
    )


class ProgrammingTestJobResponse(BaseModel):
    """Response body for async programming test submission (job-based)."""

    job_id: int = Field(..., description="Job identifier for async programming test execution")
    status: str = Field(..., description="Initial job status, typically PENDING")


# --- Performance ---


class PerformanceSummaryResponse(BaseModel):
    """Response body for GET performance summary."""

    avg_score: float = Field(..., ge=0, le=1, description="Average score (recent assessments)")
    weak_topics: list[str] = Field(default_factory=list, description="Topics to review")
    strong_topics: list[str] = Field(default_factory=list, description="Strong topics")
    alert_flag: bool = Field(default=False, description="True if user may need extra support")
