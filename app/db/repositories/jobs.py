"""Job persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class JobRecord:
    id: int
    type: str
    status: str
    payload: Any
    user_id: Optional[str]
    conversation_id: Optional[int]
    result: Optional[Any]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class JobsRepository:
    """Repository for jobs lifecycle."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_job(
        self,
        type: str,
        payload: Any,
        status: str = "PENDING",
        user_id: Optional[str] = None,
        conversation_id: Optional[int] = None,
    ) -> JobRecord:
        query = text(
            """
            INSERT INTO jobs (type, status, payload, user_id, conversation_id)
            VALUES (:type, :status, :payload, :user_id, :conversation_id)
            RETURNING id, type, status, payload, user_id, conversation_id,
                      result, error, created_at, started_at, finished_at
            """
        )
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    query,
                    {
                        "type": type,
                        "status": status,
                        "payload": payload,
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                    },
                )
            ).one()

        return JobRecord(
            id=row.id,
            type=row.type,
            status=row.status,
            payload=row.payload,
            user_id=row.user_id,
            conversation_id=row.conversation_id,
            result=row.result,
            error=row.error,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    async def get_job(self, job_id: int) -> Optional[JobRecord]:
        query = text(
            """
            SELECT id, type, status, payload, user_id, conversation_id,
                   result, error, created_at, started_at, finished_at
            FROM jobs
            WHERE id = :job_id
            """
        )
        async with self._engine.connect() as conn:
            result = await conn.execute(query, {"job_id": job_id})
            row = result.one_or_none()

        if row is None:
            return None

        return JobRecord(
            id=row.id,
            type=row.type,
            status=row.status,
            payload=row.payload,
            user_id=row.user_id,
            conversation_id=row.conversation_id,
            result=row.result,
            error=row.error,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    async def update_job_status(
        self,
        job_id: int,
        status: str,
        result: Any = None,
        error: Optional[str] = None,
        finished_at: Optional[datetime] = None,
    ) -> Optional[JobRecord]:
        query = text(
            """
            UPDATE jobs
            SET status = :status,
                result = :result,
                error = :error,
                finished_at = COALESCE(:finished_at, finished_at)
            WHERE id = :job_id
            RETURNING id, type, status, payload, user_id, conversation_id,
                      result, error, created_at, started_at, finished_at
            """
        )
        async with self._engine.begin() as conn:
            result_cursor = await conn.execute(
                query,
                {
                    "job_id": job_id,
                    "status": status,
                    "result": result,
                    "error": error,
                    "finished_at": finished_at,
                },
            )
            row = result_cursor.one_or_none()

        if row is None:
            return None

        return JobRecord(
            id=row.id,
            type=row.type,
            status=row.status,
            payload=row.payload,
            user_id=row.user_id,
            conversation_id=row.conversation_id,
            result=row.result,
            error=row.error,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

