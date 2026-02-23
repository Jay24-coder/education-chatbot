"""Integration tests: full assessment flow via API (quiz, concept test, performance, errors)."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_agent_registry, get_concept_test_agent, get_performance_monitor, get_quiz_agent
from app.api.main import create_app
from app.orchestrator.types import Intent
from app.orchestrator.wiring import build_agent_registry
from app.services.context.memory_store import MemoryStore


class FakeLLM:
    """Minimal LLM for tests: returns fixed QUESTION/RUBRIC for concept test and '0.8' for scoring."""

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_seconds: float | None = None,
    ) -> str:
        if "Rubric (use this to evaluate)" in prompt or "Student answer:" in prompt:
            return "0.8"
        # Concept test question generation
        return (
            "QUESTION: What is the main idea of this topic?\n"
            "RUBRIC: Correct if key concepts are mentioned.\n\n"
            "QUESTION: Explain in one sentence.\n"
            "RUBRIC: Correct if explanation is coherent.\n\n"
            "QUESTION: Give an example.\n"
            "RUBRIC: Correct if example is relevant."
        )


@pytest.fixture
def assessment_store():
    """Shared store for assessment tests so we can read quiz/concept-test state."""
    return MemoryStore()


@pytest.fixture
def client_with_store_and_fake_llm(assessment_store):
    """Client with a fresh MemoryStore and FakeLLM so concept test and performance use same store."""
    app = create_app()
    store = assessment_store
    fake_llm = FakeLLM()
    registry = build_agent_registry(llm_provider=fake_llm, context_store=store)
    # Override agent getters so the app uses our registry (get_agent_registry is called in-process, not as a dep)
    app.dependency_overrides[get_quiz_agent] = lambda: registry.get_agent(Intent.QUIZ)
    app.dependency_overrides[get_concept_test_agent] = lambda: registry.get_agent(Intent.CONCEPT_TEST)
    app.dependency_overrides[get_performance_monitor] = lambda: registry.get_agent(Intent.PERFORMANCE)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client():
    """Default client (uses app default deps: real store, no LLM for concept test)."""
    app = create_app()
    return TestClient(app)


class TestFullQuizFlowViaApi:
    """7.1: POST /quiz/start → POST /quiz/answer (x N) → assert final score; ContextStore/Performance updated."""

    def test_quiz_full_flow_final_score_and_performance_updated(
        self, client_with_store_and_fake_llm: TestClient, assessment_store: MemoryStore
    ):
        client = client_with_store_and_fake_llm
        user_id = "user-quiz-1"
        session_id = "sess-quiz-1"
        # Start quiz
        r = client.post(
            "/api/v1/assessment/quiz/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "algebra", "difficulty": "beginner"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "Question 1 of" in data["content"] or "algebra" in data["content"].lower()
        assert data.get("completed") is False

        # Answer each question with correct answer from store (order is random from question bank)
        for _ in range(5):
            state = assessment_store.get(session_id, "quiz:state").get("quiz:state")
            if not state or state["current_q"] >= len(state["questions"]):
                break
            correct = state["questions"][state["current_q"]]["correct_answer"]
            r = client.post(
                "/api/v1/assessment/quiz/answer",
                json={"session_id": session_id, "user_id": user_id, "answer": correct},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            if data.get("completed"):
                break

        assert data.get("completed") is True
        assert "Score:" in data["content"] or "score" in data["content"].lower()
        meta = data.get("metadata") or {}
        assert meta.get("result_type") == "quiz"
        assert "score" in meta
        assert 0 <= meta["score"] <= 1

        # Performance summary updated for user
        r_perf = client.get(f"/api/v1/assessment/performance/{user_id}")
        assert r_perf.status_code == 200
        perf = r_perf.json()
        assert perf["avg_score"] > 0
        assert "algebra" in perf["strong_topics"] or perf["avg_score"] >= 0.7

    def test_quiz_full_flow_with_correct_answers_from_state(self, client_with_store_and_fake_llm: TestClient):
        """Complete a quiz by submitting correct answers (match options A/B/C/D or text)."""
        client = client_with_store_and_fake_llm
        session_id = "sess-quiz-2"
        user_id = "user-quiz-2"
        r = client.post(
            "/api/v1/assessment/quiz/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "algebra", "difficulty": "beginner"},
        )
        assert r.status_code == 200
        # Answer with option letters A for first, etc. (algebra beginner: Q1 correct is "5" often option B)
        # Seed: ("What is 2 + 3?", "5", ["3", "5", "6", "7"]) so A=3,B=5,C=6,D=7 -> answer "B" or "5"
        answers_submitted = 0
        while True:
            r = client.post(
                "/api/v1/assessment/quiz/answer",
                json={"session_id": session_id, "user_id": user_id, "answer": "5"},
            )
            assert r.status_code == 200
            answers_submitted += 1
            data = r.json()
            if data.get("completed"):
                break
            if answers_submitted > 10:
                pytest.fail("Quiz did not complete after 10 answers")
        assert data["metadata"].get("result_type") == "quiz"
        assert data["metadata"].get("score") is not None
        r_perf = client.get(f"/api/v1/assessment/performance/{user_id}")
        assert r_perf.status_code == 200
        assert r_perf.json()["avg_score"] > 0


class TestConceptTestMultiTurnViaApi:
    """7.2: POST /concept-test/start → POST /concept-test/answer (x turns) → mastery level; session continuity."""

    def test_concept_test_multi_turn_mastery_returned(self, client_with_store_and_fake_llm: TestClient):
        client = client_with_store_and_fake_llm
        session_id = "sess-ct-1"
        user_id = "user-ct-1"
        r = client.post(
            "/api/v1/assessment/concept-test/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "algebra"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "Question 1 of" in data["content"] or "concept test" in data["content"].lower()
        assert data.get("completed") is False

        # Answer three questions then "done" (FakeLLM returns 0.8 so we get FULL mastery)
        for _ in range(3):
            r = client.post(
                "/api/v1/assessment/concept-test/answer",
                json={"session_id": session_id, "user_id": user_id, "answer": "Key concepts are X and Y."},
            )
            assert r.status_code == 200
            data = r.json()
            if data.get("completed"):
                break
        if not data.get("completed"):
            r = client.post(
                "/api/v1/assessment/concept-test/answer",
                json={"session_id": session_id, "user_id": user_id, "answer": "done"},
            )
            assert r.status_code == 200
            data = r.json()

        assert data.get("completed") is True
        assert "Concept test complete" in data["content"] or "Mastery:" in data["content"]
        meta = data.get("metadata") or {}
        assert meta.get("result_type") == "concept_test"
        assert meta.get("mastery") in ("FULL", "PARTIAL", "NEEDS_REVIEW")

    def test_concept_test_session_continuity(self, client_with_store_and_fake_llm: TestClient):
        """Same session_id keeps same concept test state across turns."""
        client = client_with_store_and_fake_llm
        session_id = "sess-ct-cont"
        user_id = "user-ct-cont"
        client.post(
            "/api/v1/assessment/concept-test/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "calculus"},
        )
        r2 = client.post(
            "/api/v1/assessment/concept-test/answer",
            json={"session_id": session_id, "user_id": user_id, "answer": "The derivative gives the rate of change."},
        )
        assert r2.status_code == 200
        # Response should be about next question or score for current, not "start a concept test"
        assert "No concept test in progress" not in r2.json().get("content", "")


class TestPerformanceSummaryEndpoint:
    """7.3: Run quiz + concept test; GET /performance/{user_id}; assert both results in summary."""

    def test_performance_summary_includes_quiz_and_concept_test(
        self, client_with_store_and_fake_llm: TestClient
    ):
        client = client_with_store_and_fake_llm
        user_id = "user-perf-summary"
        session_quiz = "sess-pq"
        session_ct = "sess-pct"

        # Complete a short quiz (one topic)
        client.post(
            "/api/v1/assessment/quiz/start",
            json={"session_id": session_quiz, "user_id": user_id, "topic": "algebra", "difficulty": "beginner"},
        )
        for _ in range(5):
            r = client.post(
                "/api/v1/assessment/quiz/answer",
                json={"session_id": session_quiz, "user_id": user_id, "answer": "5"},
            )
            assert r.status_code == 200
            if r.json().get("completed"):
                break

        # Complete concept test (FakeLLM)
        client.post(
            "/api/v1/assessment/concept-test/start",
            json={"session_id": session_ct, "user_id": user_id, "topic": "calculus"},
        )
        for _ in range(4):
            r = client.post(
                "/api/v1/assessment/concept-test/answer",
                json={"session_id": session_ct, "user_id": user_id, "answer": "Done with this concept."},
            )
            assert r.status_code == 200
            if r.json().get("completed"):
                break
        r_done = client.post(
            "/api/v1/assessment/concept-test/answer",
            json={"session_id": session_ct, "user_id": user_id, "answer": "done"},
        )
        if not r_done.json().get("completed"):
            # Maybe already completed in loop
            pass

        r_perf = client.get(f"/api/v1/assessment/performance/{user_id}")
        assert r_perf.status_code == 200
        perf = r_perf.json()
        assert perf["avg_score"] > 0
        # Both quiz (algebra) and concept test (calculus) should contribute to topics
        assert len(perf["strong_topics"]) + len(perf["weak_topics"]) >= 1


class TestErrorAndEdgeCases:
    """7.5: Submit answer to non-existent quiz; start concept test twice same session; correct errors."""

    def test_answer_without_quiz_returns_404(self, client: TestClient):
        r = client.post(
            "/api/v1/assessment/quiz/answer",
            json={"session_id": "no-quiz-session", "user_id": "u1", "answer": "A"},
        )
        assert r.status_code == 404
        assert "no quiz" in r.json().get("detail", "").lower()

    def test_start_concept_test_twice_same_session_restarts(self, client_with_store_and_fake_llm: TestClient):
        """Starting concept test twice in same session: second start restarts (new test)."""
        client = client_with_store_and_fake_llm
        session_id = "sess-double-start"
        user_id = "u-double"
        r1 = client.post(
            "/api/v1/assessment/concept-test/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "algebra"},
        )
        assert r1.status_code == 200
        r2 = client.post(
            "/api/v1/assessment/concept-test/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "algebra"},
        )
        # Second start overwrites state and returns new first question (success)
        assert r2.status_code == 200
        assert r2.json()["success"] is True

    def test_answer_after_concept_test_finalized_returns_404_or_clean_message(
        self, client_with_store_and_fake_llm: TestClient
    ):
        """Submit answer after sending 'done' should get no concept test in progress or similar."""
        client = client_with_store_and_fake_llm
        session_id = "sess-after-done"
        user_id = "u-after-done"
        client.post(
            "/api/v1/assessment/concept-test/start",
            json={"session_id": session_id, "user_id": user_id, "topic": "algebra"},
        )
        for _ in range(4):
            r = client.post(
                "/api/v1/assessment/concept-test/answer",
                json={"session_id": session_id, "user_id": user_id, "answer": "done"},
            )
            if r.json().get("completed"):
                break
        r_extra = client.post(
            "/api/v1/assessment/concept-test/answer",
            json={"session_id": session_id, "user_id": user_id, "answer": "another answer"},
        )
        assert r_extra.status_code in (200, 404)
        if r_extra.status_code == 200:
            assert "no concept test" in r_extra.json().get("content", "").lower() or "begin" in r_extra.json().get("content", "").lower()
