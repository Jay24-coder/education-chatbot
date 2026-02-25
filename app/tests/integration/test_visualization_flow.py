"""Integration tests for visualization: /visualization/generate and response formats."""

from fastapi.testclient import TestClient

from app.api.deps import get_visualization_agent
from app.api.main import create_app
from app.agents.specialized.visualization_agent import VisualizationAgent


class MockLLMDiagram:
    async def complete(self, prompt, *, model=None, temperature=0.3, timeout_seconds=None):
        return (
            "Client-server flow.\n"
            "---\n"
            "sequenceDiagram\n  Client->>Server: request\n  Server->>Client: response"
        )


class MockLLMGraph:
    async def complete(self, prompt, *, model=None, temperature=0.3, timeout_seconds=None):
        return (
            "Trend chart.\n"
            "---\n"
            '{"type": "line", "title": "Test", "labels": ["A", "B"], "data": [10, 20]}'
        )


def _make_client_with_visualization_agent(use_graph_mock: bool = False):
    app = create_app()
    mock_llm = MockLLMGraph() if use_graph_mock else MockLLMDiagram()
    viz_agent = VisualizationAgent(llm_provider=mock_llm)
    app.dependency_overrides[get_visualization_agent] = lambda: viz_agent
    return TestClient(app)


class TestVisualizationGenerateEndpoint:
    """Verify /visualization/generate returns correct formats for diagram and graph."""

    def test_generate_diagram_returns_mermaid_in_content_and_metadata(self):
        client = _make_client_with_visualization_agent(use_graph_mock=False)
        r = client.post(
            "/api/v1/visualization/generate",
            json={"description": "draw a diagram of client-server", "output_type": "diagram"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "content" in data
        assert "```mermaid" in data["content"]
        assert "sequenceDiagram" in data["content"]
        meta = data.get("metadata") or {}
        assert meta.get("mode") == "diagram"
        assert "mermaid" in meta
        assert "sequenceDiagram" in meta["mermaid"]

    def test_generate_graph_returns_chart_spec_in_metadata(self):
        client = _make_client_with_visualization_agent(use_graph_mock=True)
        r = client.post(
            "/api/v1/visualization/generate",
            json={"description": "plot a graph of scores", "output_type": "graph"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "content" in data
        meta = data.get("metadata") or {}
        assert meta.get("mode") == "graph"
        assert "chart_spec" in meta
        spec = meta["chart_spec"]
        assert isinstance(spec, dict)
        assert spec.get("type") == "line"
        assert "labels" in spec
        assert "data" in spec

    def test_generate_rejects_empty_description(self):
        client = _make_client_with_visualization_agent(use_graph_mock=False)
        r = client.post(
            "/api/v1/visualization/generate",
            json={"description": ""},
        )
        assert r.status_code == 422  # validation error
