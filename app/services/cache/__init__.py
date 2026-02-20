"""Cache layer for syllabus/policy lookups. TTL documented per implementation."""

from app.services.cache.memory_cache import InMemoryCache

__all__ = ["InMemoryCache"]
