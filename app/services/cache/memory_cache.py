"""In-memory cache with TTL for syllabus/policy lookups. Per Phase 1.5 caching."""

import time
from typing import Any

# Default TTL in seconds when not specified. Document for callers.
DEFAULT_TTL_SECONDS = 300  # 5 minutes


class InMemoryCache:
    """
    In-memory key-value cache with per-entry TTL.
    TTL: entries expire after ttl_seconds (default DEFAULT_TTL_SECONDS).
    Use for syllabus/policy lookups to avoid repeated DB or KB access.
    """

    def __init__(self, default_ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry_time)

    def get(self, key: str) -> Any | None:
        """Return value if key exists and has not expired, else None."""
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.monotonic() >= expiry:
            del self._store[key]
            return None
        return value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: float | None = None,
    ) -> None:
        """Set key to value. TTL: expiry in seconds; default DEFAULT_TTL_SECONDS."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        """Remove key from cache."""
        self._store.pop(key, None)
