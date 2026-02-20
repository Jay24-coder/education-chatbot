"""Basic rate limiting and per-user quotas using app/config/limits.py."""

import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.limits import rate_limit_config


def _client_key(request: Request) -> str:
    """Identify client for rate limiting: X-User-ID header or client host."""
    user_id = request.headers.get("X-User-ID", "").strip()
    if user_id:
        return f"user:{user_id}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory per-minute rate limit per client key. Uses rate_limit_config."""

    def __init__(self, app, requests_per_minute: int | None = None):
        super().__init__(app)
        self._limit = requests_per_minute or rate_limit_config.requests_per_minute
        self._timestamps: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        key = _client_key(request)
        now = time.monotonic()
        window_start = now - 60.0  # 1 minute window
        async with self._lock:
            if key not in self._timestamps:
                self._timestamps[key] = []
            times = self._timestamps[key]
            times[:] = [t for t in times if t > window_start]
            if len(times) >= self._limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "code": "RATE_LIMIT_EXCEEDED",
                    },
                )
            times.append(now)
        return await call_next(request)
