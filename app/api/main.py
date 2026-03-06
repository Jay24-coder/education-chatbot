"""FastAPI app factory: routers and middleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.logging_mw import LoggingMiddleware
from app.api.middleware.ratelimit import RateLimitMiddleware
from app.api.routers import (
    assessment,
    chat,
    conversations,
    health,
    problem_solving,
    visualization,
)
from app.config.settings import settings
from app.observability.logging import get_logger
from app.utils.errors import (
    AgentError,
    ContextStoreError,
    EducationError,
    InvalidSessionError,
    LLMProviderError,
    OrchestratorError,
    QuizNotFoundError,
    RateLimitError,
    TestAlreadyCompleteError,
    TimeoutError,
    ValidationError,
)

logger = get_logger(__name__)

# OpenAPI tags for /docs grouping
OPENAPI_TAGS = [
    {"name": "chat", "description": "Student-facing chat: send a message, get assistant response. Uses session_id for conversation context."},
    {"name": "conversations", "description": "List conversations and retrieve message history for a user."},
    {"name": "health", "description": "Liveness and readiness probes for deployment; optional agent health check."},
    {"name": "assessment", "description": "Quiz and concept test start/answer, performance summary by user."},
    {"name": "visualization", "description": "Generate diagrams (Mermaid) or chart specs from a description."},
    {"name": "problem_solving", "description": "Start a problem-solving session with an image; respond with text. Dedicated router for file uploads and large payloads."},
]

# Order: last added is innermost (runs first). We want Correlation -> RateLimit -> Logging (outer).
def create_app() -> FastAPI:
    app = FastAPI(
        title="Education Chatbot API",
        description="Phase 1: chat and health endpoints. OpenAPI at /openapi.json, interactive docs at /docs.",
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
    )

    @app.on_event("startup")
    async def log_llm_startup_config() -> None:
        provider = (getattr(settings, "llm_provider", None) or "openai").strip().lower()
        model_id = getattr(settings, "model_id", "") or ""

        enabled = False
        if provider in {"openai"}:
            enabled = bool(getattr(settings, "llm_api_key", "").strip())
        elif provider in {"google", "gemini"}:
            enabled = bool((getattr(settings, "google_api_key", "") or getattr(settings, "llm_api_key", "")).strip())

        logger.info(
            "llm_startup_config",
            llm_provider=provider,
            model=model_id,
            enabled=enabled,
        )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(assessment.router, prefix="/api/v1")
    app.include_router(visualization.router, prefix="/api/v1")
    app.include_router(problem_solving.router, prefix="/api/v1")

    # Assessment / domain error handling: map to HTTP status codes
    @app.exception_handler(InvalidSessionError)
    def invalid_session_handler(request, exc: InvalidSessionError):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.info(
            "invalid_session_error",
            path=request.url.path,
            method=request.method,
            status_code=400,
            correlation_id=correlation_id,
            error_code=exc.code,
        )
        return JSONResponse(status_code=400, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(QuizNotFoundError)
    def quiz_not_found_handler(request, exc: QuizNotFoundError):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.info(
            "quiz_not_found_error",
            path=request.url.path,
            method=request.method,
            status_code=404,
            correlation_id=correlation_id,
            error_code=exc.code,
        )
        return JSONResponse(status_code=404, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(TestAlreadyCompleteError)
    def test_already_complete_handler(request, exc: TestAlreadyCompleteError):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.info(
            "test_already_complete_error",
            path=request.url.path,
            method=request.method,
            status_code=409,
            correlation_id=correlation_id,
            error_code=exc.code,
        )
        return JSONResponse(status_code=409, content={"detail": exc.message, "code": exc.code})

    # Generic application error handling for orchestrator/agents/infra
    @app.exception_handler(ValidationError)
    def validation_error_handler(request, exc: ValidationError):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.info(
            "validation_error",
            path=request.url.path,
            method=request.method,
            status_code=400,
            correlation_id=correlation_id,
            error_code=exc.code,
        )
        return JSONResponse(status_code=400, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(RateLimitError)
    def rate_limit_error_handler(request, exc: RateLimitError):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.info(
            "rate_limit_error",
            path=request.url.path,
            method=request.method,
            status_code=429,
            correlation_id=correlation_id,
            error_code=exc.code,
        )
        return JSONResponse(status_code=429, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(TimeoutError)
    def timeout_error_handler(request, exc: TimeoutError):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.error(
            "timeout_error",
            path=request.url.path,
            method=request.method,
            status_code=504,
            correlation_id=correlation_id,
            error_code=exc.code,
        )
        return JSONResponse(status_code=504, content={"detail": exc.message, "code": exc.code})

    def internal_app_error_handler(request, exc: EducationError):
        # Avoid logging sensitive payloads; rely on structured fields only.
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.error(
            "application_error",
            path=request.url.path,
            method=request.method,
            status_code=500,
            correlation_id=correlation_id,
            error_type=exc.__class__.__name__,
            error_code=getattr(exc, "code", None),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": getattr(exc, "message", "Internal application error"), "code": getattr(exc, "code", None)},
        )

    for exc_cls in (LLMProviderError, ContextStoreError, OrchestratorError, AgentError):
        app.add_exception_handler(exc_cls, internal_app_error_handler)

    return app


app = create_app()
