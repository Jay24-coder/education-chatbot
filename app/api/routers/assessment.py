"""Assessment API: quiz start/answer, concept test start/answer, performance summary."""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    get_concept_test_agent,
    get_performance_monitor,
    get_programming_test_agent,
    get_quiz_agent,
)
from app.api.schemas.v1.assessment import (
    ConceptTestResponse,
    ConceptTestStartRequest,
    ConceptTestTurnRequest,
    PerformanceSummaryResponse,
    ProgrammingTestResponse,
    ProgrammingTestStartRequest,
    ProgrammingTestSubmitRequest,
    ProgrammingTestJobResponse,
    QuizAnswerRequest,
    QuizResponse,
    QuizStartRequest,
)
from app.agents.shared_tools.code_execution import (
    CodeExecutionTimeoutError,
    SandboxError,
    UnsafeCodeError,
)
from app.db.pool import get_engine
from app.db.repositories.jobs import JobsRepository
from app.infra.redis import queues
from app.observability.logging import get_logger
from app.orchestrator.types import AgentRequest, Intent

if TYPE_CHECKING:
    from app.agents.assessment.concept_test_agent import ConceptTestAgent
    from app.agents.assessment.programming_test_agent import ProgrammingTestAgent
    from app.agents.assessment.quiz_agent import QuizAgent
    from app.agents.monitoring.performance_monitor_agent import PerformanceMonitorAgent

router = APIRouter(prefix="/assessment", tags=["assessment"])
logger = get_logger(__name__)


def _context(user_id: str | None, session_id: str) -> dict:
    out: dict = {}
    if user_id:
        out["user_id"] = user_id
    return out


def _raise_for_quiz_failure(content: str, success: bool) -> None:
    if success:
        return
    if "no quiz in progress" in content.lower():
        raise HTTPException(status_code=404, detail=content)  # QuizNotFoundError
    if "no quiz to finalize" in content.lower():
        raise HTTPException(status_code=409, detail=content)  # TestAlreadyCompleteError
    if "no questions available" in content.lower():
        raise HTTPException(status_code=404, detail=content)
    raise HTTPException(status_code=400, detail=content or "Quiz request failed")


def _raise_for_concept_test_failure(content: str, success: bool) -> None:
    if success:
        return
    if "no concept test in progress" in content.lower():
        raise HTTPException(status_code=404, detail=content)  # QuizNotFoundError
    if "no concept test to finalize" in content.lower():
        raise HTTPException(status_code=409, detail=content)  # TestAlreadyCompleteError
    if "not available" in content.lower() and "llm" in content.lower():
        raise HTTPException(status_code=503, detail=content)
    raise HTTPException(status_code=400, detail=content or "Concept test request failed")


def _raise_for_programming_test_failure(content: str, success: bool) -> None:
    if success:
        return
    lowered = content.lower()
    if "no programming test in progress" in lowered:
        raise HTTPException(status_code=404, detail=content)
    raise HTTPException(status_code=400, detail=content or "Programming test request failed")


@router.post(
    "/quiz/start",
    response_model=QuizResponse,
    responses={
        400: {"description": "Invalid request or session"},
        404: {"description": "Quiz not available"},
        503: {"description": "Assessment service unavailable"},
    },
)
async def quiz_start(
    body: QuizStartRequest,
    quiz_agent: "QuizAgent | None" = Depends(get_quiz_agent),
) -> QuizResponse:
    """Start a new quiz. Requires session_id; optional topic and difficulty."""
    logger.info(
        "assessment_quiz_start_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if quiz_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")
    message_parts = ["start quiz"]
    if body.topic:
        message_parts.append(body.topic)
    if body.difficulty:
        message_parts.append(body.difficulty)
    message = " ".join(message_parts)
    context = _context(body.user_id, body.session_id)
    response = await quiz_agent.start_quiz(body.session_id, message, context)
    _raise_for_quiz_failure(response.content, response.success)
    logger.info(
        "assessment_quiz_start_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        completed=response.metadata.get("result_type") == "quiz",
    )
    return QuizResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata,
        completed=response.metadata.get("result_type") == "quiz",
    )


