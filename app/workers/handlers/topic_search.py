"""Handler for topic_search jobs."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.db.repositories.jobs import JobsRepository
from app.infra.redis import cache as redis_cache

logger = logging.getLogger(__name__)


async def handle_topic_search_job(job_id: int, payload: Dict[str, Any], jobs_repo: JobsRepository) -> None:
    """Process a single topic_search job.

    For now this marks the job as FAILED with a clear error message, so that
    callers see an explicit signal that topic_search handling is not yet wired.
    """
    error_message = "topic_search job handler not implemented yet"
    updated = await jobs_repo.update_job_status(
        job_id=job_id,
        status="FAILED",
        result=None,
        error=error_message,
    )

    if updated is not None:
        cache_payload = {
            "job_id": updated.id,
            "status": updated.status,
            "result": updated.result,
            "error": updated.error,
        }
        await redis_cache.set_job_status(str(updated.id), cache_payload, ttl_sec=300)
        logger.warning("topic_search job %s marked as FAILED (not implemented)", job_id)

