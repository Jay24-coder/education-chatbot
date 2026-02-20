"""Utilities for generating correlation IDs and idempotency keys."""

import secrets
import uuid
from datetime import datetime, timezone


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for request tracing.

    Returns:
        A UUID4 string suitable for correlation tracking
    """
    return str(uuid.uuid4())


def generate_idempotency_key(prefix: str = "idempotency") -> str:
    """
    Generate an idempotency key for deduplicating requests.

    Args:
        prefix: Optional prefix for the key

    Returns:
        A unique idempotency key string
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    random_part = secrets.token_urlsafe(16)
    return f"{prefix}:{timestamp}:{random_part}"


def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Returns:
        A UUID4 string suitable for request identification
    """
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """
    Generate a unique session ID for user sessions.

    Returns:
        A UUID4 string suitable for session tracking
    """
    return str(uuid.uuid4())
