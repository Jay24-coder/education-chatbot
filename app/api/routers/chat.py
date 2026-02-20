"""Chat endpoint: accept user message and session_id, call orchestrator, return response."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_orchestrator
from app.api.schemas.v1.chat import ChatRequest, ChatResponse
from app.orchestrator.types import UserRequest
from app.utils.errors import OrchestratorError, ValidationError

router = APIRouter(tags=["chat"])


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
    """Accept user message and optional session_id; return assistant response."""
    correlation_id = getattr(request.state, "correlation_id", None)
    user_request = UserRequest(
        message=body.message,
        session_id=body.session_id,
        correlation_id=correlation_id,
        user_id=body.user_id,
    )
    try:
        response = await orchestrator.route_request(user_request)
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"detail": e.message, "code": e.code},
        )
    except OrchestratorError as e:
        return JSONResponse(
            status_code=500,
            content={"detail": e.message, "code": e.code},
        )
    return ChatResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata,
        correlation_id=response.metadata.get("correlation_id") or correlation_id,
    )
