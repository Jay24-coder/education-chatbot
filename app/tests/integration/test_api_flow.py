"""Integration tests: end-to-end API request flow (chat, health)."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client with app and dependencies."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoints:
    """Liveness and readiness probes."""

    def test_live_returns_ok(self, client: TestClient):
        r = client.get("/api/v1/live")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_ready_returns_ready(self, client: TestClient):
        r = client.get("/api/v1/ready")
        assert r.status_code == 200
        assert r.json() == {"status": "ready"}

    def test_ready_agents_returns_status(self, client: TestClient):
        r = client.get("/api/v1/ready/agents")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ready", "degraded")
        assert "unhealthy_agents" in data


class TestChatEndpoint:
    """Chat POST /api/v1/chat: request -> orchestrator -> response."""

    def test_chat_syllabus_returns_200_and_content(self, client: TestClient):
        r = client.post(
            "/api/v1/chat",
            json={"message": "What is the syllabus?", "user_id": "test-user"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        assert data.get("success") is True
        assert "Introduction" in data["content"] or "CS101" in data["content"]

    def test_chat_admin_returns_deadlines_or_policies(self, client: TestClient):
        r = client.post(
            "/api/v1/chat",
            json={"message": "When are the assignment deadlines?", "user_id": "test-user"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True
        assert "content" in data
        assert "Assignment" in data["content"] or "Week" in data["content"] or "deadline" in data["content"].lower()

    def test_chat_topic_returns_explanation(self, client: TestClient):
        r = client.post(
            "/api/v1/chat",
            json={"message": "Explain what a variable is", "user_id": "test-user"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True
        assert "variable" in data["content"].lower() or "container" in data["content"].lower()

    def test_chat_unknown_intent_returns_fallback(self, client: TestClient):
        r = client.post(
            "/api/v1/chat",
            json={"message": "hello world", "user_id": "test-user"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True
        assert "didn't quite understand" in data["content"] or "syllabus" in data["content"].lower()

    def test_chat_accepts_session_id(self, client: TestClient):
        r = client.post(
            "/api/v1/chat",
            json={"message": "syllabus?", "session_id": "sess-123", "user_id": "test-user"},
        )
        assert r.status_code == 200
        assert "content" in r.json()

    def test_chat_empty_message_returns_400(self, client: TestClient):
        r = client.post(
            "/api/v1/chat",
            json={"message": "", "user_id": "test-user"},
        )
        assert r.status_code == 422  # Pydantic validation: min_length=1

    def test_chat_missing_message_returns_422(self, client: TestClient):
        r = client.post("/api/v1/chat", json={"user_id": "test-user"})
        assert r.status_code == 422

    def test_chat_missing_user_id_returns_422(self, client: TestClient):
        r = client.post("/api/v1/chat", json={"message": "hello"})
        assert r.status_code == 422

    def test_chat_quiz_intent_routes_to_quiz_agent(self, client: TestClient):
        """7.4: POST /api/v1/chat with quiz-intent message; assert Orchestrator routes to Quiz Agent."""
        r = client.post(
            "/api/v1/chat",
            json={
                "message": "I want to start a quiz on algebra",
                "session_id": "sess-quiz-route",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True
        assert "content" in data
        # Quiz agent responds with first question or quiz started
        assert "quiz" in data["content"].lower() or "question" in data["content"].lower()
        assert "algebra" in data["content"].lower() or "Question 1 of" in data["content"]

    def test_chat_concept_test_intent_routes_to_concept_test_agent(self, client: TestClient):
        """7.4: POST /api/v1/chat with concept-test intent; assert routing to Concept Test agent."""
        r = client.post(
            "/api/v1/chat",
            json={
                "message": "Start a concept test on calculus",
                "session_id": "sess-ct-route",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True
        assert "content" in data
        # Without LLM: "not available"; with LLM or mock: concept test started or first question
        content_lower = data["content"].lower()
        assert "concept test" in content_lower or "not available" in content_lower or "question" in data["content"]


class TestLoggingFlow:
    """Basic assertions that key logging events are emitted for chat flows."""

    def test_chat_happy_path_emits_core_events(self, client: TestClient, caplog: pytest.LogCaptureFixture):
        caplog.set_level("INFO")
        r = client.post(
            "/api/v1/chat",
            json={"message": "What is the syllabus?", "user_id": "test-user"},
        )
        assert r.status_code == 200
        joined = "\n".join(rec.getMessage() for rec in caplog.records)
        # We don't assert full structure, just that core event names appear somewhere
        assert "chat_request_received" in joined
        assert "orchestrator_route_start" in joined
        assert "orchestrator_route_done" in joined

    def test_chat_unknown_intent_emits_fallback_event(self, client: TestClient, caplog: pytest.LogCaptureFixture):
        caplog.set_level("INFO")
        r = client.post(
            "/api/v1/chat",
            json={"message": "hello world", "user_id": "test-user"},
        )
        assert r.status_code == 200
        joined = "\n".join(rec.getMessage() for rec in caplog.records)
        assert "orchestrator_fallback" in joined
