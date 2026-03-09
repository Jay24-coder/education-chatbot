from __future__ import annotations

from typing import TYPE_CHECKING

from app.orchestrator.types import Intent

if TYPE_CHECKING:
    from app.services.llm.provider import LLMProvider


_ALLOWED_INTENT_WORDS: tuple[str, ...] = (
    Intent.SYLLABUS.value,
    Intent.ADMIN.value,
    Intent.TOPIC.value,
    Intent.QUIZ.value,
    Intent.CONCEPT_TEST.value,
    Intent.PROGRAMMING_TEST.value,
    Intent.PERFORMANCE.value,
    Intent.VISUALIZATION.value,
    Intent.PROBLEM_SOLVING.value,
    Intent.UNKNOWN.value,
)


def _truncate(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return (text or "")[:limit]


def build_intent_prompt(message: str) -> str:
    allowed = ", ".join(_ALLOWED_INTENT_WORDS)
    msg = _truncate((message or "").strip(), 2000)
    return (
        "You are an intent classifier for an education chatbot.\n"
        "Choose the single best intent for the user's message.\n\n"
        f"Allowed intents: {allowed}\n\n"
        "Reply with EXACTLY ONE word: one of the allowed intents.\n"
        "No punctuation, no quotes, no explanation, no extra words.\n"
        "If unclear, reply: unknown\n\n"
        f"User message:\n{msg}"
    )


def _parse_intent_word(output: str) -> Intent:
    raw = (output or "").strip().lower()
    if not raw:
        return Intent.UNKNOWN

    parts = raw.split()
    if len(parts) != 1:
        return Intent.UNKNOWN

    word = parts[0].strip().strip(".,:;!?\"'`()[]{}<>")
    if not word:
        return Intent.UNKNOWN

    try:
        intent = Intent(word)
    except ValueError:
        return Intent.UNKNOWN

    # Disallow internal capability intents from LLM output.
    if intent == Intent.ASSESSMENT:
        return Intent.UNKNOWN

    return intent


async def classify_intent_llm(
    message: str,
    llm: "LLMProvider",
    *,
    model: str | None,
    timeout_seconds: float,
) -> Intent:
    """
    Classify intent using an LLM. The model is instructed to return a single-word intent.

    Returns Intent.UNKNOWN on any error, timeout, empty response, or invalid output.
    """
    if not message or not message.strip():
        return Intent.UNKNOWN
    prompt = build_intent_prompt(message)
    try:
        out = await llm.complete(
            prompt,
            model=model,
            temperature=0.0,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        return Intent.UNKNOWN
    return _parse_intent_word(out)

