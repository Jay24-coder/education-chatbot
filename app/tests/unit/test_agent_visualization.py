"""Unit tests for VisualizationAgent: diagram (Mermaid) and graph (chart spec) with mocked LLM."""

import pytest

from app.agents.specialized.visualization_agent import (
    VisualizationAgent,
    _infer_mode,
    _parse_diagram_llm_response,
    _parse_graph_llm_response,
)
from app.orchestrator.types import AgentRequest, Intent


class TestInferMode:
    def test_diagram_keywords(self):
        assert _infer_mode("draw a diagram") == "diagram"
        assert _infer_mode("visualize the flow") == "diagram"
        assert _infer_mode("show me a flowchart") == "diagram"

    def test_graph_keywords(self):
        assert _infer_mode("plot a graph") == "graph"
        assert _infer_mode("chart of sales") == "graph"
        assert _infer_mode("bar chart") == "graph"
        assert _infer_mode("line graph") == "graph"


class TestParseDiagramLlmResponse:
    def test_separated_explanation_and_mermaid(self):
        raw = "This is the flow.\n---\nflowchart LR\n  A --> B"
        exp, mermaid = _parse_diagram_llm_response(raw)
        assert exp == "This is the flow."
        assert "flowchart" in mermaid
        assert "A --> B" in mermaid

    def test_strips_mermaid_fences(self):
        raw = "Explanation.\n---\n```mermaid\nflowchart LR\n  X --> Y\n```"
        exp, mermaid = _parse_diagram_llm_response(raw)
        assert "```" not in mermaid
        assert "flowchart" in mermaid


class TestParseGraphLlmResponse:
    def test_separated_explanation_and_json(self):
        raw = 'Trend over time.\n---\n{"type": "bar", "title": "T", "labels": ["a"], "data": [1]}'
        exp, spec = _parse_graph_llm_response(raw)
        assert exp == "Trend over time."
        assert isinstance(spec, dict)
        assert spec.get("type") == "bar"
        assert spec.get("labels") == ["a"]

    def test_invalid_json_returns_fallback_or_raw(self):
        raw = "Explanation.\n---\nnot json at all"
        exp, spec = _parse_graph_llm_response(raw)
        assert exp == "Explanation."
        assert spec == "not json at all"


@pytest.fixture
def mock_llm_diagram():
    """LLM that returns diagram-style response (explanation + Mermaid)."""

    class MockLLM:
        async def complete(self, prompt, *, model=None, temperature=0.3, timeout_seconds=None):
            return (
                "This diagram shows client-server flow.\n"
                "---\n"
                "sequenceDiagram\n  Client->>Server: request\n  Server->>Client: response"
            )

    return MockLLM()


@pytest.fixture
def mock_llm_graph():
    """LLM that returns graph-style response (explanation + JSON chart spec)."""

    class MockLLM:
        async def complete(self, prompt, *, model=None, temperature=0.3, timeout_seconds=None):
            return (
                "This chart shows the trend.\n"
                "---\n"
                '{"type": "line", "title": "Study time vs score", "labels": ["Week 1", "Week 2"], "data": [70, 85]}'
            )

    return MockLLM()


@pytest.fixture
def diagram_agent(mock_llm_diagram):
    return VisualizationAgent(llm_provider=mock_llm_diagram)


@pytest.fixture
def graph_agent(mock_llm_graph):
    return VisualizationAgent(llm_provider=mock_llm_graph)


class TestVisualizationAgentDiagram:
    @pytest.mark.asyncio
    async def test_diagram_request_returns_mermaid_block_and_explanation(self, diagram_agent):
        request = AgentRequest(
            message="draw a diagram of client-server",
            session_id=None,
            correlation_id=None,
            intent=Intent.VISUALIZATION,
            context={},
        )
        response = await diagram_agent.process_request(request)
        assert response.success is True
        assert response.agent_id == "visualization"
        assert "```mermaid" in response.content
        assert "sequenceDiagram" in response.content
        assert "client-server" in response.content.lower() or "flow" in response.content.lower()
        assert response.metadata.get("mode") == "diagram"
        assert "mermaid" in response.metadata
        assert "sequenceDiagram" in response.metadata["mermaid"]

    @pytest.mark.asyncio
    async def test_empty_message_returns_usage_guidance(self, diagram_agent):
        # Bypass Pydantic min_length=1 to test agent behavior for empty message
        request = AgentRequest.model_construct(
            message="",
            session_id=None,
            correlation_id=None,
            intent=Intent.VISUALIZATION,
            context={},
        )
        response = await diagram_agent.process_request(request)
        assert response.success is True
        assert "draw" in response.content.lower() or "visualize" in response.content.lower()


class TestVisualizationAgentGraph:
    @pytest.mark.asyncio
    async def test_graph_request_returns_chart_spec_in_metadata_and_explanation_in_content(
        self, graph_agent
    ):
        request = AgentRequest(
            message="plot a graph of study time vs test score",
            session_id=None,
            correlation_id=None,
            intent=Intent.VISUALIZATION,
            context={},
        )
        response = await graph_agent.process_request(request)
        assert response.success is True
        assert response.agent_id == "visualization"
        assert response.metadata.get("mode") == "graph"
        assert "chart_spec" in response.metadata
        spec = response.metadata["chart_spec"]
        assert isinstance(spec, dict)
        assert spec.get("type") == "line"
        assert "labels" in spec
        assert "data" in spec
        assert "trend" in response.content.lower() or "chart" in response.content.lower()


class TestVisualizationAgentNoLlm:
    @pytest.mark.asyncio
    async def test_diagram_without_llm_returns_fallback_mermaid(self):
        agent = VisualizationAgent(llm_provider=None)
        request = AgentRequest(
            message="draw a diagram",
            session_id=None,
            correlation_id=None,
            intent=Intent.VISUALIZATION,
            context={},
        )
        response = await agent.process_request(request)
        assert response.success is True
        assert "```mermaid" in response.content
        assert response.metadata.get("mode") == "diagram"
        assert "mermaid" in response.metadata

    @pytest.mark.asyncio
    async def test_graph_without_llm_returns_fallback_chart_spec(self):
        agent = VisualizationAgent(llm_provider=None)
        request = AgentRequest(
            message="plot a graph",
            session_id=None,
            correlation_id=None,
            intent=Intent.VISUALIZATION,
            context={},
        )
        response = await agent.process_request(request)
        assert response.success is True
        assert response.metadata.get("mode") == "graph"
        assert "chart_spec" in response.metadata
        assert isinstance(response.metadata["chart_spec"], dict)
