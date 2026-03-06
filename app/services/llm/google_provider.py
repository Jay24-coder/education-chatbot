"""Google (Gemini API) backed LLM provider with timeout and retry."""

from __future__ import annotations

from time import perf_counter

from google import genai

from app.config.resiliency import resiliency_config
from app.config.settings import settings
from app.observability.logging import get_logger
from app.orchestrator.policies import with_retry, with_timeout
from app.utils.errors import LLMProviderError


logger = get_logger(__name__)


class GoogleProvider:
    """LLMProvider implementation using the Gemini API (google-genai)."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        key = api_key or settings.google_api_key or settings.llm_api_key
        self._client = genai.Client(api_key=key)
        self._default_model = default_model or settings.model_id
        self._timeout = timeout_seconds or resiliency_config.timeouts.llm_request_timeout

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_seconds: float | None = None,
    ) -> str:
        model_id = model or self._default_model
        timeout = timeout_seconds if timeout_seconds is not None else self._timeout

        prompt_text = prompt or ""
        logger.info(
            "llm_call_start",
            provider="google",
            model=model_id,
            prompt_length=len(prompt_text),
        )
        start = perf_counter()

        async def _request() -> str:
            # google-genai supports async via client.aio.*
            response = await self._client.aio.models.generate_content(
                model=model_id,
                contents=prompt_text,
                config={"temperature": temperature},
            )

            # Prefer response.text when present; fall back to candidates structure.
            text = getattr(response, "text", None)
            if isinstance(text, str):
                return text

            candidates = getattr(response, "candidates", None) or []
            if not candidates:
                raise LLMProviderError("Empty completion response", code="EMPTY_RESPONSE")

            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) or []
            if not parts:
                raise LLMProviderError("Empty completion response", code="EMPTY_RESPONSE")

            part_text = getattr(parts[0], "text", None)
            return part_text or ""

        async def _call() -> str:
            return await with_timeout(
                _request(),
                timeout_seconds=timeout,
                timeout_message=f"LLM request timed out after {timeout}s",
            )

        try:
            result = await with_retry(
                _call,
                retry_on=(LLMProviderError, Exception),
            )
            duration_ms = (perf_counter() - start) * 1000
            logger.info(
                "llm_call_done",
                provider="google",
                model=model_id,
                duration_ms=round(duration_ms, 2),
                completion_length=len(result or ""),
            )
            return result
        except LLMProviderError:
            raise
        except Exception as e:
            duration_ms = (perf_counter() - start) * 1000
            logger.error(
                "llm_call_error",
                provider="google",
                model=model_id,
                duration_ms=round(duration_ms, 2),
                error=str(e),
            )
            raise LLMProviderError(str(e), code="LLM_ERROR") from e

