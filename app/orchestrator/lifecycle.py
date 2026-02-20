"""Agent lifecycle: initialization, health checks, and graceful shutdown."""

from typing import Callable, TYPE_CHECKING

from app.observability.logging import get_logger

if TYPE_CHECKING:
    from app.agents.base.base_agent import BaseAgent

logger = get_logger(__name__)

# Global shutdown hooks; call from API on shutdown
_shutdown_hooks: list[Callable[[], None] | Callable[[], object]] = []


def register_shutdown_hook(hook: Callable[[], None] | Callable[[], object]) -> None:
    """Register a callable to be run on application shutdown (e.g. close connections)."""
    _shutdown_hooks.append(hook)


def run_shutdown_hooks() -> None:
    """Run all registered shutdown hooks. Safe to call multiple times."""
    while _shutdown_hooks:
        hook = _shutdown_hooks.pop()
        try:
            hook()
        except Exception as e:
            logger.exception(
                "shutdown_hook_failed",
                hook=getattr(hook, "__name__", repr(hook)),
                error=str(e),
            )


def check_agents_health(agents: list["BaseAgent"]) -> dict[str, bool]:
    """
    Run health_check() on each agent. Returns a dict of agent_id -> healthy.
    Used by API readiness probe.
    """
    result: dict[str, bool] = {}
    for agent in agents:
        aid = getattr(agent, "agent_id", str(id(agent)))
        try:
            result[aid] = bool(agent.health_check())
        except Exception as e:
            logger.warning("agent_health_check_failed", agent_id=aid, error=str(e))
            result[aid] = False
    return result


def all_agents_healthy(agents: list["BaseAgent"]) -> bool:
    """Return True if every agent's health_check() returns True."""
    return all(check_agents_health(agents).values()) if agents else True
