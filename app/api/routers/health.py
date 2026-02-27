"""Health endpoints: liveness and readiness (and optional agent health)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.api.deps import get_orchestrator
from app.db.pool import get_engine
from app.infra.redis.client import get_cache_client
from app.observability.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/live")
def liveness() -> dict[str, str]:
    """Liveness probe: process is running (does not depend on DB/Redis)."""
    logger.info("health_liveness_check")
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe: app is ready to accept traffic (Postgres + Redis healthy)."""

    # Check Postgres
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("health_readiness_postgres_failed")
        raise HTTPException(status_code=503, detail=f"Postgres readiness check failed: {exc}") from exc

    # Check Redis (cache client)
    try:
        client = get_cache_client()
        pong = await client.ping()
        if not pong:
            raise RuntimeError("Redis PING returned falsy response")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("health_readiness_redis_failed")
        raise HTTPException(status_code=503, detail=f"Redis readiness check failed: {exc}") from exc

    logger.info("health_readiness_ok")
    return {"status": "ready"}


@router.get("/ready/agents")
def agents_readiness(orch=Depends(get_orchestrator)) -> dict[str, str | list[str]]:
    """Optional: readiness including agent health. Returns status and list of unhealthy agent IDs if any."""
    unhealthy = []
    for agent in orch.all_agents():
        if not agent.health_check():
            unhealthy.append(agent.agent_id)
    if unhealthy:
        return {"status": "degraded", "unhealthy_agents": unhealthy}
    return {"status": "ready", "unhealthy_agents": []}
