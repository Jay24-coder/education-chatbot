"""FastAPI app factory: routers and middleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.logging_mw import LoggingMiddleware
from app.api.middleware.ratelimit import RateLimitMiddleware
from app.api.routers import assessment, chat, health
from app.utils.errors import (
    InvalidSessionError,
    QuizNotFoundError,
    TestAlreadyCompleteError,
)

# OpenAPI tags for /docs grouping
OPENAPI_TAGS = [
    {"name": "chat", "description": "Student-facing chat: send a message, get assistant response. Uses session_id for conversation context."},
    {"name": "health", "description": "Liveness and readiness probes for deployment; optional agent health check."},
    {"name": "assessment", "description": "Quiz and concept test start/answer, performance summary by user."},
]

# Order: last added is innermost (runs first). We want Correlation -> RateLimit -> Logging (outer).
def create_app() -> FastAPI:
    app = FastAPI(
        title="Education Chatbot API",
        description="Phase 1: chat and health endpoints. OpenAPI at /openapi.json, interactive docs at /docs.",
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(assessment.router, prefix="/api/v1")

    # Assessment error handling: map to HTTP status codes
    @app.exception_handler(InvalidSessionError)
    def invalid_session_handler(request, exc: InvalidSessionError):
        return JSONResponse(status_code=400, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(QuizNotFoundError)
    def quiz_not_found_handler(request, exc: QuizNotFoundError):
        return JSONResponse(status_code=404, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(TestAlreadyCompleteError)
    def test_already_complete_handler(request, exc: TestAlreadyCompleteError):
        return JSONResponse(status_code=409, content={"detail": exc.message, "code": exc.code})

    return app


app = create_app()
