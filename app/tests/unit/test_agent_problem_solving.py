"""
Unit tests for ProblemSolvingAgent with OCR and LLM mocked.

Covers:
- Path where solution is withheld due to weak understanding (explain/similar, never SOLVE).
- Path where hints lead to solution (eventual strong understanding -> SOLVE, ALLOW_SOLVE).
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.specialized.problem_solving_agent import ProblemSolvingAgent
from app.orchestrator.types import AgentRequest, Intent
from app.services.context.memory_store import MemoryStore


# Fixed OCR result for all tests (no real image)
FAKE_PROBLEM_TEXT = "Solve for x: 2x + 3 = 7"


def _make_vision_result():
    from app.agents.shared_tools.vision import VisionResult
    return VisionResult(FAKE_PROBLEM_TEXT, hints={})


class MockLLM:
    """LLM that returns configurable responses for classify and fixed text for other calls."""

    def __init__(
        self,
        *,
        classification: str = "partial",
        topic_difficulty: str = "TOPIC: algebra\nDIFFICULTY: medium",
        probe_response: str = "What part would you like to try first?",
        action_response: str = "Here is a hint.",
    ):
        self.classification = classification
        self.topic_difficulty = topic_difficulty
        self.probe_response = probe_response
        self.action_response = action_response
        self._complete = AsyncMock(side_effect=self._complete_impl)

    async def _complete_impl(self, prompt: str, *, temperature=None, timeout_seconds=None, model=None):
        if "Rate their understanding" in prompt or "exactly one word: weak" in prompt:
            return self.classification
        if "TOPIC:" in prompt and "DIFFICULTY:" in prompt:
            return self.topic_difficulty
        if "probe question" in prompt or "assess their current understanding" in prompt:
            return self.probe_response
        return self.action_response

    async def complete(self, prompt: str, *, temperature=0.0, timeout_seconds=10.0, model=None):
        return await self._complete_impl(prompt, temperature=temperature, timeout_seconds=timeout_seconds, model=model)


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def session_id():
    return "test-session-ps"


@pytest.mark.asyncio
async def test_first_turn_with_image_returns_probe_and_saves_state(store, session_id):
    """First turn with image: OCR (mocked), coarse classify, probe; state saved."""
    with patch(
        "app.agents.specialized.problem_solving_agent.process_problem_image",
        return_value=_make_vision_result(),
    ):
        llm = MockLLM()
        agent = ProblemSolvingAgent(context_store=store, llm_provider=llm)
        request = AgentRequest(
            message="start",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={"image_bytes": b"fake-png-bytes"},
        )
        response = await agent.process_request(request)

    assert response.success is True
    assert response.agent_id == "problem_solving"
    assert "probe" in response.content.lower() or "first" in response.content.lower() or "try" in response.content.lower()
    assert response.metadata.get("action") == "probe"
    assert response.metadata.get("topic") == "algebra"
    assert response.metadata.get("difficulty") == "medium"

    # State persisted
    stored = store.get(session_id, "problem_solving:state")
    assert stored
    data = stored.get("problem_solving:state")
    assert data and data.get("problem_text") == FAKE_PROBLEM_TEXT
    assert data.get("guardrail", {}).get("stage") == "probe"


@pytest.mark.asyncio
async def test_weak_understanding_solution_withheld_stays_in_explain_or_similar(store, session_id):
    """Path where solution is withheld: weak understanding -> EXPLAIN_CONCEPT or SIMILAR_PROBLEM, never SOLVE."""
    with patch(
        "app.agents.specialized.problem_solving_agent.process_problem_image",
        return_value=_make_vision_result(),
    ):
        llm = MockLLM(classification="weak")
        agent = ProblemSolvingAgent(context_store=store, llm_provider=llm)

        # Turn 1: start with image -> probe
        r1 = await agent.process_request(AgentRequest(
            message="start",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={"image_bytes": b"fake"},
        ))
        assert r1.success is True

        # Turn 2: student gives wrong/weak answer -> should get explain or similar, not allow_solve
        r2 = await agent.process_request(AgentRequest(
            message="I don't know",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={},
        ))

    assert r2.success is True
    assert r2.metadata.get("stage") in ("explain_concept", "similar_problem")
    assert r2.metadata.get("action") in ("explain_concept", "give_similar_problem")
    assert r2.metadata.get("action") != "allow_solve"
    assert r2.metadata.get("stage") != "solve"


@pytest.mark.asyncio
async def test_hints_lead_to_solution_strong_understanding_progresses_to_solve(store, session_id):
    """Path where hints lead to solution: after strong understanding -> SOLVE, ALLOW_SOLVE."""
    with patch(
        "app.agents.specialized.problem_solving_agent.process_problem_image",
        return_value=_make_vision_result(),
    ):
        # LLM returns weak first, then strong (simulate student improving)
        call_count = [0]

        class SwitchingLLM(MockLLM):
            async def _complete_impl(self, prompt, *, temperature=None, timeout_seconds=None, model=None):
                if "Rate their understanding" in prompt or "exactly one word" in prompt:
                    call_count[0] += 1
                    return "weak" if call_count[0] == 1 else "strong"
                if "TOPIC:" in prompt:
                    return "TOPIC: algebra\nDIFFICULTY: easy"
                if "probe" in prompt or "assess" in prompt:
                    return "What would you like to try first?"
                return "Here is the key concept."

        llm = SwitchingLLM()
        agent = ProblemSolvingAgent(context_store=store, llm_provider=llm)

        # Turn 1: image -> probe
        r1 = await agent.process_request(AgentRequest(
            message="start",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={"image_bytes": b"fake"},
        ))
        assert r1.success is True

        # Turn 2: weak answer -> explain or similar
        r2 = await agent.process_request(AgentRequest(
            message="I'm confused",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={},
        ))
        assert r2.success is True
        assert r2.metadata.get("stage") != "solve"

        # Turn 3: strong answer -> SOLVE, ALLOW_SOLVE
        r3 = await agent.process_request(AgentRequest(
            message="x equals 2, because 2x = 4 so x = 2",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={},
        ))

    assert r3.success is True
    assert r3.metadata.get("stage") == "solve"
    assert r3.metadata.get("action") == "allow_solve"


@pytest.mark.asyncio
async def test_no_image_no_state_asks_for_problem(store):
    """Without image and no stored state, agent asks to share a problem."""
    agent = ProblemSolvingAgent(context_store=store, llm_provider=MockLLM())
    request = AgentRequest(
        message="help me",
        session_id="other-session",
        correlation_id=None,
        intent=Intent.PROBLEM_SOLVING,
        context={},
    )
    response = await agent.process_request(request)

    assert response.success is False
    assert "Share a problem" in response.content or "upload" in response.content.lower() or "image" in response.content.lower()


@pytest.mark.asyncio
async def test_subsequent_turn_empty_message_asks_for_reply(store, session_id):
    """Existing state but blank message (whitespace only after strip) -> ask for reply."""
    with patch(
        "app.agents.specialized.problem_solving_agent.process_problem_image",
        return_value=_make_vision_result(),
    ):
        agent = ProblemSolvingAgent(context_store=store, llm_provider=MockLLM())
        await agent.process_request(AgentRequest(
            message="start",
            session_id=session_id,
            correlation_id=None,
            intent=Intent.PROBLEM_SOLVING,
            context={"image_bytes": b"x"},
        ))
    # Message that strips to empty (agent strips in process_request)
    request = AgentRequest(
        message="   ",
        session_id=session_id,
        correlation_id=None,
        intent=Intent.PROBLEM_SOLVING,
        context={},
    )
    response = await agent.process_request(request)

    assert response.success is False
    assert "reply" in response.content.lower() or "thoughts" in response.content.lower()
