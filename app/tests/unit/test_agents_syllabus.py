"""Unit tests for SyllabusAgent and syllabus helpers."""

import pytest

from app.agents.information.syllabus_agent import (
    SyllabusAgent,
    get_course_info,
    get_prerequisites,
    search_syllabus,
)
from app.orchestrator.types import AgentRequest, Intent


class TestSyllabusHelpers:
    """Tests for module-level syllabus functions (stub data)."""

    def test_get_course_info_returns_name_and_outline(self):
        out = get_course_info()
        assert "Introduction to Computer Science" in out
        assert "CS101" in out
        assert "Programming fundamentals" in out or "outline" in out.lower()
        assert "Variables" in out or "topics" in out.lower()

    def test_get_prerequisites_returns_prereqs(self):
        out = get_prerequisites()
        assert "prerequisite" in out.lower() or "Basic algebra" in out
        assert "CS101" in out or "Introduction" in out

    def test_search_syllabus_by_topic_keyword(self):
        out = search_syllabus("control flow")
        assert "control flow" in out.lower() or "Relevant syllabus" in out
        assert "Programming" in out or "outline" in out.lower()

    def test_search_syllabus_generic_syllabus_returns_course_info(self):
        out = search_syllabus("what is the syllabus")
        assert "Introduction" in out or "CS101" in out

    def test_search_syllabus_prerequisite_returns_prereqs(self):
        out = search_syllabus("prerequisites for this course")
        assert "prerequisite" in out.lower() or "algebra" in out


class TestSyllabusAgent:
    """Tests for SyllabusAgent process_request and protocol."""

    @pytest.mark.asyncio
    async def test_agent_id_and_capabilities(self, syllabus_agent: SyllabusAgent):
        assert syllabus_agent.agent_id == "syllabus"
        assert Intent.SYLLABUS.value in syllabus_agent.get_capabilities()

    @pytest.mark.asyncio
    async def test_health_check(self, syllabus_agent: SyllabusAgent):
        assert syllabus_agent.health_check() is True

    @pytest.mark.asyncio
    async def test_process_request_course_info(self, syllabus_agent: SyllabusAgent):
        req = AgentRequest(message="What is this course about?", intent=Intent.SYLLABUS)
        resp = await syllabus_agent.process_request(req)
        assert resp.agent_id == "syllabus"
        assert resp.success is True
        assert "Introduction" in resp.content or "CS101" in resp.content
        assert resp.metadata.get("intent") == Intent.SYLLABUS.value

    @pytest.mark.asyncio
    async def test_process_request_prerequisites(self, syllabus_agent: SyllabusAgent):
        req = AgentRequest(message="What are the prerequisites?", intent=Intent.SYLLABUS)
        resp = await syllabus_agent.process_request(req)
        assert resp.success is True
        assert "prerequisite" in resp.content.lower() or "algebra" in resp.content

    @pytest.mark.asyncio
    async def test_process_request_empty_message_returns_course_info(
        self, syllabus_agent: SyllabusAgent
    ):
        req = AgentRequest(message="x", intent=Intent.SYLLABUS)
        resp = await syllabus_agent.process_request(req)
        assert resp.success is True
        assert len(resp.content) > 0
