"""Postgres async engine / pool helpers.

This module owns the process-wide Postgres connection pool. It builds the
engine using settings from `app/config/db_redis.py` (Postgres section).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

from app.config import db_redis


_engine: Optional[AsyncEngine] = None


def get_engine() -> AsyncEngine:
    """Return a process-wide async engine, creating it lazily if needed."""
    global _engine

    if _engine is None:
        url = db_redis.build_postgres_url()
        pool_opts = db_redis.postgres_pool_options()

        # SQLAlchemy-style config dict; can be adjusted as needed later.
        config = {
            "url": url,
            "echo": False,
            "pool_pre_ping": True,
            "pool_size": pool_opts["max_size"],
            "max_overflow": 0,
        }
        _engine = async_engine_from_config(config, prefix="")

    return _engine


async def dispose_engine() -> None:
    """Dispose of the global engine (for application shutdown or tests)."""
    global _engine

    if _engine is not None:
        await _engine.dispose()
        _engine = None

