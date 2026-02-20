"""Typed error classes for the application."""


class EducationError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


class AgentError(EducationError):
    """Error raised by agents during request processing."""

    pass


class OrchestratorError(EducationError):
    """Error raised by orchestrator during routing or coordination."""

    pass


class LLMProviderError(EducationError):
    """Error raised by LLM provider during API calls."""

    pass


class ContextStoreError(EducationError):
    """Error raised by context store during state operations."""

    pass


class ValidationError(EducationError):
    """Error raised during request validation."""

    pass


class RateLimitError(EducationError):
    """Error raised when rate limit is exceeded."""

    pass


class TimeoutError(EducationError):
    """Error raised when an operation times out."""

    pass
