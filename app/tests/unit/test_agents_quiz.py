"""Unit tests for QuizAgent: start, submit, scoring, finalize, adaptive difficulty."""

import pytest

from app.agents.assessment.quiz_agent import QuizAgent, _parse_topic_and_difficulty
from app.agents.monitoring import PerformanceMonitorAgent
from app.agents.shared_tools.question_bank import QuestionBank
from app.orchestrator.types import AgentRequest, Intent
from app.services.context.memory_store import MemoryStore


@pytest.fixture
def memory_store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def performance_monitor(memory_store: MemoryStore) -> PerformanceMonitorAgent:
    return PerformanceMonitorAgent(context_store=memory_store)


@pytest.fixture
def quiz_agent(
    memory_store: MemoryStore,
    performance_monitor: PerformanceMonitorAgent,
) -> QuizAgent:
    return QuizAgent(
        context_store=memory_store,
        question_bank=QuestionBank(),
        performance_monitor=performance_monitor,
    )


class TestParseTopicAndDifficulty:
    def test_defaults(self):
        topic, diff = _parse_topic_and_difficulty("hello")
        assert topic == "algebra"
        assert diff == "beginner"

    def test_topic_in_message(self):
        topic, _ = _parse_topic_and_difficulty("quiz on calculus")
        assert topic == "calculus"
        topic, _ = _parse_topic_and_difficulty("kinematics")
        assert topic == "kinematics"

    def test_difficulty_in_message(self):
        _, diff = _parse_topic_and_difficulty("intermediate quiz")
        assert diff == "intermediate"
        _, diff = _parse_topic_and_difficulty("advanced algebra")
        assert diff == "advanced"


class TestQuizStart:
    """Test start_quiz: state stored, first question returned."""

    @pytest.mark.asyncio
    async def test_start_quiz_returns_first_question(self, quiz_agent: QuizAgent):
        req = AgentRequest(
            message="start a quiz on algebra",
            session_id="s1",
            intent=Intent.QUIZ,
            context={},
        )
        resp = await quiz_agent.process_request(req)
        assert resp.agent_id == "quiz"
        assert resp.success is True
        assert "Quiz started" in resp.content
        assert "Question 1 of" in resp.content
        assert "algebra" in resp.content.lower()
        assert resp.metadata.get("quiz_started") is True

    @pytest.mark.asyncio
    async def test_start_quiz_stores_state(self, quiz_agent: QuizAgent, memory_store: MemoryStore):
        req = AgentRequest(message="quiz on calculus beginner", session_id="s2", intent=Intent.QUIZ, context={})
        await quiz_agent.process_request(req)
        state = memory_store.get("s2", "quiz:state").get("quiz:state")
        assert state is not None
        assert state["topic"] == "calculus"
        assert state["difficulty"] == "beginner"
        assert len(state["questions"]) <= 5
        assert state["current_q"] == 0
        assert state["answers"] == []


class TestSubmitAnswerAndScoring:
    """Test submit_answer: scoring, feedback, advance to next or finalize."""

    @pytest.mark.asyncio
    async def test_submit_correct_answer_returns_feedback_and_next(
        self, quiz_agent: QuizAgent, memory_store: MemoryStore
    ):
        req_start = AgentRequest(
            message="start quiz on algebra",
            session_id="s3",
            intent=Intent.QUIZ,
            context={},
        )
        await quiz_agent.process_request(req_start)
        state = memory_store.get("s3", "quiz:state").get("quiz:state")
        first_correct = state["questions"][0]["correct_answer"]

        req_submit = AgentRequest(
            message=first_correct,
            session_id="s3",
            intent=Intent.QUIZ,
            context={},
        )
        resp = await quiz_agent.submit_answer("s3", req_submit.message, {})
        assert resp.success is True
        assert "Correct" in resp.content or "correct" in resp.content.lower()
        assert "Question 2 of" in resp.content
        state2 = memory_store.get("s3", "quiz:state").get("quiz:state")
        assert len(state2["answers"]) == 1
        assert state2["answers"][0]["score"] == 1.0

    @pytest.mark.asyncio
    async def test_submit_wrong_answer_scores_zero(self, quiz_agent: QuizAgent, memory_store: MemoryStore):
        await quiz_agent.start_quiz("s4", "quiz algebra", {})
        resp = await quiz_agent.submit_answer("s4", "wrong answer", {})
        assert resp.success is True
        state = memory_store.get("s4", "quiz:state").get("quiz:state")
        assert state["answers"][0]["score"] == 0.0


