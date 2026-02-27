"""OpenAI-backed LLM provider with timeout and retry."""

from time import perf_counter

from openai import AsyncOpenAI

from app.config.resiliency import resiliency_config
from app.config.settings import settings
from app.observability.logging import get_logger
from app.orchestrator.policies import with_retry, with_timeout
from app.utils.errors import LLMProviderError


logger = get_logger(__name__)


class OpenAIProvider:
    """LLMProvider implementation using OpenAI API with timeout and retry."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key or settings.llm_api_key)
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
            provider="openai",
            model=model_id,
            prompt_length=len(prompt_text),
        )
        start = perf_counter()

        async def _request() -> str:
            response = await self._client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            if not response.choices:
                raise LLMProviderError("Empty completion response", code="EMPTY_RESPONSE")
            content = response.choices[0].message.content
            return content or ""

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
                provider="openai",
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
                provider="openai",
                model=model_id,
                duration_ms=round(duration_ms, 2),
                error=str(e),
            )
            raise LLMProviderError(str(e), code="LLM_ERROR") from e
