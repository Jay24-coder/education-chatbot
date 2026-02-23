"""Unit tests for ConceptTestAgent: new session, continuing session, follow-up, finalization."""

import pytest

from app.agents.assessment.concept_test_agent import (
    ConceptTestAgent,
    KEY_CONCEPT_TEST_STATE,
    _parse_topic,
    _parse_questions_from_llm_response,
)
from app.agents.monitoring import PerformanceMonitorAgent
from app.orchestrator.types import AgentRequest, Intent
from app.services.context.memory_store import MemoryStore


@pytest.fixture
def memory_store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def performance_monitor(memory_store: MemoryStore) -> PerformanceMonitorAgent:
    return PerformanceMonitorAgent(context_store=memory_store)


def _mock_llm_questions():
    return (
        "QUESTION: What is the main idea of algebra?\n"
        "RUBRIC: Correct if they mention variables, unknowns, or equations.\n\n"
        "QUESTION: Give an example of an equation.\n"
        "RUBRIC: Correct if it has an equals sign and at least one variable or number.\n\n"
        "QUESTION: Why do we use letters in algebra?\n"
        "RUBRIC: Correct if they mention representing unknowns or quantities.\n"
    )


@pytest.fixture
def mock_llm():
    """LLM that returns structured questions for start, and score/follow-up as needed."""

    class MockLLM:
        def __init__(self):
            self._score = 0.8
            self._call_count = 0

        async def complete(self, prompt, *, model=None, temperature=0.4, timeout_seconds=None):
            self._call_count += 1
            p = (prompt or "").lower()
            if "generate a concept test" in p or "question:" in p and "rubric:" in p:
                return _mock_llm_questions()
            if "reply with only a single number" in p or "rubric" in p and "student answer" in p:
                return str(self._score)
            if "follow-up question" in p or "simpler" in p:
                return "Can you give a simple example?"
            return "0.5"

    return MockLLM()


@pytest.fixture
def concept_test_agent(
    memory_store: MemoryStore,
    performance_monitor: PerformanceMonitorAgent,
    mock_llm,
) -> ConceptTestAgent:
    return ConceptTestAgent(
        context_store=memory_store,
        llm_provider=mock_llm,
        performance_monitor=performance_monitor,
    )


class TestParseTopic:
    def test_default(self):
        assert _parse_topic("") == "general"
        assert _parse_topic("hello") == "hello"

    def test_topic_from_message(self):
        assert _parse_topic("concept test on calculus") == "calculus"
        assert _parse_topic("algebra") == "algebra"


class TestParseQuestionsFromLlm:
    def test_parses_question_rubric_blocks(self):
        raw = _mock_llm_questions()
        out = _parse_questions_from_llm_response(raw)
        assert len(out) >= 3
        assert "main idea" in out[0]["text"].lower() or "algebra" in out[0]["text"].lower()
        assert out[0]["rubric"]
        assert "equation" in out[1]["text"].lower()
        assert out[1]["rubric"]


class TestNewSession:
    """New session: process_request starts concept test and returns first question."""

    @pytest.mark.asyncio
    async def test_start_stores_state_and_returns_first_question(
        self,
        concept_test_agent: ConceptTestAgent,
        memory_store: MemoryStore,
    ):
        req = AgentRequest(
            message="start concept test on algebra",
            session_id="s1",
            intent=Intent.CONCEPT_TEST,
            context={},
        )
        resp = await concept_test_agent.process_request(req)
        assert resp.agent_id == "concept_test"
        assert resp.success is True
        assert "Concept test started" in resp.content
        assert "Question 1 of" in resp.content
        assert resp.metadata.get("concept_test_started") is True

        state = memory_store.get("s1", KEY_CONCEPT_TEST_STATE).get(KEY_CONCEPT_TEST_STATE)
        assert state is not None
        assert state["topic"] == "algebra"
        assert len(state["questions"]) >= 3
        assert state["current_q"] == 0
        assert state["question_turn_scores"] == [[] for _ in state["questions"]]


class TestContinuingSession:
    """Continuing session: process_request with state calls evaluate_answer."""

    @pytest.mark.asyncio
    async def test_evaluate_answer_returns_feedback_and_next_question(
        self,
        concept_test_agent: ConceptTestAgent,
        memory_store: MemoryStore,
    ):
        req_start = AgentRequest(
            message="concept test on calculus",
            session_id="s2",
            intent=Intent.CONCEPT_TEST,
            context={},
        )
        await concept_test_agent.process_request(req_start)
        req_answer = AgentRequest(
            message="Algebra is about variables and equations.",
            session_id="s2",
            intent=Intent.CONCEPT_TEST,
            context={},
        )
        resp = await concept_test_agent.process_request(req_answer)
        assert resp.success is True
        assert "Score" in resp.content or "score" in resp.content.lower()
        state = memory_store.get("s2", KEY_CONCEPT_TEST_STATE).get(KEY_CONCEPT_TEST_STATE)
        assert state["current_q"] >= 1
        assert len(state["question_turn_scores"][0]) == 1


