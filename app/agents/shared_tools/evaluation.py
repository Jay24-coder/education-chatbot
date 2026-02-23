"""Scoring and rubric utilities for Quiz and Concept Test agents (Phase 2)."""

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.llm.provider import LLMProvider


def score_mcq(
    answer: str,
    correct: str,
    *,
    partial_credit_answers: list[str] | None = None,
) -> float:
    """
    Score a multiple-choice answer. Returns 1.0 for exact match (after normalizing),
    0.5 if answer is in partial_credit_answers, else 0.0.
    """
    a = (answer or "").strip().lower()
    c = (correct or "").strip().lower()
    if a == c:
        return 1.0
    if partial_credit_answers:
        normalized_partial = [x.strip().lower() for x in partial_credit_answers]
        if a in normalized_partial:
            return 0.5
    return 0.0


async def score_freetext(
    answer: str,
    rubric: str,
    llm_provider: "LLMProvider",
    *,
    model: str | None = None,
    timeout_seconds: float | None = None,
) -> float:
    """
    Use the LLM to score a free-text answer against a rubric. Returns a float in [0.0, 1.0].
    Prompt asks for a single number; parses the first number found in the response.
    """
    prompt = (
        f"Rubric (use this to evaluate):\n{rubric}\n\n"
        f"Student answer:\n{answer or '(empty)'}\n\n"
        "Reply with only a single number between 0.0 and 1.0 (0=wrong, 1=fully correct). "
        "No explanation, just the number."
    )
    response = await llm_provider.complete(
        prompt,
        model=model,
        temperature=0.0,
        timeout_seconds=timeout_seconds,
    )
    # Allow optional minus so that e.g. "-0.2" is parsed as -0.2 and clamped to 0.0
    match = re.search(r"-?(?:0?\.\d+|1\.0?|1)", (response or "").strip())
    if not match:
        return 0.0
    try:
        score = float(match.group(0))
        return max(0.0, min(1.0, score))
    except ValueError:
        return 0.0


def build_feedback(score: float, correct_answer: str | None = None) -> str:
    """
    Build short feedback string from score and optional correct answer.
    """
    if correct_answer is None:
        correct_answer = ""
    if score >= 1.0:
        return f"Correct! The answer is {correct_answer}." if correct_answer else "Correct!"
    if score >= 0.5:
        return (
            f"Partially correct. The full answer is: {correct_answer}."
            if correct_answer
            else "Partially correct."
        )
    return (
        f"Not quite. The correct answer is: {correct_answer}."
        if correct_answer
        else "Not quite."
    )
