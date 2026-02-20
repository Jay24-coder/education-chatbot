"""Base agent protocol and implementation for all agents."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from app.orchestrator.types import AgentRequest, AgentResponse


@runtime_checkable
class BaseAgent(Protocol):
    """Protocol for agents: identity, capabilities, request processing, and health."""

    @property
    def agent_id(self) -> str:
        """Unique identifier for this agent."""
        ...

    def get_capabilities(self) -> list[str]:
        """Return list of capability/intent identifiers this agent handles."""
        ...

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process a request and return a response."""
        ...

    def health_check(self) -> bool:
        """Return True if the agent is healthy and ready to process requests."""
        ...


class AbstractBaseAgent(ABC):
    """Abstract base class implementing BaseAgent protocol with common fields."""

    def __init__(self, agent_id: str, capabilities: list[str]) -> None:
        self._agent_id = agent_id
        self._capabilities = list(capabilities)

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def get_capabilities(self) -> list[str]:
        return list(self._capabilities)

    @abstractmethod
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process the request and return a response."""
        ...

    def health_check(self) -> bool:
        """Override in subclasses for dependency checks; default is True."""
        return True
