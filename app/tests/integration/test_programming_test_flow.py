import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_agent_registry,
    get_performance_monitor,
    get_programming_test_agent,
)
from app.api.main import create_app
from app.agents.assessment.programming_test_agent import ProgrammingTestAgent
from app.agents.monitoring.performance_monitor_agent import PerformanceMonitorAgent
from app.agents.shared_tools.programming_bank import ProgrammingQuestionBank
from app.agents.shared_tools.test_case_runner import CaseRunResult, ExecutionResult
from app.orchestrator.registry import AgentRegistry
from app.orchestrator.types import AssessmentResult, Intent
from app.services.context.memory_store import MemoryStore


async def fake_executor_echo_hello(_code: str, _language: str, _timeout: float) -> ExecutionResult:
    # Minimal executor that always passes one visible test case with output "hello"
    from app.agents.shared_tools.programming_bank import ProgrammingTestCase

    tc = ProgrammingTestCase(id="t1", input="'world'", expected_output="hello")
    tr = CaseRunResult(
        test_case=tc,
        passed=True,
        actual_output="hello",
        expected_output="hello",
        error=None,
        execution_time_ms=1.0,
    )
    return ExecutionResult(test_results=[tr], all_passed=True, stdout="hello\n", stderr="", error=None)


class RecordingPerformanceMonitor(PerformanceMonitorAgent):
    def __init__(self, context_store: MemoryStore) -> None:
        super().__init__(context_store)
        self.logged_results: list[AssessmentResult] = []

    def log_result(self, user_id: str, result: AssessmentResult) -> None:
        super().log_result(user_id, result)
        self.logged_results.append(result)


class TestProgrammingTestFlow:
    def _make_client_and_store(self):
        app = create_app()
        store = MemoryStore()
        perf = RecordingPerformanceMonitor(store)
        registry = AgentRegistry()
        # Register only what we need for this flow
        registry.register_capabilities(perf)
        registry.register(
            Intent.PROGRAMMING_TEST,
            ProgrammingTestAgent(
                context_store=store,
                programming_bank=ProgrammingQuestionBank(),
                performance_monitor=perf,
                executor=fake_executor_echo_hello,
            ),
        )

        app.dependency_overrides[get_agent_registry] = lambda: registry
        app.dependency_overrides[get_programming_test_agent] = lambda: registry.get_agent(
            Intent.PROGRAMMING_TEST
        )
        app.dependency_overrides[get_performance_monitor] = lambda: perf

        client = TestClient(app)
        return client, store, perf

    def test_programming_test_start_and_submit_updates_performance(self):
        client, store, perf = self._make_client_and_store()
        user_id = "user-prog-1"
        session_id = "sess-prog-1"

        # Start programming test
        r_start = client.post(
            "/api/v1/assessment/programming-test/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "math"},
        )
        assert r_start.status_code == 200
        data_start = r_start.json()
        assert data_start["success"] is True
        assert data_start.get("completed") is False
        assert "Programming test started" in data_start["content"]

        # Submit code (content doesn't matter for fake executor)
        r_submit = client.post(
            "/api/v1/assessment/programming-test/submit",
            json={"session_id": session_id, "user_id": user_id, "code": "def f(x): return 'hello'"},
        )
        assert r_submit.status_code == 200
        data_submit = r_submit.json()
        assert data_submit["success"] is True
        assert data_submit.get("completed") is True
        meta = data_submit.get("metadata") or {}
        assert meta.get("result_type") == "programming_test"
        assert 0 <= meta.get("score", 0.0) <= 1
        assert data_submit.get("test_case_results") is not None
        assert isinstance(data_submit["test_case_results"], list)

        # Performance monitor should have recorded the result
        assert len(perf.logged_results) == 1
        logged = perf.logged_results[0]
        assert logged.type == "programming_test"
        assert logged.score == meta.get("score")