@router.post(
    "/quiz/answer",
    response_model=QuizResponse,
    responses={
        400: {"description": "Invalid request or session"},
        404: {"description": "No quiz in progress"},
        409: {"description": "Quiz already complete"},
        503: {"description": "Assessment service unavailable"},
    },
)
async def quiz_answer(
    body: QuizAnswerRequest,
    quiz_agent: "QuizAgent | None" = Depends(get_quiz_agent),
) -> QuizResponse:
    """Submit an answer for the current quiz question."""
    logger.info(
        "assessment_quiz_answer_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if quiz_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")
    context = _context(body.user_id, body.session_id)
    response = await quiz_agent.submit_answer(body.session_id, body.answer, context)
    _raise_for_quiz_failure(response.content, response.success)
    logger.info(
        "assessment_quiz_answer_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        completed=response.metadata.get("result_type") == "quiz",
    )
    return QuizResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata,
        completed=response.metadata.get("result_type") == "quiz",
    )


@router.post(
    "/concept-test/start",
    response_model=ConceptTestResponse,
    responses={
        400: {"description": "Invalid request or session"},
        503: {"description": "Concept test not available (LLM required)"},
    },
)
async def concept_test_start(
    body: ConceptTestStartRequest,
    concept_test_agent: "ConceptTestAgent | None" = Depends(get_concept_test_agent),
) -> ConceptTestResponse:
    """Start a new concept test. Requires session_id; optional topic."""
    logger.info(
        "assessment_concept_test_start_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if concept_test_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")
    message = f"concept test on {body.topic}" if body.topic else "start concept test"
    context = _context(body.user_id, body.session_id)
    response = await concept_test_agent.start_concept_test(body.session_id, message, context)
    _raise_for_concept_test_failure(response.content, response.success)
    logger.info(
        "assessment_concept_test_start_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        completed=response.metadata.get("result_type") == "concept_test",
    )
    return ConceptTestResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata,
        completed=response.metadata.get("result_type") == "concept_test",
    )


@router.post(
    "/concept-test/answer",
    response_model=ConceptTestResponse,
    responses={
        400: {"description": "Invalid request or session"},
        404: {"description": "No concept test in progress"},
        409: {"description": "Concept test already complete"},
        503: {"description": "Assessment service unavailable"},
    },
)
async def concept_test_answer(
    body: ConceptTestTurnRequest,
    concept_test_agent: "ConceptTestAgent | None" = Depends(get_concept_test_agent),
) -> ConceptTestResponse:
    """Submit an answer for the current concept test question, or send 'done' to finalize."""
    logger.info(
        "assessment_concept_test_answer_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if concept_test_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")
    context = _context(body.user_id, body.session_id)
    request = AgentRequest(
        message=body.answer,
        session_id=body.session_id,
        intent=Intent.CONCEPT_TEST,
        context=context,
    )
    response = await concept_test_agent.process_request(request)
    _raise_for_concept_test_failure(response.content, response.success)
    logger.info(
        "assessment_concept_test_answer_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        completed=response.metadata.get("result_type") == "concept_test",
    )
    return ConceptTestResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata,
        completed=response.metadata.get("result_type") == "concept_test",
    )


@router.post(
    "/programming-test/start",
    response_model=ProgrammingTestResponse,
    responses={
        400: {"description": "Invalid request or session"},
        503: {"description": "Assessment service unavailable"},
    },
)
async def programming_test_start(
    body: ProgrammingTestStartRequest,
    programming_agent: "ProgrammingTestAgent | None" = Depends(get_programming_test_agent),
) -> ProgrammingTestResponse:
    """Start a new programming test. Requires session_id; optional topic and language."""
    logger.info(
        "assessment_programming_test_start_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if programming_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")

    # For now language is fixed to Python in the executor; topic may influence challenge selection.
    message_parts = ["start programming test"]
    if body.topic:
        message_parts.append(body.topic)
    if body.language:
        message_parts.append(body.language)
    message = " ".join(message_parts)

    context = _context(body.user_id, body.session_id)
    response = await programming_agent.start_test(body.session_id, message, context)
    _raise_for_programming_test_failure(response.content, response.success)
    meta = response.metadata or {}
    logger.info(
        "assessment_programming_test_start_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        completed=meta.get("completed", False),
    )
    return ProgrammingTestResponse(
        content=response.content,
        success=response.success,
        metadata=meta,
        completed=meta.get("completed", False),
        test_case_results=[],
    )


