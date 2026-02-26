"""Cache helpers built on top of Redis."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.config.settings import settings
from .client import get_cache_client


def _conversation_key(conversation_id: str) -> str:
    return f"{settings.env}:chat:conversation:{conversation_id}"


def _job_status_key(job_id: str) -> str:
    return f"{settings.env}:job:{job_id}:status"


async def get_cached_conversation(conversation_id: str) -> Optional[Any]:
    client = get_cache_client()
    raw = await client.get(_conversation_key(conversation_id))
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_conversation(conversation_id: str, payload: Any, ttl_sec: int) -> None:
    client = get_cache_client()
    await client.setex(_conversation_key(conversation_id), ttl_sec, json.dumps(payload))


async def invalidate_conversation(conversation_id: str) -> None:
    client = get_cache_client()
    await client.delete(_conversation_key(conversation_id))


async def get_job_status(job_id: str) -> Optional[Any]:
    client = get_cache_client()
    raw = await client.get(_job_status_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)


async def set_job_status(job_id: str, payload: Any, ttl_sec: int) -> None:
    client = get_cache_client()
    await client.setex(_job_status_key(job_id), ttl_sec, json.dumps(payload))