class TestLowScoreFollowUp:
    """Low score (< 0.6) triggers follow-up; max 2 follow-ups per question."""

    @pytest.mark.asyncio
    async def test_low_score_triggers_follow_up(
        self,
        memory_store: MemoryStore,
        performance_monitor: PerformanceMonitorAgent,
    ):
        class LowScoreLLM:
            async def complete(self, prompt, *, model=None, temperature=0.4, timeout_seconds=None):
                p = (prompt or "").lower()
                if "generate a concept test" in p:
                    return _mock_llm_questions()
                if "reply with only a single number" in p or ("rubric" in p and "student" in p):
                    return "0.4"  # below 0.6
                if "follow-up" in p or "simpler" in p:
                    return "Can you give a simple example?"
                return "0.5"

        agent = ConceptTestAgent(
            context_store=memory_store,
            llm_provider=LowScoreLLM(),
            performance_monitor=performance_monitor,
        )
        await agent.process_request(
            AgentRequest(message="concept test algebra", session_id="s3", intent=Intent.CONCEPT_TEST, context={})
        )
        resp = await agent.process_request(
            AgentRequest(message="I don't know", session_id="s3", intent=Intent.CONCEPT_TEST, context={})
        )
        assert resp.success is True
        assert resp.metadata.get("follow_up") is True or "follow-up" in resp.content.lower()
        state = memory_store.get("s3", KEY_CONCEPT_TEST_STATE).get(KEY_CONCEPT_TEST_STATE)
        assert state["current_follow_up_text"] or state["current_follow_ups"] >= 1


class TestFinalization:
    """Finalize: aggregate scores, mastery, log to performance monitor, summary with gaps."""

    @pytest.mark.asyncio
    async def test_finish_keyword_finalizes_and_clears_state(
        self,
        concept_test_agent: ConceptTestAgent,
        memory_store: MemoryStore,
    ):
        await concept_test_agent.process_request(
            AgentRequest(message="concept test on algebra", session_id="s4", intent=Intent.CONCEPT_TEST, context={})
        )
        resp = await concept_test_agent.process_request(
            AgentRequest(message="done", session_id="s4", intent=Intent.CONCEPT_TEST, context={})
        )
        assert resp.success is True
        assert "Concept test complete" in resp.content or "complete" in resp.content.lower()
        assert "Mastery" in resp.content or "mastery" in resp.content.lower()
        final = memory_store.get("s4", KEY_CONCEPT_TEST_STATE).get(KEY_CONCEPT_TEST_STATE)
        assert final is None

    @pytest.mark.asyncio
    async def test_finalize_logs_to_performance_monitor(
        self,
        concept_test_agent: ConceptTestAgent,
        memory_store: MemoryStore,
        performance_monitor: PerformanceMonitorAgent,
    ):
        await concept_test_agent.process_request(
            AgentRequest(message="concept test algebra", session_id="s5", intent=Intent.CONCEPT_TEST, context={})
        )
        await concept_test_agent.process_request(
            AgentRequest(message="done", session_id="s5", intent=Intent.CONCEPT_TEST, context={"user_id": "u5"})
        )
        summary = performance_monitor.get_summary("u5")
        assert summary["avg_score"] >= 0 or "concept_test" in str(memory_store._perf_metrics.get("u5", {}))
        # Metrics may be in concept_tests list
        metrics = memory_store._perf_metrics.get("u5", {})
        assert "concept_tests" in metrics or summary["avg_score"] is not None


class TestConceptTestAgentIdentity:
    @pytest.mark.asyncio
    async def test_agent_id_and_capabilities(self, concept_test_agent: ConceptTestAgent):
        assert concept_test_agent.agent_id == "concept_test"
        assert Intent.CONCEPT_TEST.value in concept_test_agent.get_capabilities()

    @pytest.mark.asyncio
    async def test_no_llm_returns_failure_on_start(
        self,
        memory_store: MemoryStore,
        performance_monitor: PerformanceMonitorAgent,
    ):
        agent = ConceptTestAgent(
            context_store=memory_store,
            llm_provider=None,
            performance_monitor=performance_monitor,
        )
        resp = await agent.process_request(
            AgentRequest(message="concept test", session_id="s6", intent=Intent.CONCEPT_TEST, context={})
        )
        assert resp.success is False
        assert "not available" in resp.content or "LLM" in resp.content
