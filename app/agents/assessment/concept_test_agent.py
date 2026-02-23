"""Concept Test Agent: multi-turn free-text assessment with follow-ups and mastery summary."""

from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.agents.shared_tools.evaluation import score_freetext
from app.orchestrator.types import AgentRequest, AgentResponse, AssessmentResult, Intent

if TYPE_CHECKING:
    from app.agents.monitoring.performance_monitor_agent import PerformanceMonitorAgent
    from app.services.context.store import ContextStore
    from app.services.llm.provider import LLMProvider

KEY_CONCEPT_TEST_STATE = "concept_test:state"
MIN_QUESTIONS = 3
MAX_QUESTIONS = 5
FOLLOW_UP_THRESHOLD = 0.6
MAX_FOLLOW_UPS_PER_QUESTION = 2
MASTERY_FULL = 0.8
MASTERY_PARTIAL = 0.5


def _parse_topic(message: str) -> str:
    """Extract topic from user message; default 'general'."""
    msg = (message or "").strip().lower()
    if not msg:
        return "general"
    # Common topic words; extend as needed
    for part in msg.split():
        if len(part) > 2 and part not in ("the", "a", "on", "for", "test", "concept", "start", "begin"):
            return part
    return "general" if "topic" not in msg else "general"


def _parse_questions_from_llm_response(response: str) -> list[dict[str, str]]:
    """
    Parse LLM response into list of {text, rubric}.
    Expected format: blocks of "QUESTION: ..." and "RUBRIC: ..." or "Q: ..." / "R: ...".
    """
    out: list[dict[str, str]] = []
    block = {"text": "", "rubric": ""}
    for line in (response or "").split("\n"):
        line = line.strip()
        if not line:
            if block["text"] or block["rubric"]:
                if block["text"]:
                    block["rubric"] = block["rubric"] or "Correct if the answer shows understanding."
                    out.append(block)
                block = {"text": "", "rubric": ""}
            continue
        if line.upper().startswith("QUESTION:") or line.upper().startswith("Q:"):
            if block["text"] or block["rubric"]:
                if block["text"]:
                    block["rubric"] = block["rubric"] or "Correct if the answer shows understanding."
                    out.append(block)
                block = {"text": "", "rubric": ""}
            block["text"] = line.split(":", 1)[-1].strip()
        elif line.upper().startswith("RUBRIC:") or line.upper().startswith("R:"):
            block["rubric"] = line.split(":", 1)[-1].strip()
        elif block["text"] and not block["rubric"]:
            block["text"] += " " + line
        elif block["rubric"]:
            block["rubric"] += " " + line
    if block["text"]:
        block["rubric"] = block["rubric"] or "Correct if the answer shows understanding."
        out.append(block)
    return out[:MAX_QUESTIONS]