class TestFinalizeQuiz:
    """Test finalize_quiz: score logged to Performance Monitor, breakdown returned."""

    @pytest.mark.asyncio
    async def test_finalize_logs_to_performance_monitor(
        self, quiz_agent: QuizAgent, memory_store: MemoryStore, performance_monitor: PerformanceMonitorAgent
    ):
        await quiz_agent.start_quiz("s5", "start quiz algebra", {})
        for _ in range(6):  # up to 5 questions then finalize
            state = memory_store.get("s5", "quiz:state").get("quiz:state")
            if not state:
                break
            q = state["questions"][state["current_q"]]
            await quiz_agent.submit_answer("s5", q["correct_answer"], {"user_id": "u5"})
        summary = performance_monitor.get_summary("u5")
        assert summary["avg_score"] > 0
        assert "algebra" in summary["strong_topics"]

    @pytest.mark.asyncio
    async def test_finalize_returns_breakdown_and_clears_state(self, quiz_agent: QuizAgent, memory_store: MemoryStore):
        await quiz_agent.start_quiz("s6", "quiz algebra", {})
        resp = None
        while True:
            state = memory_store.get("s6", "quiz:state").get("quiz:state")
            if not state or state["current_q"] >= len(state["questions"]):
                break
            q = state["questions"][state["current_q"]]
            resp = await quiz_agent.submit_answer("s6", q["correct_answer"], {})
        assert resp is not None
        assert "Quiz complete" in resp.content
        assert "Score:" in resp.content or "score" in resp.content.lower()
        assert "Per-question" in resp.content or "breakdown" in resp.content.lower()
        final_state = memory_store.get("s6", "quiz:state").get("quiz:state")
        assert final_state is None


class TestAdaptiveDifficulty:
    """Test adaptive difficulty: 2 consecutive correct → suggest harder; 2 wrong → suggest easier."""

    @pytest.mark.asyncio
    async def test_two_consecutive_correct_raise_suggested_difficulty(
        self, quiz_agent: QuizAgent, memory_store: MemoryStore
    ):
        await quiz_agent.start_quiz("s7", "quiz algebra beginner", {})
        state = memory_store.get("s7", "quiz:state").get("quiz:state")
        # Answer first two correctly
        for i in range(2):
            q = state["questions"][state["current_q"]]
            await quiz_agent.submit_answer("s7", q["correct_answer"], {})
            state = memory_store.get("s7", "quiz:state").get("quiz:state")
        assert state["suggested_difficulty"] == "intermediate"

    @pytest.mark.asyncio
    async def test_two_consecutive_wrong_lower_suggested_difficulty(
        self, quiz_agent: QuizAgent, memory_store: MemoryStore
    ):
        await quiz_agent.start_quiz("s8", "quiz algebra intermediate", {})
        for _ in range(2):
            await quiz_agent.submit_answer("s8", "wrong", {})
        state = memory_store.get("s8", "quiz:state").get("quiz:state")
        assert state["suggested_difficulty"] == "beginner"

    @pytest.mark.asyncio
    async def test_four_consecutive_correct_escalate_difficulty(
        self, quiz_agent: QuizAgent, memory_store: MemoryStore
    ):
        """7.6: Simulate 4 correct answers; assert difficulty escalates (beginner → intermediate → advanced)."""
        await quiz_agent.start_quiz("s9", "quiz algebra beginner", {})
        state = memory_store.get("s9", "quiz:state").get("quiz:state")
        for _ in range(4):
            if state["current_q"] >= len(state["questions"]):
                break
            q = state["questions"][state["current_q"]]
            await quiz_agent.submit_answer("s9", q["correct_answer"], {})
            state = memory_store.get("s9", "quiz:state").get("quiz:state")
        # After 2 correct: intermediate; after 4 correct: advanced
        assert state["suggested_difficulty"] == "advanced"

    @pytest.mark.asyncio
    async def test_four_consecutive_wrong_drop_difficulty(
        self, quiz_agent: QuizAgent, memory_store: MemoryStore
    ):
        """7.6: Simulate 4 wrong answers; assert difficulty drops (e.g. intermediate → beginner)."""
        await quiz_agent.start_quiz("s10", "quiz algebra intermediate", {})
        for _ in range(4):
            await quiz_agent.submit_answer("s10", "wrong", {})
        state = memory_store.get("s10", "quiz:state").get("quiz:state")
        assert state["suggested_difficulty"] == "beginner"


class TestQuizAgentIdentity:
    @pytest.mark.asyncio
    async def test_agent_id_and_capabilities(self, quiz_agent: QuizAgent):
        assert quiz_agent.agent_id == "quiz"
        assert Intent.QUIZ.value in quiz_agent.get_capabilities()

    @pytest.mark.asyncio
    async def test_health_check(self, quiz_agent: QuizAgent):
        assert quiz_agent.health_check() is True
