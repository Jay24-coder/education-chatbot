"""Quiz Agent: start quiz, submit answers, score with evaluation utilities, finalize and log to Performance Monitor."""

from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.agents.shared_tools.evaluation import build_feedback, score_mcq
from app.agents.shared_tools.question_bank import (
    DifficultyLevel,
    Question,
    QuestionBank,
    TopicArea,
)
from app.orchestrator.types import AgentRequest, AgentResponse, AssessmentResult, Intent

if TYPE_CHECKING:
    from app.agents.monitoring.performance_monitor_agent import PerformanceMonitorAgent
    from app.services.context.store import ContextStore

KEY_QUIZ_STATE = "quiz:state"
KEY_SUGGESTED_DIFFICULTY = "quiz:suggested_difficulty"
QUESTION_COUNT = 5
DIFFICULTY_ORDER = ["beginner", "intermediate", "advanced"]


def _parse_topic_and_difficulty(message: str) -> tuple[str, str]:
    """Extract topic and difficulty from user message; defaults: algebra, beginner."""
    msg = (message or "").strip().lower()
    topic = "algebra"
    for t in [a.value for a in TopicArea]:
        if t in msg:
            topic = t
            break
    difficulty = "beginner"
    for d in DIFFICULTY_ORDER:
        if d in msg:
            difficulty = d
            break
    return topic, difficulty


def _question_to_state_q(q: Question) -> dict[str, Any]:
    """Serialize a Question for storage in quiz state."""
    return {
        "topic": q.topic,
        "difficulty": q.difficulty,
        "text": q.text,
        "correct_answer": q.correct_answer,
        "options": list(q.options),
    }


def _format_question_prompt(q: dict[str, Any], index: int, total: int) -> str:
    """Format current question for display."""
    lines = [f"**Question {index + 1} of {total}**", q["text"]]
    opts = q.get("options") or []
    if opts:
        for i, o in enumerate(opts):
            lines.append(f"  {chr(65 + i)}. {o}")
    return "\n".join(lines)


