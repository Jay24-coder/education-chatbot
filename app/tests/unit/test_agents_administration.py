"""Unit tests for AdministrationAgent and admin helpers."""

import pytest

from app.agents.information.administration_agent import (
    AdministrationAgent,
    get_deadlines,
    get_policy,
    explain_procedure,
)
from app.orchestrator.types import AgentRequest, Intent


class TestAdministrationHelpers:
    """Tests for module-level administration functions."""

    def test_get_deadlines_returns_list(self):
        out = get_deadlines()
        assert "Deadlines" in out or "due" in out.lower()
        assert "Assignment" in out or "Week" in out

    def test_get_policy_attendance(self):
        out = get_policy("attendance")
        assert "Attendance" in out
        assert "80" in out or "80%" in out

    def test_get_policy_late_submission(self):
        out = get_policy("late")
        assert "Late" in out or "submission" in out.lower()
        assert "10" in out or "day" in out.lower()

    def test_explain_procedure_extension(self):
        out = explain_procedure("extension")
        assert "Extension" in out or "extension" in out.lower()
        assert "Email" in out or "instructor" in out.lower()

    def test_explain_procedure_unknown_returns_known_list(self):
        out = explain_procedure("unknown_xyz")
        assert "not found" in out.lower() or "Known" in out


class TestAdministrationAgent:
    """Tests for AdministrationAgent process_request and protocol."""

    @pytest.mark.asyncio
    async def test_agent_id_and_capabilities(self, administration_agent: AdministrationAgent):
        assert administration_agent.agent_id == "administration"
        assert Intent.ADMIN.value in administration_agent.get_capabilities()

    @pytest.mark.asyncio
    async def test_health_check(self, administration_agent: AdministrationAgent):
        assert administration_agent.health_check() is True

    @pytest.mark.asyncio
    async def test_process_request_deadlines(self, administration_agent: AdministrationAgent):
        req = AgentRequest(message="When are the assignment deadlines?", intent=Intent.ADMIN)
        resp = await administration_agent.process_request(req)
        assert resp.agent_id == "administration"
        assert resp.success is True
        assert "Assignment" in resp.content or "Week" in resp.content or "due" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_process_request_policy(self, administration_agent: AdministrationAgent):
        req = AgentRequest(message="What is the attendance policy?", intent=Intent.ADMIN)
        resp = await administration_agent.process_request(req)
        assert resp.success is True
        assert "Attendance" in resp.content or "80" in resp.content

    @pytest.mark.asyncio
    async def test_process_request_procedure(self, administration_agent: AdministrationAgent):
        req = AgentRequest(message="How do I request an extension?", intent=Intent.ADMIN)
        resp = await administration_agent.process_request(req)
        assert resp.success is True
        assert "Extension" in resp.content or "extension" in resp.content.lower()