@router.post(
    "/programming-test/submit",
    response_model=ProgrammingTestResponse,
    responses={
        400: {"description": "Invalid request or session"},
        404: {"description": "No programming test in progress"},
        408: {"description": "Code execution timed out"},
        503: {"description": "Sandbox unavailable or infrastructure error"},
    },
)
async def programming_test_submit(
    body: ProgrammingTestSubmitRequest,
    programming_agent: "ProgrammingTestAgent | None" = Depends(get_programming_test_agent),
) -> ProgrammingTestResponse:
    """Submit solution code for the current programming test."""
    logger.info(
        "assessment_programming_test_submit_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if programming_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")

    context = _context(body.user_id, body.session_id)
    try:
        response = await programming_agent.submit_code(body.session_id, body.code, context)
    except UnsafeCodeError as e:
        logger.info(
            "assessment_programming_test_submit_unsafe_code",
            session_id=body.session_id or None,
            user_id=body.user_id or None,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except CodeExecutionTimeoutError as e:
        logger.error(
            "assessment_programming_test_submit_timeout",
            session_id=body.session_id or None,
            user_id=body.user_id or None,
        )
        raise HTTPException(status_code=408, detail=str(e)) from e
    except SandboxError as e:
        logger.error(
            "assessment_programming_test_submit_sandbox_error",
            session_id=body.session_id or None,
            user_id=body.user_id or None,
        )
        raise HTTPException(status_code=503, detail=str(e)) from e

    _raise_for_programming_test_failure(response.content, response.success)
    meta = response.metadata or {}
    logger.info(
        "assessment_programming_test_submit_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        completed=meta.get("completed", False),
    )
    return ProgrammingTestResponse(
        content=response.content,
        success=response.success,
        metadata=meta,
        completed=meta.get("completed", False),
        test_case_results=meta.get("test_case_results") or [],
    )


@router.post(
    "/programming-test/submit-job",
    response_model=ProgrammingTestJobResponse,
    responses={
        400: {"description": "Invalid request or session"},
        503: {"description": "Assessment service unavailable"},
    },
)
async def programming_test_submit_job(
    body: ProgrammingTestSubmitRequest,
    programming_agent: "ProgrammingTestAgent | None" = Depends(get_programming_test_agent),
) -> ProgrammingTestJobResponse:
    """Submit solution code as an async job for the current programming test.

    This endpoint creates a job row and enqueues it on the code execution queue,
    returning a job_id for clients to poll.
    """
    logger.info(
        "assessment_programming_test_submit_job_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    if programming_agent is None:
        raise HTTPException(status_code=503, detail="Assessment service unavailable")

    engine = get_engine()
    jobs_repo = JobsRepository(engine)

    payload = {
        "session_id": body.session_id,
        "user_id": body.user_id,
        "code": body.code,
        "intent": "PROGRAMMING_TEST",
    }
    job = await jobs_repo.create_job(
        type="code_execution",
        payload=payload,
        status="PENDING",
        user_id=body.user_id or None,
        conversation_id=None,
    )

    await queues.enqueue(
        queues.code_execution_queue_name(),
        {"job_id": job.id},
    )

    logger.info(
        "assessment_programming_test_submit_job_enqueued",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        job_id=job.id,
    )
    return ProgrammingTestJobResponse(job_id=job.id, status=job.status)


@router.get(
    "/performance/{user_id}",
    response_model=PerformanceSummaryResponse,
    responses={400: {"description": "Invalid user_id"}},
)
async def get_performance(
    user_id: str,
    performance_monitor: "PerformanceMonitorAgent | None" = Depends(get_performance_monitor),
) -> PerformanceSummaryResponse:
    """Get performance summary for a user (avg score, weak/strong topics, alert flag)."""
    logger.info(
        "assessment_performance_summary_requested",
        user_id=user_id,
    )
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required")
    if performance_monitor is None:
        raise HTTPException(status_code=503, detail="Performance service unavailable")
    summary = performance_monitor.get_summary(user_id)
    return PerformanceSummaryResponse(
        avg_score=summary.get("avg_score", 0.0),
        weak_topics=summary.get("weak_topics") or [],
        strong_topics=summary.get("strong_topics") or [],
        alert_flag=summary.get("alert_flag", False),
    )