class QuizAgent(AbstractBaseAgent):
    """
    Agent for QUIZ intent: start quiz, submit answers, get feedback, finalize with score.
    Uses QuestionBank, evaluation.score_mcq, and PerformanceMonitor.log_result.
    """

    def __init__(
        self,
        context_store: "ContextStore",
        question_bank: QuestionBank,
        performance_monitor: "PerformanceMonitorAgent",
    ) -> None:
        super().__init__(agent_id="quiz", capabilities=[Intent.QUIZ.value])
        self._store = context_store
        self._qbank = question_bank
        self._perf = performance_monitor

    def _get_quiz_state(self, session_id: str) -> dict[str, Any] | None:
        """Return quiz state dict if present, else None."""
        out = self._store.get(session_id, KEY_QUIZ_STATE)
        return out.get(KEY_QUIZ_STATE) if out else None

    def _set_quiz_state(self, session_id: str, state: dict[str, Any]) -> None:
        self._store.set(session_id, KEY_QUIZ_STATE, state)

    def _clear_quiz_state(self, session_id: str) -> None:
        self._store.delete(session_id, KEY_QUIZ_STATE)

    def _get_suggested_difficulty(self, session_id: str) -> str:
        out = self._store.get(session_id, KEY_SUGGESTED_DIFFICULTY)
        d = (out or {}).get(KEY_SUGGESTED_DIFFICULTY)
        return d if d in DIFFICULTY_ORDER else "beginner"

    def _set_suggested_difficulty(self, session_id: str, difficulty: str) -> None:
        self._store.set(session_id, KEY_SUGGESTED_DIFFICULTY, difficulty)

    async def start_quiz(self, session_id: str, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Read topic and difficulty from request (or suggested_difficulty); fetch N questions;
        store state under quiz:{session_id}:state and return first question.
        """
        suggested = self._get_suggested_difficulty(session_id)
        topic, difficulty = _parse_topic_and_difficulty(message)
        if topic not in [t.value for t in TopicArea]:
            topic = "algebra"
        if difficulty not in DIFFICULTY_ORDER:
            difficulty = suggested

        questions = self._qbank.get_questions(topic, difficulty, QUESTION_COUNT)
        if not questions:
            return AgentResponse(
                content=f"No questions available for **{topic}** at **{difficulty}**. Try another topic or difficulty.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.QUIZ.value},
                error_message=None,
            )

        state = {
            "topic": topic,
            "difficulty": difficulty,
            "questions": [_question_to_state_q(q) for q in questions],
            "answers": [],
            "current_q": 0,
            "consecutive_correct": 0,
            "consecutive_wrong": 0,
            "suggested_difficulty": difficulty,
        }
        self._set_quiz_state(session_id, state)
        total = len(state["questions"])
        content = _format_question_prompt(state["questions"][0], 0, total)
        content = f"Quiz started: **{topic}** ({difficulty}), {total} questions.\n\n" + content
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.QUIZ.value, "quiz_started": True},
            error_message=None,
        )

    async def submit_answer(self, session_id: str, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Retrieve current question from state; score with score_mcq; update state and consecutive counters;
        apply adaptive difficulty; return feedback and next question or finalize.
        """
        state = self._get_quiz_state(session_id)
        if not state:
            return AgentResponse(
                content="No quiz in progress. Say something like \"Start a quiz on algebra\" to begin.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.QUIZ.value},
                error_message=None,
            )

        questions = state["questions"]
        current_q = state["current_q"]
        answers = state["answers"]
        if current_q >= len(questions):
            return await self.finalize_quiz(session_id, context)

        q = questions[current_q]
        correct = q.get("correct_answer") or ""
        options = q.get("options") or []
        # Allow matching by option letter (A/B/C/D) or by answer text
        answer_text = (message or "").strip()
        if len(answer_text) == 1 and options:
            idx = ord(answer_text.upper()) - ord("A")
            if 0 <= idx < len(options):
                answer_text = options[idx]
        score = score_mcq(answer_text, correct)
        answers.append({"answer": message, "score": score})

        # Consecutive correct/wrong for adaptive
        consecutive_correct = state.get("consecutive_correct", 0)
        consecutive_wrong = state.get("consecutive_wrong", 0)
        if score >= 1.0:
            consecutive_correct += 1
            consecutive_wrong = 0
        else:
            consecutive_wrong += 1
            consecutive_correct = 0

        suggested_difficulty = state.get("suggested_difficulty", state["difficulty"])
        # Use current suggested_difficulty so we can escalate beginner → intermediate → advanced
        diff_idx = DIFFICULTY_ORDER.index(suggested_difficulty) if suggested_difficulty in DIFFICULTY_ORDER else 0
        if consecutive_correct >= 2 and diff_idx < len(DIFFICULTY_ORDER) - 1:
            suggested_difficulty = DIFFICULTY_ORDER[diff_idx + 1]
        elif consecutive_wrong >= 2 and diff_idx > 0:
            suggested_difficulty = DIFFICULTY_ORDER[diff_idx - 1]

        state["answers"] = answers
        state["current_q"] = current_q + 1
        state["consecutive_correct"] = consecutive_correct
        state["consecutive_wrong"] = consecutive_wrong
        state["suggested_difficulty"] = suggested_difficulty

        feedback = build_feedback(score, correct)
        if state["current_q"] >= len(questions):
            self._set_quiz_state(session_id, state)
            return await self.finalize_quiz(session_id, context)

        self._set_quiz_state(session_id, state)
        next_q = questions[state["current_q"]]
        total = len(questions)
        next_content = _format_question_prompt(next_q, state["current_q"], total)
        content = f"{feedback}\n\n**Next question:**\n{next_content}"
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={"intent": Intent.QUIZ.value, "score": score},
            error_message=None,
        )

    async def finalize_quiz(self, session_id: str, context: dict[str, Any]) -> AgentResponse:
        """
        Compute total score, call performance_monitor.log_result(), clear state,
        persist suggested_difficulty, return summary with per-question breakdown.
        """
        state = self._get_quiz_state(session_id)
        if not state:
            return AgentResponse(
                content="No quiz to finalize.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.QUIZ.value},
                error_message=None,
            )

        answers = state.get("answers") or []
        questions = state.get("questions") or []
        topic = state.get("topic") or "general"
        suggested = state.get("suggested_difficulty") or "beginner"

        if not answers:
            total_score = 0.0
        else:
            total_score = sum(a["score"] for a in answers) / len(answers)

        # Per-question breakdown lines
        breakdown_lines = ["**Per-question breakdown:**"]
        for i, (a, q) in enumerate(zip(answers, questions)):
            pct = "✓" if a["score"] >= 1.0 else ("~" if a["score"] >= 0.5 else "✗")
            breakdown_lines.append(f"  Q{i + 1}: {pct} ({a['score']:.0%}) — {q.get('text', '')[:50]}...")

        user_id = (context or {}).get("user_id") or session_id or "default"
        self._perf.log_result(
            user_id,
            AssessmentResult(
                user_id=user_id,
                session_id=session_id,
                type="quiz",
                topic=topic,
                score=round(total_score, 4),
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={"question_count": len(questions), "suggested_difficulty": suggested},
            ),
        )

        self._set_suggested_difficulty(session_id, suggested)
        self._clear_quiz_state(session_id)

        content = (
            f"**Quiz complete.**\n\n"
            f"**Score: {total_score:.0%}** ({sum(a['score'] for a in answers)}/{len(answers)} correct)\n\n"
            + "\n".join(breakdown_lines)
            + f"\n\nNext time we suggest **{suggested}** difficulty."
        )
        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={
                "intent": Intent.QUIZ.value,
                "result_type": "quiz",
                "score": total_score,
                "topic": topic,
            },
            error_message=None,
        )

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Dispatch to start_quiz() or submit_answer() based on session state.
        If no quiz state and message looks like starting a quiz → start_quiz; else if state exists → submit_answer;
        if no state and message doesn't look like start → start_quiz with defaults.
        """
        session_id = request.session_id or ""
        context = request.context or {}
        message = (request.message or "").strip()

        state = self._get_quiz_state(session_id)
        # Starting: no state and (message suggests "start" / "quiz" / topic or difficulty)
        start_keywords = ["start", "begin", "quiz", "give me", "want to take"] + DIFFICULTY_ORDER + [t.value for t in TopicArea]
        is_start = not state and any(kw in message.lower() for kw in start_keywords)
        if is_start or not state:
            return await self.start_quiz(session_id, message, context)
        return await self.submit_answer(session_id, message, context)
