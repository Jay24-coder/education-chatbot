"""FastAPI app factory: routers and middleware."""

from fastapi import FastAPI

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.logging_mw import LoggingMiddleware
from app.api.middleware.ratelimit import RateLimitMiddleware
from app.api.routers import chat, health

# OpenAPI tags for /docs grouping
OPENAPI_TAGS = [
    {"name": "chat", "description": "Student-facing chat: send a message, get assistant response. Uses session_id for conversation context."},
    {"name": "health", "description": "Liveness and readiness probes for deployment; optional agent health check."},
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

    return app


app = create_app()
