"""Attach request/correlation ID to each request. Propagate to orchestrator and logs."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Set request.state.correlation_id from header or generate new. Add to response headers."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
