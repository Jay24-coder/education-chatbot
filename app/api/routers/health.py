"""Health endpoints: liveness and readiness (and optional agent health)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_orchestrator

router = APIRouter(tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    """Liveness probe: process is running."""
    return {"status": "ok"}


@router.get("/ready")
def readiness() -> dict[str, str]:
    """Readiness probe: app is ready to accept traffic."""
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
