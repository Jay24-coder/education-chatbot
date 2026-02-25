from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from app.agents.assessment.programming_test_agent import (
    KEY_PROGRAMMING_TEST_STATE,
    ProgrammingTestAgent,
)
from app.agents.shared_tools.programming_bank import (
    ProgrammingChallenge,
    ProgrammingQuestionBank,
    ProgrammingTestCase,
)
from app.agents.shared_tools.test_case_runner import CaseRunResult, ExecutionResult
from app.orchestrator.types import AssessmentResult


class InMemoryStore:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def get(self, session_id: str, key: str) -> Dict[str, Any] | None:
        return self._data.get(session_id)

    def set(self, session_id: str, key: str, value: Any) -> None:
        self._data.setdefault(session_id, {})
        self._data[session_id][key] = value

    def delete(self, session_id: str, key: str) -> None:
        if session_id in self._data and key in self._data[session_id]:
            del self._data[session_id][key]

    def get_state(self, session_id: str) -> Dict[str, Any] | None:
        return (self._data.get(session_id) or {}).get(KEY_PROGRAMMING_TEST_STATE)


class DummyPerformanceMonitor:
    def __init__(self) -> None:
        self.logged: List[AssessmentResult] = []

    def log_result(self, user_id: str, result: AssessmentResult) -> None:
        self.logged.append(result)


async def fake_executor_always_pass(_code: str, _language: str, _timeout: float) -> ExecutionResult:
    tc = ProgrammingTestCase(id="t1", input="1, 2", expected_output="3")
    tr = CaseRunResult(
        test_case=tc,
        passed=True,
        actual_output="3",
        expected_output="3",
        error=None,
        execution_time_ms=1.0,
    )
    return ExecutionResult(test_results=[tr], all_passed=True, stdout="3\n", stderr="", error=None)


async def fake_executor_partial_fail(_code: str, _language: str, _timeout: float) -> ExecutionResult:
    t1 = ProgrammingTestCase(id="t1", input="1, 2", expected_output="3")
    t2 = ProgrammingTestCase(id="t2", input="2, 2", expected_output="4")
    r1 = CaseRunResult(
        test_case=t1,
        passed=True,
        actual_output="3",
        expected_output="3",
        error=None,
        execution_time_ms=1.0,
    )
    r2 = CaseRunResult(
        test_case=t2,
        passed=False,
        actual_output="5",
        expected_output="4",
        error=None,
        execution_time_ms=1.0,
    )
    return ExecutionResult(test_results=[r1, r2], all_passed=False, stdout="3\n5\n", stderr="", error=None)


class SingleChallengeBank(ProgrammingQuestionBank):
    def __init__(self, challenge: ProgrammingChallenge) -> None:
        self._challenge = challenge

    def get_challenge(self, topic: str | None, difficulty: str | None) -> ProgrammingChallenge:
        return self._challenge


def _make_challenge() -> ProgrammingChallenge:
    return ProgrammingChallenge(
        id="sum_two_numbers",
        title="Sum two numbers",
        description="Return the sum of two integers.",
        function_signature="def sum_two_numbers(a: int, b: int) -> int:",
        language="python",
        difficulty="beginner",
        topic="math",
        test_cases=[
            ProgrammingTestCase(id="t1", input="1, 2", expected_output="3"),
            ProgrammingTestCase(id="t2", input="2, 2", expected_output="4", is_hidden=True),
        ],
    )


@pytest.mark.asyncio
async def test_start_test_stores_state_and_returns_instructions():
    store = InMemoryStore()
    perf = DummyPerformanceMonitor()
    challenge = _make_challenge()
    bank = SingleChallengeBank(challenge)
    agent = ProgrammingTestAgent(
        context_store=store,
        programming_bank=bank,
        performance_monitor=perf,
        executor=fake_executor_always_pass,
    )

    session_id = "sess1"
    resp = await agent.start_test(session_id, "start programming test on math beginner", context={})

    assert resp.success is True
    assert "Programming test started" in resp.content
    state = store.get_state(session_id)
    assert state is not None
    assert state["challenge"]["id"] == challenge.id


@pytest.mark.asyncio
async def test_submit_code_without_state_returns_error_response():
    store = InMemoryStore()
    perf = DummyPerformanceMonitor()
    challenge = _make_challenge()
    bank = SingleChallengeBank(challenge)
    agent = ProgrammingTestAgent(
        context_store=store,
        programming_bank=bank,
        performance_monitor=perf,
        executor=fake_executor_always_pass,
    )

    resp = await agent.submit_code("sess-missing", "def sum_two_numbers(a, b): return a + b", context={})

    assert resp.success is False
    assert "no programming test in progress" in resp.content.lower()


@pytest.mark.asyncio
async def test_submit_code_logs_result_and_returns_score():
    store = InMemoryStore()
    perf = DummyPerformanceMonitor()
    challenge = _make_challenge()
    bank = SingleChallengeBank(challenge)
    agent = ProgrammingTestAgent(
        context_store=store,
        programming_bank=bank,
        performance_monitor=perf,
        executor=fake_executor_partial_fail,
    )

    session_id = "sess-score"
    await agent.start_test(session_id, "start programming test on math beginner", context={"user_id": "u1"})

    resp = await agent.submit_code(session_id, "def sum_two_numbers(a, b): return a + b", context={"user_id": "u1"})

    assert resp.success is True
    assert "Score:" in resp.content
    meta = resp.metadata
    assert meta.get("result_type") == "programming_test"
    assert 0 <= meta.get("score", 0.0) <= 1
    # Performance monitor should have been called
    assert len(perf.logged) == 1
    logged = perf.logged[0]
    assert logged.type == "programming_test"
    assert logged.topic == challenge.topic

