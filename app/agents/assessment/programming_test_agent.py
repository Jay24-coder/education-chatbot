"""Programming Test Agent: single-challenge coding assessment with deterministic test cases."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.agents.shared_tools.programming_bank import ProgrammingChallenge, ProgrammingQuestionBank
from app.agents.shared_tools.test_case_runner import CaseRunResult, run_test_cases
from app.orchestrator.types import AgentRequest, AgentResponse, AssessmentResult, Intent

if TYPE_CHECKING:
    from app.agents.monitoring.performance_monitor_agent import PerformanceMonitorAgent
    from app.agents.shared_tools.test_case_runner import ExecutorCallable
    from app.services.context.store import ContextStore


KEY_PROGRAMMING_TEST_STATE = "programming_test:state"


def _parse_topic_and_difficulty(message: str) -> tuple[str | None, str | None]:
    """
    Best-effort extraction of topic and difficulty from the user's message.

    For now we support a small fixed vocabulary aligned with the seed challenges.
    """
    msg = (message or "").strip().lower()
    if not msg:
        return None, None

    topic: str | None = None
    if "array" in msg or "list" in msg:
        topic = "arrays"
    elif "string" in msg:
        topic = "strings"
    elif "math" in msg or "number" in msg:
        topic = "math"

    difficulty: str | None = None
    if "beginner" in msg or "easy" in msg:
        difficulty = "beginner"
    elif "intermediate" in msg or "medium" in msg:
        difficulty = "intermediate"
    elif "advanced" in msg or "hard" in msg:
        difficulty = "advanced"

    return topic, difficulty


def _challenge_to_state(challenge: ProgrammingChallenge) -> dict[str, Any]:
    """Serialize challenge identity for storage in ContextStore."""
    return {
        "id": challenge.id,
        "topic": challenge.topic,
        "difficulty": challenge.difficulty,
    }


class ProgrammingTestAgent(AbstractBaseAgent):
    """
    Agent for PROGRAMMING_TEST intent: start a single programming challenge and evaluate code submissions.

    Responsibilities:
    - start_test: select a challenge, store state, return description and instructions.
    - submit_code: load state, run test cases via executor, compute score, log result, and return feedback.
    """

    def __init__(
        self,
        context_store: "ContextStore",
        programming_bank: ProgrammingQuestionBank,
        performance_monitor: "PerformanceMonitorAgent",
        executor: "ExecutorCallable",
    ) -> None:
        super().__init__(agent_id="programming_test", capabilities=[Intent.PROGRAMMING_TEST.value])
        self._store = context_store
        self._bank = programming_bank
        self._perf = performance_monitor
        self._executor = executor

    def _get_state(self, session_id: str) -> dict[str, Any] | None:
        out = self._store.get(session_id, KEY_PROGRAMMING_TEST_STATE)
        return out.get(KEY_PROGRAMMING_TEST_STATE) if out else None

    def _set_state(self, session_id: str, state: dict[str, Any]) -> None:
        self._store.set(session_id, KEY_PROGRAMMING_TEST_STATE, state)

    def _clear_state(self, session_id: str) -> None:
        self._store.delete(session_id, KEY_PROGRAMMING_TEST_STATE)

    async def start_test(self, session_id: str, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Choose a programming challenge based on the message (topic/difficulty),
        store its identity in ContextStore, and return description + instructions.
        """
        topic, difficulty = _parse_topic_and_difficulty(message)
        challenge = self._bank.get_challenge(topic, difficulty)

        state = {
            "challenge": _challenge_to_state(challenge),
            "language": "python",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self._set_state(session_id, state)

        instructions = (
            "You will be solving a programming challenge.\n\n"
            "Please implement the requested function exactly as specified by the signature below. "
            "When you're ready, submit your code as a complete Python function (you may include helper "
            "functions if needed). The system will run your code against several hidden and visible tests."
        )

        content_lines = [
            f"**Programming test started: {challenge.title}**",
            "",
            challenge.description,
            "",
            f"**Function signature:** `{challenge.function_signature}`",
            "",
            instructions,
        ]
        content = "\n".join(content_lines)

        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={
                "intent": Intent.PROGRAMMING_TEST.value,
                "programming_test_started": True,
                "challenge_id": challenge.id,
                "topic": challenge.topic,
                "difficulty": challenge.difficulty,
            },
            error_message=None,
        )

    async def submit_code(self, session_id: str, code: str, context: dict[str, Any]) -> AgentResponse:
        """
        Evaluate submitted code against the stored challenge's test cases, log result, and return feedback.
        """
        state = self._get_state(session_id)
        if not state or "challenge" not in state:
            return AgentResponse(
                content="No programming test in progress. Start a new programming test before submitting code.",
                agent_id=self.agent_id,
                success=False,
                metadata={"intent": Intent.PROGRAMMING_TEST.value},
                error_message=None,
            )

        challenge_state = state["challenge"]
        topic = challenge_state.get("topic")
        difficulty = challenge_state.get("difficulty")
        # Re-select challenge deterministically using stored topic/difficulty.
        challenge = self._bank.get_challenge(topic, difficulty)

        test_results: list[CaseRunResult] = await run_test_cases(
            challenge=challenge,
            code=code,
            executor=self._executor,
        )

        total = len(test_results)
        passed_count = sum(1 for r in test_results if r.passed)
        score = float(passed_count) / float(total) if total > 0 else 0.0

        # Log to Performance Monitor
        user_id = (context or {}).get("user_id") or session_id or "default"
        self._perf.log_result(
            user_id,
            AssessmentResult(
                user_id=user_id,
                session_id=session_id,
                type="programming_test",
                topic=challenge.topic,
                score=round(score, 4),
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "challenge_id": challenge.id,
                    "test_case_count": total,
                    "passed_count": passed_count,
                },
            ),
        )

        visible_results = [r for r in test_results if not r.test_case.is_hidden]
        serialized_results = [
            {
                "test_case_id": r.test_case.id,
                "passed": r.passed,
                "actual_output": r.actual_output,
                "expected_output": r.expected_output,
                "error": r.error,
                "execution_time_ms": r.execution_time_ms,
            }
            for r in test_results
        ]
        lines = [
            f"**Programming test complete.**",
            f"**Score: {score:.0%}** ({passed_count}/{total} test cases passed)",
            "",
            "**Per-test-case results (visible tests only):**",
        ]
        for r in visible_results:
            status = "✅ Passed" if r.passed else "❌ Failed"
            expected_display = r.expected_output if r.expected_output is not None else "<none>"
            actual_display = (r.actual_output or "").strip()
            lines.append(
                f"- `{r.test_case.id}`: {status} | expected `{expected_display}`, got `{actual_display}`"
            )
            if r.error:
                lines.append(f"  - Error: {r.error}")

        content = "\n".join(lines)

        # Programming test is single-shot for now; clear state.
        self._clear_state(session_id)

        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata={
                "intent": Intent.PROGRAMMING_TEST.value,
                "result_type": "programming_test",
                "score": score,
                "topic": challenge.topic,
                "challenge_id": challenge.id,
                "completed": True,
                "test_case_results": serialized_results,
            },
            error_message=None,
        )

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Dispatch to start_test or submit_code based on session state.

        For now we use a simple rule:
        - If no programming_test state exists → start_test.
        - If state exists → treat the message as a code submission.
        """
        session_id = request.session_id or ""
        context = request.context or {}
        message = (request.message or "").strip()

        state = self._get_state(session_id)
        if not state:
            return await self.start_test(session_id, message, context)

        # When test is in progress, interpret the message body as code.
        return await self.submit_code(session_id, message, context)

