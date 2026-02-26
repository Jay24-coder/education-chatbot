"""Worker runner: initialize Postgres and Redis, then consume queues."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.config.settings import settings
from app.db.pool import get_engine
from app.db.repositories.jobs import JobsRepository
from app.infra.redis import queues
from app.infra.redis.client import get_queue_client
from app.workers.handlers.code_execution import handle_code_execution_job
from app.workers.handlers.topic_search import handle_topic_search_job

logger = logging.getLogger(__name__)


async def _code_execution_worker_loop(worker_id: int) -> None:
    engine = get_engine()
    jobs_repo = JobsRepository(engine)

    while True:
        message = await queues.dequeue(queues.code_execution_queue_name(), timeout_sec=5)
        if message is None:
            continue

        job_id = int(message.get("job_id"))
        payload: Dict[str, Any] = {}
        job = await jobs_repo.get_job(job_id)
        if job is not None:
            # Payload is stored in the jobs table; prefer that as source of truth.
            payload = job.payload or {}

        logger.info("Worker %s processing code_execution job %s", worker_id, job_id)
        await handle_code_execution_job(job_id, payload, jobs_repo)


async def _topic_search_worker_loop(worker_id: int) -> None:
    engine = get_engine()
    jobs_repo = JobsRepository(engine)

    while True:
        message = await queues.dequeue(queues.topic_search_queue_name(), timeout_sec=5)
        if message is None:
            continue

        job_id = int(message.get("job_id"))
        payload: Dict[str, Any] = {}
        job = await jobs_repo.get_job(job_id)
        if job is not None:
            payload = job.payload or {}

        logger.info("Worker %s processing topic_search job %s", worker_id, job_id)
        await handle_topic_search_job(job_id, payload, jobs_repo)


async def main() -> None:
    """Entry point for workers: start consumer loops."""
    # Touch the Redis queue client early so connection pool is ready.
    get_queue_client()

    concurrency = max(settings.worker_concurrency, 1)

    tasks = []
    for i in range(concurrency):
        tasks.append(asyncio.create_task(_code_execution_worker_loop(worker_id=i)))
        tasks.append(asyncio.create_task(_topic_search_worker_loop(worker_id=i)))

    logger.info(
        "Started workers with concurrency=%s (code_execution + topic_search)",
        concurrency,
    )
    await asyncio.gather(*tasks)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

