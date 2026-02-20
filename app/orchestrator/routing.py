"""Agent selection rules: intent → agent. Delegates to registry."""

from typing import TYPE_CHECKING

from app.orchestrator.registry import AgentRegistry
from app.orchestrator.types import Intent

if TYPE_CHECKING:
    from app.agents.base.base_agent import BaseAgent


def select_agent(registry: AgentRegistry, intent: Intent) -> "BaseAgent | None":
    """
    Select the agent responsible for the given intent.

    Uses registry's intent→agent mapping. Extend here for load balancing
    or fallback rules (e.g. unknown → generalist agent) when needed.
    """
    return registry.select_agent(intent)
