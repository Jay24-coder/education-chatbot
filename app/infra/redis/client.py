"""Redis client and pool management.

This module centralizes construction of Redis clients for:
- cache usage
- queue usage
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.config import db_redis


_cache_client: Optional[aioredis.Redis] = None
_queue_client: Optional[aioredis.Redis] = None


def get_cache_client() -> aioredis.Redis:
    """Return a process-wide Redis client for cache operations."""
    global _cache_client

    if _cache_client is None:
        url = db_redis.build_redis_cache_url()
        pool_opts = db_redis.redis_pool_options()
        _cache_client = aioredis.from_url(url, **pool_opts, decode_responses=True)

    return _cache_client


def get_queue_client() -> aioredis.Redis:
    """Return a process-wide Redis client for queue operations."""
    global _queue_client

    if _queue_client is None:
        url = db_redis.build_redis_queues_url()
        pool_opts = db_redis.redis_pool_options()
        _queue_client = aioredis.from_url(url, **pool_opts, decode_responses=True)

    return _queue_client


async def close_clients() -> None:
    """Close Redis clients (for shutdown or tests)."""
    global _cache_client, _queue_client

    if _cache_client is not None:
        await _cache_client.close()
        _cache_client = None

    if _queue_client is not None:
        await _queue_client.close()
        _queue_client = None

