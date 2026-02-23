"""Unit tests for PerformanceMonitorAgent: log_result, get_summary, formatting, weak-topic detection."""

import pytest

from app.agents.monitoring.performance_monitor_agent import (
    PerformanceMonitorAgent,
    format_performance_response,
)
from app.orchestrator.types import AgentRequest, AssessmentResult, Intent
from app.services.context.memory_store import MemoryStore


@pytest.fixture
def memory_store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def performance_agent(memory_store: MemoryStore) -> PerformanceMonitorAgent:
    return PerformanceMonitorAgent(context_store=memory_store)


class TestLogResultAccumulation:
    """Test that log_result accumulates results and get_summary reflects them."""

    def test_log_result_stores_quiz_and_updates_summary(self, performance_agent: PerformanceMonitorAgent):
        performance_agent.log_result(
            "user1",
            AssessmentResult(
                user_id="user1",
                session_id="s1",
                type="quiz",
                topic="algebra",
                score=0.8,
                timestamp="2025-01-01T12:00:00",
            ),
        )
        summary = performance_agent.get_summary("user1")
        assert summary["avg_score"] == 0.8
        assert "algebra" in summary["strong_topics"]
        assert summary["weak_topics"] == []

    def test_log_result_accumulates_multiple(self, performance_agent: PerformanceMonitorAgent):
        performance_agent.log_result(
            "u2",
            AssessmentResult(user_id="u2", type="quiz", topic="physics", score=0.4),
        )
        performance_agent.log_result(
            "u2",
            AssessmentResult(user_id="u2", type="concept_test", topic="physics", score=0.3),
        )
        summary = performance_agent.get_summary("u2")
        # Recent 2: 0.4 and 0.3 -> avg 0.35; topic physics avg 0.35 < 0.5 → weak
        assert summary["avg_score"] == 0.35
        assert "physics" in summary["weak_topics"]


class TestSummaryFormatting:
    """Test format_performance_response produces human-readable text and flags weak topics."""

    def test_format_includes_avg_and_topics(self):
        summary = {
            "avg_score": 0.75,
            "weak_topics": ["algebra"],
            "strong_topics": ["physics"],
            "alert_flag": False,
        }
        text = format_performance_response(summary)
        assert "75%" in text or "0.75" in text
        assert "algebra" in text
        assert "physics" in text
        assert "Topics to review" in text or "review" in text.lower()
        assert "Strong topics" in text or "strong" in text.lower()

    def test_format_flags_weak_topics(self):
        summary = {
            "avg_score": 0.3,
            "weak_topics": ["calculus", "linear algebra"],
            "strong_topics": [],
            "alert_flag": True,
        }
        text = format_performance_response(summary)
        assert "calculus" in text
        assert "linear algebra" in text
        assert "Consider spending" in text or "review" in text.lower()

    def test_format_empty_data(self):
        summary = {"avg_score": 0.0, "weak_topics": [], "strong_topics": [], "alert_flag": False}
        text = format_performance_response(summary)
        assert "No assessment data" in text or "0%" in text


class TestWeakTopicDetection:
    """Test that weak-topic detection appears in get_summary and process_request."""

    def test_weak_topic_detection_via_log_result(self, performance_agent: PerformanceMonitorAgent):
        for _ in range(3):
            performance_agent.log_result(
                "u3",
                AssessmentResult(user_id="u3", type="quiz", topic="weak_topic", score=0.3),
            )
        summary = performance_agent.get_summary("u3")
        assert "weak_topic" in summary["weak_topics"]
        assert summary["avg_score"] == pytest.approx(0.3, rel=1e-5)

    def test_strong_topic_detection(self, performance_agent: PerformanceMonitorAgent):
        performance_agent.log_result(
            "u4",
            AssessmentResult(user_id="u4", type="quiz", topic="strong_topic", score=0.9),
        )
        summary = performance_agent.get_summary("u4")
        assert "strong_topic" in summary["strong_topics"]


class TestProcessRequest:
    """Test process_request for PERFORMANCE intent and orchestrator reachability."""

    @pytest.mark.asyncio
    async def test_process_request_returns_summary(self, performance_agent: PerformanceMonitorAgent):
        performance_agent.log_result(
            "u5",
            AssessmentResult(user_id="u5", type="quiz", topic="math", score=0.7),
        )
        req = AgentRequest(
            message="show my progress",
            session_id="s5",
            intent=Intent.PERFORMANCE,
            context={"user_id": "u5"},
        )
        resp = await performance_agent.process_request(req)
        assert resp.agent_id == "performance_monitor"
        assert resp.success is True
        assert "70%" in resp.content or "0.7" in resp.content or "math" in resp.content
        assert resp.metadata.get("intent") == Intent.PERFORMANCE.value

    @pytest.mark.asyncio
    async def test_process_request_uses_session_id_when_no_user_id(self, performance_agent: PerformanceMonitorAgent):
        req = AgentRequest(
            message="how am i doing",
            session_id="session-99",
            intent=Intent.PERFORMANCE,
            context={},
        )
        resp = await performance_agent.process_request(req)
        assert resp.success is True
        assert "No assessment data" in resp.content or "0%" in resp.content

    @pytest.mark.asyncio
    async def test_agent_id_and_capabilities(self, performance_agent: PerformanceMonitorAgent):
        assert performance_agent.agent_id == "performance_monitor"
        caps = performance_agent.get_capabilities()
        assert Intent.PERFORMANCE.value in caps
        assert Intent.ASSESSMENT.value in caps

    @pytest.mark.asyncio
    async def test_health_check(self, performance_agent: PerformanceMonitorAgent):
        assert performance_agent.health_check() is True
