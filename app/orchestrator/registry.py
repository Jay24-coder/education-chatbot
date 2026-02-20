"""Agent registry: register and lookup agents by intent/capability."""

from typing import TYPE_CHECKING

from app.orchestrator.types import Intent

if TYPE_CHECKING:
    from app.agents.base.base_agent import BaseAgent


class AgentRegistry:
    """Register agents by intent; lookup by intent for routing."""

    def __init__(self) -> None:
        self._intent_to_agent: dict[Intent, "BaseAgent"] = {}
        self._all_agents: list["BaseAgent"] = []

    def register(self, intent: Intent, agent: "BaseAgent") -> None:
        """Register an agent for the given intent. Overwrites any existing registration."""
        self._intent_to_agent[intent] = agent
        if agent not in self._all_agents:
            self._all_agents.append(agent)

    def register_capabilities(self, agent: "BaseAgent") -> None:
        """Register an agent for all of its declared capabilities (by capability name)."""
        for cap in agent.get_capabilities():
            try:
                intent = Intent(cap)
                self.register(intent, agent)
            except ValueError:
                pass
        if agent not in self._all_agents:
            self._all_agents.append(agent)

    def get_agent(self, intent: Intent) -> "BaseAgent | None":
        """Return the agent registered for the given intent, or None."""
        return self._intent_to_agent.get(intent)

    def select_agent(self, intent: Intent) -> "BaseAgent | None":
        """Alias for get_agent; used by orchestrator routing."""
        return self.get_agent(intent)

    def all_agents(self) -> list["BaseAgent"]:
        """Return all registered agents (for health checks)."""
        return list(self._all_agents)
