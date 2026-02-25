"""
Integration tests for problem-solving flow: start with image (or stub), 2–3 turns, verify state progression.
"""

import base64
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_problem_solving_agent
from app.api.main import create_app
from app.agents.specialized.problem_solving_agent import ProblemSolvingAgent
from app.services.context.memory_store import MemoryStore


# Stub image bytes (real OCR is mocked)
STUB_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x02\x00\x00\x00\xfd\xd4\x9as\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
STUB_IMAGE_BASE64 = base64.b64encode(STUB_IMAGE_BYTES).decode("ascii")


class MockLLMIntegration:
    """LLM that returns fixed responses: first classify partial, second classify strong."""

    def __init__(self):
        self._classify_calls = 0

    async def complete(self, prompt: str, *, temperature=0.0, timeout_seconds=10.0, model=None):
        if "TOPIC:" in prompt and "DIFFICULTY:" in prompt:
            return "TOPIC: algebra\nDIFFICULTY: medium"
        if "Rate their understanding" in prompt or "exactly one word" in prompt:
            self._classify_calls += 1
            return "partial" if self._classify_calls == 1 else "strong"
        if "probe" in prompt or "assess their current" in prompt:
            return "What part of this problem would you like to tackle first?"
        return "Here is a hint to help you."


def _stub_vision_result():
    from app.agents.shared_tools.vision import VisionResult
    return VisionResult("Solve for x: 2x + 3 = 7", hints={})


class TestProblemSolvingFlow:
    """Start with test image (stub), simulate 2–3 turns, verify state progression."""

    def _make_client_and_agent(self):
        app = create_app()
        store = MemoryStore()
        llm = MockLLMIntegration()
        agent = ProblemSolvingAgent(context_store=store, llm_provider=llm)
        app.dependency_overrides[get_problem_solving_agent] = lambda: agent
        client = TestClient(app)
        return client, store, agent

    @patch("app.agents.specialized.problem_solving_agent.process_problem_image")
    def test_start_then_respond_turns_progression(self, mock_process_image):
        """Start with image stub; 2–3 respond turns; verify stage/action progression."""
        mock_process_image.return_value = _stub_vision_result()

        client, store, _ = self._make_client_and_agent()
        session_id = "int-session-ps-1"
        user_id = "user-ps-1"

        # Turn 1: start with image
        r_start = client.post(
            "/api/v1/problem-solving/start",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "image_base64": STUB_IMAGE_BASE64,
                "message": "start",
            },
        )
        assert r_start.status_code == 200
        data_start = r_start.json()
        assert data_start["success"] is True
        assert data_start.get("content")
        meta_start = data_start.get("metadata") or {}
        assert meta_start.get("action") == "probe"
        assert meta_start.get("topic") == "algebra"
        assert meta_start.get("difficulty") == "medium"

        # Stored state
        stored = store.get(session_id, "problem_solving:state")
        assert stored
        ps_data = stored.get("problem_solving:state")
        assert ps_data and ps_data.get("problem_text") == "Solve for x: 2x + 3 = 7"
        assert ps_data.get("guardrail", {}).get("stage") == "probe"

        # Turn 2: respond (partial understanding -> explain or similar)
        r2 = client.post(
            "/api/v1/problem-solving/respond",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "answer": "I think we need to isolate x",
            },
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["success"] is True
        meta2 = data2.get("metadata") or {}
        assert meta2.get("stage") in ("explain_concept", "similar_problem", "probe", "assess")
        assert meta2.get("action") in ("explain_concept", "give_similar_problem", "probe", "assess")

        # Turn 3: strong understanding (mock returns strong on second classify) -> SOLVE, ALLOW_SOLVE
        r3 = client.post(
            "/api/v1/problem-solving/respond",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "answer": "x = 2, because 2x = 4 so x = 2",
            },
        )
        assert r3.status_code == 200
        data3 = r3.json()
        assert data3["success"] is True
        meta3 = data3.get("metadata") or {}
        assert meta3.get("stage") == "solve"
        assert meta3.get("action") == "allow_solve"

    @patch("app.agents.specialized.problem_solving_agent.process_problem_image")
    def test_start_requires_session_id(self, mock_process_image):
        """Start without session_id returns 400."""
        mock_process_image.return_value = _stub_vision_result()
        client, _, _ = self._make_client_and_agent()

        r = client.post(
            "/api/v1/problem-solving/start",
            json={
                "session_id": "",
                "image_base64": STUB_IMAGE_BASE64,
            },
        )
        assert r.status_code == 400

    @patch("app.agents.specialized.problem_solving_agent.process_problem_image")
    def test_respond_requires_answer(self, mock_process_image):
        """Respond without answer returns 400."""
        mock_process_image.return_value = _stub_vision_result()
        client, _, _ = self._make_client_and_agent()

        r = client.post(
            "/api/v1/problem-solving/respond",
            json={
                "session_id": "any",
                "answer": "",
            },
        )
        assert r.status_code == 400  # Router validates answer required
