"""Helpers to construct database and Redis URLs and pool options from settings.

This module is the single source of truth for how we build connection URLs
and pool configuration for Postgres and Redis.
"""

from __future__ import annotations

from typing import Dict

from .settings import settings


def build_postgres_url() -> str:
    """Build an async Postgres URL from granular settings.

    We intentionally use the asyncpg driver scheme so this URL can be used
    directly with SQLAlchemy async engine or asyncpg pools.
    """

    user = settings.postgres_user
    password = settings.postgres_password
    host = settings.postgres_host
    port = settings.postgres_port
    db = settings.postgres_db

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def postgres_pool_options() -> Dict[str, int]:
    """Return pool size configuration for Postgres connections."""
    return {
        "min_size": settings.db_pool_min_size,
        "max_size": settings.db_pool_max_size,
    }


def build_redis_cache_url() -> str:
    """Build Redis URL for cache usage."""
    return _build_redis_url(db=settings.redis_db_cache)


def build_redis_queues_url() -> str:
    """Build Redis URL for queue usage."""
    return _build_redis_url(db=settings.redis_db_queues)


def redis_pool_options() -> Dict[str, int]:
    """Return pool size configuration shared by Redis clients."""
    return {
        "max_connections": settings.redis_pool_max_size,
    }


def _build_redis_url(db: int) -> str:
    password = settings.redis_password
    host = settings.redis_host
    port = settings.redis_port

    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"

