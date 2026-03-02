"""Chat endpoint: accept user message and session_id, call orchestrator, return response."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_orchestrator
from app.api.schemas.v1.chat import ChatRequest, ChatResponse
from app.observability.logging import get_logger
from app.orchestrator.types import UserRequest
from app.utils.errors import OrchestratorError, ValidationError

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Orchestrator error"},
    },
)
async def chat(
    body: ChatRequest,
    request: Request,
    orchestrator=Depends(get_orchestrator),
) -> ChatResponse:
    """Accept user message, required user_id, and optional session_id; return assistant response."""
    correlation_id = getattr(request.state, "correlation_id", None)
    message = body.message or ""
    session_id = body.session_id or None
    user_id = body.user_id

    logger.info(
        "chat_request_received",
        correlation_id=correlation_id,
        session_id=session_id,
        user_id=user_id,
        message_length=len(message),
    )

    user_request = UserRequest(
        message=message,
        session_id=session_id,
        correlation_id=correlation_id,
        user_id=user_id,
    )
    try:
        response = await orchestrator.route_request(user_request)
    except ValidationError as e:
        logger.info(
            "chat_request_validation_error",
            correlation_id=correlation_id,
            session_id=session_id,
            user_id=user_id,
            error_code=e.code,
        )
        return JSONResponse(
            status_code=400,
            content={"detail": e.message, "code": e.code},
        )
    except OrchestratorError as e:
        logger.error(
            "chat_request_orchestrator_error",
            correlation_id=correlation_id,
            session_id=session_id,
            user_id=user_id,
            error_code=e.code,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": e.message, "code": e.code},
        )

    logger.info(
        "chat_response_sent",
        correlation_id=correlation_id,
        session_id=session_id,
        user_id=user_id,
        success=response.success,
        response_length=len(response.content or ""),
    )

    return ChatResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata,
        correlation_id=response.metadata.get("correlation_id") or correlation_id,
    )
