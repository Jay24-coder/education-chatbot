"""Handler for code_execution jobs."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.agents.shared_tools.code_execution import (
    CodeExecutionTimeoutError,
    SandboxError,
    UnsafeCodeError,
    execute_in_docker,
)
from app.db.repositories.jobs import JobsRepository
from app.infra.redis import cache as redis_cache

logger = logging.getLogger(__name__)


async def handle_code_execution_job(job_id: int, payload: Dict[str, Any], jobs_repo: JobsRepository) -> None:
    """Process a single code_execution job."""
    code = payload.get("code") or ""
    language = (payload.get("language") or "python").lower()
    user_id = payload.get("user_id")

    try:
        result = await execute_in_docker(code=code, language=language, timeout_seconds=10.0)
        status = "SUCCESS" if result.all_passed else "FAILED"
        job_result = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "all_passed": result.all_passed,
            "test_results": [tr.model_dump() for tr in result.test_results],
        }
        error_message = result.error
    except UnsafeCodeError as e:
        status = "FAILED"
        job_result = None
        error_message = str(e)
    except CodeExecutionTimeoutError as e:
        status = "FAILED"
        job_result = None
        error_message = str(e)
    except SandboxError as e:
        status = "FAILED"
        job_result = None
        error_message = str(e)
    except Exception as e:  # pragma: no cover - defensive
        status = "FAILED"
        job_result = None
        error_message = f"Unexpected error while executing job {job_id}: {e}"
        logger.exception("Unexpected error while handling code_execution job %s", job_id)

    # Persist final job state
    updated = await jobs_repo.update_job_status(
        job_id=job_id,
        status=status,
        result=job_result,
        error=error_message,
    )

    # Optionally update Redis job-status cache for fast polling
    if updated is not None:
        cache_payload = {
            "job_id": updated.id,
            "status": updated.status,
            "result": updated.result,
            "error": updated.error,
            "user_id": user_id,
        }
        await redis_cache.set_job_status(str(updated.id), cache_payload, ttl_sec=300)

