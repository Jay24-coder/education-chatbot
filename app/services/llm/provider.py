"""LLM provider protocol: central interface for LLM completion calls."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM completion with timeout, model, and temperature."""

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_seconds: float | None = None,
    ) -> str:
        """
        Run a completion and return the generated text.

        Args:
            prompt: Input prompt.
            model: Model identifier; None to use provider default.
            temperature: Sampling temperature (0 = deterministic).
            timeout_seconds: Request timeout; None for provider default.

        Returns:
            Generated text.

        Raises:
            LLMProviderError: On API or provider errors.
            TimeoutError: On timeout (app.utils.errors.TimeoutError).
        """
        ...
