"""
Problem-solving agent: OCR from image, guardrail state machine, LLM for concepts/hints/solution.

First turn: image -> OCR + coarse classification -> initialize state -> guardrails -> PROBE -> LLM response.
Subsequent turns: load state from ContextStore, student reply -> LLM analysis -> next_state -> LLM response -> save state.
Optionally logs an assessment-like result when solution is shown.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.agents.problem_solving.guardrails import (
    Action,
    Analysis,
    GuardrailState,
    initial_state,
    next_state,
    state_from_dict,
    state_to_dict,
)
from app.agents.problem_solving.image_processor import process_problem_image
from app.observability.logging import get_logger
from app.orchestrator.types import AgentRequest, AgentResponse, Intent

if TYPE_CHECKING:
    from app.services.context.store import ContextStore
    from app.services.llm.provider import LLMProvider

KEY_PROBLEM_SOLVING_STATE = "problem_solving:state"


logger = get_logger(__name__)


async def _coarse_classify_async(problem_text: str, llm: "LLMProvider | None") -> tuple[str | None, str | None]:
    """Use LLM to get topic and difficulty (easy/medium/hard). Returns (topic, difficulty)."""
    if not llm or not problem_text.strip():
        return None, None
    try:
        prompt = (
            "Based on the following problem statement, reply with exactly two short labels on separate lines:\n"
            "TOPIC: <one or two words, e.g. algebra, kinematics>\n"
            "DIFFICULTY: <one of: easy, medium, hard>\n\n"
            "Problem:\n"
            f"{problem_text.strip()[:2000]}\n\n"
            "Reply only with TOPIC: and DIFFICULTY: lines, nothing else."
        )
        result = await llm.complete(prompt, temperature=0.0, timeout_seconds=10.0)
    except Exception:
        return None, None
    if not result:
        return None, None
    topic, difficulty = None, None
    for line in (result or "").strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("TOPIC:"):
            topic = line.split(":", 1)[-1].strip() or None
        elif line.upper().startswith("DIFFICULTY:"):
            raw = line.split(":", 1)[-1].strip().lower()
            if raw in ("easy", "medium", "hard"):
                difficulty = raw
    return topic, difficulty


async def _classify_understanding_async(
    problem_text: str,
    student_reply: str,
    llm: "LLMProvider | None",
) -> str:
    """LLM classifies understanding as weak, partial, or strong. Returns one word."""
    if not llm:
        return "partial"
    prompt = (
        "You are assessing a student's understanding of a problem.\n\n"
        f"Problem (summary): {problem_text[:500]}\n\n"
        f"Student's reply: {student_reply[:500]}\n\n"
        "Rate their understanding as exactly one word: weak, partial, or strong.\n"
        "Reply with only that one word, nothing else."
    )
    try:
        result = await llm.complete(prompt, temperature=0.0, timeout_seconds=10.0)
        word = (result or "").strip().lower()
        if word in ("weak", "partial", "strong"):
            return word
    except Exception:
        pass
    return "partial"


async def _generate_probe_async(problem_text: str, topic: str | None, difficulty: str | None, llm: "LLMProvider | None") -> str:
    """LLM generates a short probe question to assess the student."""
    if not llm:
        return "What part of this problem would you like to tackle first?"
    prompt = (
        "You are a tutor. The student will work on this problem. Write one short, friendly probe question "
        "to assess their current understanding (e.g. what they already know, or where they want to start). "
        "Do not give the solution. One or two sentences only.\n\n"
        f"Problem:\n{problem_text[:1500]}\n\n"
        "Your probe question:"
    )
    try:
        return (await llm.complete(prompt, temperature=0.3, timeout_seconds=15.0) or "").strip() or "What would you like to try first?"
    except Exception:
        return "What part of this problem would you like to tackle first?"


async def _generate_response_for_action_async(
    problem_text: str,
    student_reply: str,
    action: Action,
    guardrail_state: GuardrailState,
    llm: "LLMProvider | None",
) -> str:
    """Generate assistant message based on guardrail action (explain, similar problem, or hint/solution)."""
    if not llm:
        return _fallback_response_for_action(action)
    action_desc = {
        Action.EXPLAIN_CONCEPT: "Explain the key concept needed for this problem clearly and concisely. Do not give the full solution.",
        Action.GIVE_SIMILAR_PROBLEM: "Give one similar practice problem (same concept, different numbers or scenario) so the student can try. Do not give the solution yet.",
        Action.ALLOW_SOLVE: "The student has shown understanding. Give a brief hint or scaffolding to help them solve the original problem, or confirm they can proceed.",
        Action.PROBE: "Ask a short follow-up probe question to understand what the student knows.",
        Action.ASSESS: "Acknowledge their answer and ask one more clarifying question or give a brief hint.",
    }.get(action, "Acknowledge and provide brief help.")
    prompt = (
        "You are a tutor helping a student with a problem.\n\n"
        f"Problem:\n{problem_text[:1500]}\n\n"
        f"Student's latest reply: {student_reply[:500]}\n\n"
        f"Your task: {action_desc}\n\n"
        "Reply in 1-4 short sentences. Be clear and educational."
    )
    try:
        return (await llm.complete(prompt, temperature=0.3, timeout_seconds=20.0) or "").strip() or _fallback_response_for_action(action)
    except Exception:
        return _fallback_response_for_action(action)


def _fallback_response_for_action(action: Action) -> str:
    if action == Action.EXPLAIN_CONCEPT:
        return "Let me explain the key concept needed for this problem."
    if action == Action.GIVE_SIMILAR_PROBLEM:
        return "Try a similar problem first to practice the same idea."
    if action == Action.ALLOW_SOLVE:
        return "You're ready to work through the main problem. Try the next step."
    return "How would you like to proceed?"


class ProblemSolvingAgent(AbstractBaseAgent):
    """
    Agent for problem-solving flow: image OCR, guardrail state machine, LLM for concepts/hints/solution.
    First turn uses image processor for OCR + coarse classification and guardrails for first response.
    Subsequent turns load state from ContextStore, incorporate student reply, call guardrails, update state.
    """

    def __init__(
        self,
        context_store: "ContextStore",
        llm_provider: "LLMProvider | None" = None,
    ) -> None:
        super().__init__(agent_id="problem_solving", capabilities=[Intent.UNKNOWN.value])
        self._store = context_store
        self._llm = llm_provider

    def _get_stored_state(self, session_id: str) -> dict[str, Any] | None:
        out = self._store.get(session_id, KEY_PROBLEM_SOLVING_STATE)
        return out.get(KEY_PROBLEM_SOLVING_STATE) if out else None

    def _set_stored_state(self, session_id: str, guardrail_state: GuardrailState, problem_text: str) -> None:
        self._store.set(
            session_id,
            KEY_PROBLEM_SOLVING_STATE,
            {"guardrail": state_to_dict(guardrail_state), "problem_text": problem_text},
        )

    def _clear_state(self, session_id: str) -> None:
        self._store.delete(session_id, KEY_PROBLEM_SOLVING_STATE)

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        First turn: image in context -> OCR, classify, init state, PROBE, LLM response, save state.
        Subsequent turns: load state, analyze understanding, next_state, LLM response, save state.
        """
        session_id = request.session_id or ""
        context = request.context or {}
        message = (request.message or "").strip()
        correlation_id = request.correlation_id
        logger.info(
            "agent_request_start",
            agent_id=self.agent_id,
            intent="problem_solving",
            correlation_id=correlation_id,
            session_id=session_id or None,
        )

        # Check for image (first turn): context may have image_bytes or image_path
        image_bytes = context.get("image_bytes") if isinstance(context.get("image_bytes"), bytes) else None
        image_path = context.get("image_path")
        if image_path is not None and not isinstance(image_path, str):
            image_path = None

        stored = self._get_stored_state(session_id)
        guardrail_state: GuardrailState | None = None
        problem_text = ""

        if stored and isinstance(stored, dict):
            guardrail_state = state_from_dict(stored.get("guardrail") or {})
            problem_text = stored.get("problem_text") or ""

        # First turn with image: OCR, classify, initialize, return probe and save state
        if (image_bytes is not None or image_path is not None) and guardrail_state is None:
            try:
                if image_bytes is not None:
                    result = process_problem_image(image_bytes)
                else:
                    from pathlib import Path
                    result = process_problem_image(Path(image_path))
                problem_text = result.text or "Problem statement could not be extracted."
            except Exception as e:
                logger.error(
                    "problem_solving_image_processing_error",
                    correlation_id=correlation_id,
                    session_id=session_id or None,
                )
                return AgentResponse(
                    content=f"I couldn't read the problem from the image: {e}. Please try again or type the problem.",
                    agent_id=self.agent_id,
                    success=False,
                    metadata={"intent": "problem_solving", "correlation_id": correlation_id},
                    error_message=str(e),
                )
            topic, difficulty = None, None
            if self._llm:
                try:
                    topic, difficulty = await _coarse_classify_async(problem_text, self._llm)
                except Exception:
                    pass
            state = initial_state(topic=topic, difficulty=difficulty)
            _, action = next_state(None, "", Analysis(understanding="partial"))
            probe_content = await _generate_probe_async(problem_text, topic, difficulty, self._llm)
            self._set_stored_state(session_id, state, problem_text)
            return AgentResponse(
                content=probe_content,
                agent_id=self.agent_id,
                success=True,
                metadata={
                    "intent": "problem_solving",
                    "correlation_id": correlation_id,
                    "action": action.value,
                    "topic": topic,
                    "difficulty": difficulty,
                },
                error_message=None,
            )

        # No image and no existing state: ask for problem or image
        if guardrail_state is None:
            response = AgentResponse(
                content="Share a problem (upload an image or describe it) to get started.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": "problem_solving", "correlation_id": correlation_id},
                error_message=None,
            )
            logger.info(
                "agent_request_done",
                agent_id=self.agent_id,
                intent="problem_solving",
                correlation_id=correlation_id,
                session_id=session_id or None,
                response_length=len(response.content or ""),
            )
            return response

        # Subsequent turn: analyze understanding, next_state, generate response, save
        if not message:
            response = AgentResponse(
                content="Please reply with your thoughts or answer so I can help you.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": "problem_solving", "correlation_id": correlation_id},
                error_message=None,
            )
            logger.info(
                "agent_request_done",
                agent_id=self.agent_id,
                intent="problem_solving",
                correlation_id=correlation_id,
                session_id=session_id or None,
                response_length=len(response.content or ""),
            )
            return response

        understanding = await _classify_understanding_async(problem_text, message, self._llm)
        analysis = Analysis(understanding=understanding)
        new_state, action = next_state(guardrail_state, message, analysis)
        content = await _generate_response_for_action_async(
            problem_text, message, action, new_state, self._llm
        )
        self._set_stored_state(session_id, new_state, problem_text)

        # Optionally log assessment-like result when solution path is reached
        metadata: dict[str, Any] = {
            "intent": "problem_solving",
            "correlation_id": correlation_id,
            "action": action.value,
            "stage": new_state.stage.value,
        }
        if new_state.stage.value == "solve" and action == Action.ALLOW_SOLVE:
            try:
                user_id = context.get("user_id") if isinstance(context.get("user_id"), str) else None
                if user_id:
                    self._store.append_assessment_result(
                        user_id,
                        {
                            "type": "problem_solving",
                            "topic": new_state.topic or "unknown",
                            "score": 1.0,
                            "session_id": session_id,
                            "metadata": {"stage": "solve", "action": action.value},
                        },
                    )
            except Exception:
                pass

        response = AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata=metadata,
            error_message=None,
        )
        logger.info(
            "agent_request_done",
            agent_id=self.agent_id,
            intent="problem_solving",
            correlation_id=correlation_id,
            session_id=session_id or None,
            response_length=len(response.content or ""),
        )
        return response
