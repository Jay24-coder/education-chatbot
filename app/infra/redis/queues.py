"""Simple Redis-backed queues."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.config.settings import settings
from .client import get_queue_client


async def enqueue(queue_name: str, payload: Dict[str, Any]) -> None:
    """Push a JSON-serializable payload onto a Redis list."""
    client = get_queue_client()
    key = _queue_key(queue_name)
    await client.rpush(key, json.dumps(payload))


async def dequeue(queue_name: str, timeout_sec: int = 5) -> Optional[Dict[str, Any]]:
    """Pop a payload from a Redis list, blocking up to timeout_sec."""
    client = get_queue_client()
    key = _queue_key(queue_name)

    result = await client.blpop(key, timeout=timeout_sec)
    if result is None:
        return None

    _, raw = result
    return json.loads(raw)


def _queue_key(queue_name: str) -> str:
    # Namespaced by ENV to keep environments isolated
    return f"{settings.env}:queue:{queue_name}"


def code_execution_queue_name() -> str:
    return settings.queue_code_execution


def topic_search_queue_name() -> str:
    return settings.queue_topic_search

