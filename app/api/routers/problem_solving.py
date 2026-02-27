"""Problem-solving API: start with image (multipart or JSON), respond with text. Uses agent directly."""

import base64
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_problem_solving_agent
from app.api.schemas.v1.problem_solving import (
    ProblemSolvingRespondRequest,
    ProblemSolvingRespondResponse,
    ProblemSolvingStartResponse,
)
from app.observability.logging import get_logger
from app.orchestrator.types import AgentRequest, Intent

if TYPE_CHECKING:
    from app.agents.specialized.problem_solving_agent import ProblemSolvingAgent

router = APIRouter(prefix="/problem-solving", tags=["problem_solving"])
logger = get_logger(__name__)


def _context(user_id: str | None, session_id: str) -> dict:
    out: dict = {}
    if user_id:
        out["user_id"] = user_id
    return out


@router.post(
    "/start",
    response_model=ProblemSolvingStartResponse,
    responses={
        400: {"description": "Invalid request or missing image"},
        503: {"description": "Problem-solving service unavailable"},
    },
)
async def problem_solving_start(
    request: Request,
    problem_solving_agent: "ProblemSolvingAgent | None" = Depends(get_problem_solving_agent),
) -> ProblemSolvingStartResponse:
    """
    Start a problem-solving session with an image (multipart or JSON).
    Multipart: form fields session_id, user_id (optional), message (optional); file field 'image'.
    JSON: session_id, user_id (optional), image_base64, message (optional).
    """
    logger.info(
        "problem_solving_start_received",
    )
    if problem_solving_agent is None:
        raise HTTPException(status_code=503, detail="Problem-solving service unavailable")

    correlation_id = getattr(request.state, "correlation_id", None)
    session_id = ""
    user_id: str | None = None
    message = "start"
    image_bytes: bytes | None = None

    content_type = request.headers.get("content-type") or ""
    if "multipart/form-data" in content_type:
        form = await request.form()
        session_id = (form.get("session_id") or "").strip()
        raw_user_id = form.get("user_id")
        user_id = str(raw_user_id).strip() if raw_user_id is not None else None
        if user_id == "":
            user_id = None
        msg = form.get("message")
        message = (str(msg).strip() or "start") if msg is not None else "start"
        file = form.get("image")
        if file is None or not hasattr(file, "read"):
            raise HTTPException(status_code=400, detail="image file required for multipart upload")
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="image file is empty")
    else:
        body = await request.json()
        session_id = (body.get("session_id") or "").strip()
        user_id = body.get("user_id")
        if user_id is not None and not isinstance(user_id, str):
            user_id = None
        if user_id is not None:
            user_id = user_id.strip() or None
        msg = body.get("message")
        message = (str(msg).strip() or "start") if msg is not None else "start"
        b64 = body.get("image_base64")
        if not b64:
            raise HTTPException(status_code=400, detail="image_base64 required for JSON upload")
        try:
            image_bytes = base64.b64decode(b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image_base64: {e}") from e
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Decoded image is empty")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    context = _context(user_id, session_id)
    context["image_bytes"] = image_bytes
    agent_request = AgentRequest(
        message=message,
        session_id=session_id,
        correlation_id=correlation_id,
        intent=Intent.PROBLEM_SOLVING,
        context=context,
    )
    response = await problem_solving_agent.process_request(agent_request)
    logger.info(
        "problem_solving_start_done",
        session_id=session_id or None,
        user_id=user_id or None,
        success=response.success,
    )
    return ProblemSolvingStartResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata or {},
    )


@router.post(
    "/respond",
    response_model=ProblemSolvingRespondResponse,
    responses={
        400: {"description": "Invalid request or session"},
        503: {"description": "Problem-solving service unavailable"},
    },
)
async def problem_solving_respond(
    body: ProblemSolvingRespondRequest,
    request: Request,
    problem_solving_agent: "ProblemSolvingAgent | None" = Depends(get_problem_solving_agent),
) -> ProblemSolvingRespondResponse:
    """Submit a text answer in an existing problem-solving session."""
    if problem_solving_agent is None:
        raise HTTPException(status_code=503, detail="Problem-solving service unavailable")
    if not body.answer or not body.answer.strip():
        raise HTTPException(status_code=400, detail="answer is required")

    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        "problem_solving_respond_received",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
    )
    context = _context(body.user_id, body.session_id)
    agent_request = AgentRequest(
        message=body.answer.strip(),
        session_id=body.session_id,
        correlation_id=correlation_id,
        intent=Intent.PROBLEM_SOLVING,
        context=context,
    )
    response = await problem_solving_agent.process_request(agent_request)
    logger.info(
        "problem_solving_respond_done",
        session_id=body.session_id or None,
        user_id=body.user_id or None,
        success=response.success,
    )
    return ProblemSolvingRespondResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata or {},
    )