class ConceptTestAgent(AbstractBaseAgent):
    """
    Agent for CONCEPT_TEST intent: multi-turn free-text concept check.
    Uses ContextStore for state, score_freetext for evaluation, follow-ups when score < 0.6,
    and PerformanceMonitor.log_result on finalize.
    """

    def __init__(
        self,
        context_store: "ContextStore",
        llm_provider: "LLMProvider | None",
        performance_monitor: "PerformanceMonitorAgent",
    ) -> None:
        super().__init__(agent_id="concept_test", capabilities=[Intent.CONCEPT_TEST.value])
        self._store = context_store
        self._llm = llm_provider
        self._perf = performance_monitor

    def _get_state(self, session_id: str) -> dict[str, Any] | None:
        out = self._store.get(session_id, KEY_CONCEPT_TEST_STATE)
        return out.get(KEY_CONCEPT_TEST_STATE) if out else None

    def _set_state(self, session_id: str, state: dict[str, Any]) -> None:
        self._store.set(session_id, KEY_CONCEPT_TEST_STATE, state)

    def _clear_state(self, session_id: str) -> None:
        self._store.delete(session_id, KEY_CONCEPT_TEST_STATE)

    async def start_concept_test(self, session_id: str, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Accept topic from request; generate 3--5 probing questions via LLM with structured prompt;
        store state in concept_test:state; return first question.
        """
        if not self._llm:
            return AgentResponse(
                content="Concept test is not available (no LLM configured).",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.CONCEPT_TEST.value},
                error_message=None,
            )
        topic = _parse_topic(message)
        prompt = (
            f"Generate a concept test for the topic: **{topic}**.\n\n"
            "Output exactly 3 to 5 probing questions. For each question output two lines:\n"
            "QUESTION: <the question text>\n"
            "RUBRIC: <short rubric describing what a correct answer should include>\n\n"
            "Use QUESTION: and RUBRIC: as labels. No numbering in the question text."
        )
        response = await self._llm.complete(prompt, temperature=0.4, timeout_seconds=30.0)
        questions = _parse_questions_from_llm_response(response)
        if len(questions) < MIN_QUESTIONS:
            # Fallback: at least one block
            questions = [
                {"text": f"Explain the main idea of {topic} in your own words.", "rubric": "Correct if key concepts are mentioned."}
            ] * MIN_QUESTIONS
        questions = questions[:MAX_QUESTIONS]

        state = {
            "topic": topic,
            "questions": questions,
            "current_q": 0,
            "question_turn_scores": [[] for _ in questions],
            "current_follow_ups": 0,
            "current_follow_up_text": None,
        }
        self._set_state(session_id, state)
        q0 = state["questions"][0]
        content = (
            f"Concept test started on **{topic}** ({len(questions)} questions).\n\n"
            f"**Question 1 of {len(questions)}:**\n{q0['text']}"
        )
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.CONCEPT_TEST.value, "concept_test_started": True},
            error_message=None,
        )

    async def evaluate_answer(self, session_id: str, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Score current answer with score_freetext using question rubric; store partial score;
        if score < 0.6 and follow-ups < 2, generate simpler follow-up question; else advance.
        """
        state = self._get_state(session_id)
        if not state:
            return AgentResponse(
                content="No concept test in progress. Say something like \"Start a concept test on algebra\" to begin.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.CONCEPT_TEST.value},
                error_message=None,
            )
        if not self._llm:
            return AgentResponse(
                content="LLM not available for scoring.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.CONCEPT_TEST.value},
                error_message=None,
            )

        questions = state["questions"]
        current_q = state["current_q"]
        question_turn_scores = state["question_turn_scores"]
        current_follow_ups = state.get("current_follow_ups", 0)
        current_follow_up_text = state.get("current_follow_up_text")

        if current_q >= len(questions):
            return await self.finalize_concept_test(session_id, context)

        q = questions[current_q]
        rubric = q.get("rubric") or "Correct if the answer shows understanding."
        score = await score_freetext(message or "", rubric, self._llm)
        question_turn_scores[current_q] = question_turn_scores[current_q] + [score]

        # Follow-up logic: if score < 0.6 and follow-ups < 2, generate simpler follow-up
        if score < FOLLOW_UP_THRESHOLD and current_follow_ups < MAX_FOLLOW_UPS_PER_QUESTION:
            follow_up_prompt = (
                f"Original question: {q['text']}\n\n"
                f"Student's answer (showing incomplete understanding): {message[:500]}\n\n"
                "Generate one simpler, more focused follow-up question to probe the same concept. "
                "Reply with only the follow-up question, no preamble."
            )
            follow_up_response = await self._llm.complete(follow_up_prompt, temperature=0.3, timeout_seconds=15.0)
            follow_up_text = (follow_up_response or "").strip() or "Can you explain that in a bit more detail?"
            state["current_follow_ups"] = current_follow_ups + 1
            state["current_follow_up_text"] = follow_up_text
            self._set_state(session_id, state)
            feedback = f"Your answer was partially correct (score {score:.0%}). Let me ask a simpler follow-up."
            content = f"{feedback}\n\n**Follow-up:**\n{follow_up_text}"
            return AgentResponse(
                content=content,
                agent_id=self.agent_id,
                success=True,
                metadata={"intent": Intent.CONCEPT_TEST.value, "score": score, "follow_up": True},
                error_message=None,
            )

        # Advance to next question (or finalize)
        state["current_follow_ups"] = 0
        state["current_follow_up_text"] = None
        state["current_q"] = current_q + 1
        self._set_state(session_id, state)

        feedback = f"Score for this answer: {score:.0%}."
        if state["current_q"] >= len(questions):
            return await self.finalize_concept_test(session_id, context)
        next_q = questions[state["current_q"]]
        total = len(questions)
        content = f"{feedback}\n\n**Question {state['current_q'] + 1} of {total}:**\n{next_q['text']}"
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.CONCEPT_TEST.value, "score": score},
            error_message=None,
        )

    async def finalize_concept_test(self, session_id: str, context: dict[str, Any]) -> AgentResponse:
        """
        Aggregate turn scores (best per question); set mastery FULL/PARTIAL/NEEDS_REVIEW;
        call performance_monitor.log_result(); return summary with explanation gaps.
        """
        state = self._get_state(session_id)
        if not state:
            return AgentResponse(
                content="No concept test to finalize.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.CONCEPT_TEST.value},
                error_message=None,
            )

        questions = state.get("questions") or []
        question_turn_scores = state.get("question_turn_scores") or [[] for _ in questions]
        topic = state.get("topic") or "general"
        user_id = (context or {}).get("user_id") or session_id or "default"

        best_scores = [
            max(scores) if scores else 0.0
            for scores in question_turn_scores
        ]
        aggregate_score = sum(best_scores) / len(best_scores) if best_scores else 0.0

        if aggregate_score >= MASTERY_FULL:
            mastery = "FULL"
        elif aggregate_score >= MASTERY_PARTIAL:
            mastery = "PARTIAL"
        else:
            mastery = "NEEDS_REVIEW"

        explanation_gaps = [
            questions[i].get("text", "")[:80]
            for i in range(len(questions))
            if i < len(best_scores) and best_scores[i] < FOLLOW_UP_THRESHOLD
        ]

        self._perf.log_result(
            user_id,
            AssessmentResult(
                user_id=user_id,
                session_id=session_id,
                type="concept_test",
                topic=topic,
                score=round(aggregate_score, 4),
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "mastery": mastery,
                    "question_count": len(questions),
                    "explanation_gaps": explanation_gaps,
                },
            ),
        )
        self._clear_state(session_id)

        gap_text = ""
        if explanation_gaps:
            gap_text = "\n\n**Topics to review:**\n" + "\n".join(f"- {g[:80]}..." if len(g) > 80 else f"- {g}" for g in explanation_gaps)
        content = (
            f"**Concept test complete.**\n\n"
            f"**Score: {aggregate_score:.0%}** | **Mastery: {mastery}**\n"
            f"({sum(1 for s in best_scores if s >= FOLLOW_UP_THRESHOLD)}/{len(best_scores)} questions at or above threshold)"
            + gap_text
        )
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={
                "intent": Intent.CONCEPT_TEST.value,
                "result_type": "concept_test",
                "score": aggregate_score,
                "topic": topic,
                "mastery": mastery,
            },
            error_message=None,
        )

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Check ContextStore for concept_test state: new session → start_concept_test;
        continuing → evaluate_answer; explicit finish → finalize_concept_test.
        """
        session_id = request.session_id or ""
        context = request.context or {}
        message = (request.message or "").strip()

        state = self._get_state(session_id)
        finish_keywords = ["done", "finish", "end", "submit", "that's all", "stop"]
        is_finish = any(kw in message.lower() for kw in finish_keywords) and len(message.split()) <= 3
        start_keywords = ["concept test", "start", "begin", "algebra", "calculus", "kinematics", "waves"]
        is_start_like = any(kw in message.lower() for kw in start_keywords)

        if state and is_finish:
            return await self.finalize_concept_test(session_id, context)
        if state:
            return await self.evaluate_answer(session_id, message, context)
        # No state: only start if message looks like a start request; else no concept test in progress
        if not is_start_like:
            return AgentResponse(
                content="No concept test in progress. Say something like \"Start a concept test on algebra\" to begin.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.CONCEPT_TEST.value},
                error_message=None,
            )
        return await self.start_concept_test(session_id, message, context)
