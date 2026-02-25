"""Visualization agent: diagrams (Mermaid) and graphs (chart spec)."""

import json
import re
from typing import Any, TYPE_CHECKING

from app.agents.base.base_agent import AbstractBaseAgent
from app.orchestrator.types import AgentRequest, AgentResponse, Intent

if TYPE_CHECKING:
    from app.services.llm.provider import LLMProvider

_SEP = "\n---\n"

# Fallback Mermaid when LLM unavailable or parsing fails
_FALLBACK_MERMAID = "flowchart LR\n  A[Request] --> B[Process]\n  B --> C[Response]"
_FALLBACK_DIAGRAM_EXPLANATION = "Generic flow: request flows to process, then to response. You can replace the nodes with your own labels."

# Fallback chart spec when LLM unavailable or parsing fails
_FALLBACK_CHART_SPEC: dict[str, Any] = {
    "type": "line",
    "title": "Sample chart",
    "labels": ["A", "B", "C"],
    "data": [10, 20, 15],
}
_FALLBACK_GRAPH_EXPLANATION = "Plot the horizontal axis (labels) vs vertical axis (data). Adjust labels and data to match your scenario."


def _infer_mode(message: str) -> str:
    """Infer whether the user wants a diagram (Mermaid) or graph (chart spec)."""
    msg = message.lower()
    # Diagram-like keywords first so "flowchart" / "sequence" map to diagram, not graph
    if any(kw in msg for kw in ["diagram", "flowchart", "flow", "sequence", "mermaid"]):
        return "diagram"
    if any(kw in msg for kw in ["graph", "plot", "chart", "bar", "line"]):
        return "graph"
    return "diagram"


def _parse_diagram_llm_response(raw: str) -> tuple[str, str]:
    """Split LLM response into explanation and Mermaid code. Returns (explanation, mermaid_code)."""
    raw = (raw or "").strip()
    if _SEP in raw:
        parts = raw.split(_SEP, 1)
        explanation = (parts[0] or "").strip()
        mermaid = (parts[1] or "").strip()
    else:
        explanation = ""
        mermaid = raw
    # Strip markdown code fences from mermaid if present
    mermaid = re.sub(r"^```\s*mermaid?\s*\n?", "", mermaid)
    mermaid = re.sub(r"\n?```\s*$", "", mermaid)
    mermaid = mermaid.strip()
    return explanation or "Diagram below.", mermaid or _FALLBACK_MERMAID


def _parse_graph_llm_response(raw: str) -> tuple[str, dict[str, Any] | str]:
    """Split LLM response into explanation and chart spec. Returns (explanation, chart_spec)."""
    raw = (raw or "").strip()
    if _SEP in raw:
        parts = raw.split(_SEP, 1)
        explanation = (parts[0] or "").strip()
        spec_str = (parts[1] or "").strip()
    else:
        explanation = ""
        spec_str = raw
    # Strip markdown code fences
    spec_str = re.sub(r"^```\s*json?\s*\n?", "", spec_str)
    spec_str = re.sub(r"\n?```\s*$", "", spec_str)
    spec_str = spec_str.strip()
    try:
        spec = json.loads(spec_str) if spec_str else _FALLBACK_CHART_SPEC
        if not isinstance(spec, dict):
            spec = _FALLBACK_CHART_SPEC
    except (json.JSONDecodeError, TypeError):
        spec = spec_str if spec_str else _FALLBACK_CHART_SPEC
    return explanation or "Chart spec in metadata.", spec


class VisualizationAgent(AbstractBaseAgent):
    """Agent for diagrams (Mermaid) and graphs (chart spec)."""

    def __init__(self, llm_provider: "LLMProvider | None" = None) -> None:
        super().__init__(agent_id="visualization", capabilities=[Intent.VISUALIZATION.value])
        self._llm = llm_provider

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Diagram: return a ```mermaid ... ``` block plus short explanation in content.
        Graph: return JSON-like chart spec in metadata and brief explanation in content.
        """
        message = (request.message or "").strip()
        if not message:
            content = (
                "You can ask me to draw or visualize concepts. For example:\n"
                "- \"Draw a diagram of a client-server architecture.\"\n"
                "- \"Plot a graph of study time versus test score.\""
            )
            return AgentResponse(
                content=content,
                agent_id=self.agent_id,
                success=True,
                metadata={"intent": Intent.VISUALIZATION.value, "correlation_id": request.correlation_id},
                error_message=None,
            )

        mode = _infer_mode(message)

        if self._llm is not None:
            try:
                if mode == "diagram":
                    prompt = (
                        "The student wants a diagram (Mermaid).\n"
                        "Student request:\n"
                        f"{message}\n\n"
                        "Reply with exactly two parts separated by a line containing only '---'.\n"
                        "First part: 1-2 sentence explanation of the diagram.\n"
                        "Second part: ONLY valid Mermaid diagram syntax (e.g. flowchart, sequenceDiagram), "
                        "no markdown code fences, no other text."
                    )
                    raw = await self._llm.complete(prompt, temperature=0.3)
                    explanation, mermaid_code = _parse_diagram_llm_response(raw or "")
                    content = f"{explanation}\n\n```mermaid\n{mermaid_code}\n```"
                    metadata = {
                        "intent": Intent.VISUALIZATION.value,
                        "mode": "diagram",
                        "mermaid": mermaid_code,
                        "correlation_id": request.correlation_id,
                    }
                else:
                    prompt = (
                        "The student wants a chart/graph.\n"
                        "Student request:\n"
                        f"{message}\n\n"
                        "Reply with exactly two parts separated by a line containing only '---'.\n"
                        "First part: 1-2 sentence explanation of the chart.\n"
                        "Second part: a JSON object only, with keys: type (e.g. bar, line), "
                        "title (string), labels (array of x-axis labels), data (array of numbers). "
                        "No markdown, no code fences."
                    )
                    raw = await self._llm.complete(prompt, temperature=0.3)
                    explanation, chart_spec = _parse_graph_llm_response(raw or "")
                    content = explanation
                    metadata = {
                        "intent": Intent.VISUALIZATION.value,
                        "mode": "graph",
                        "chart_spec": chart_spec,
                        "correlation_id": request.correlation_id,
                    }
            except Exception:
                if mode == "diagram":
                    content = f"{_FALLBACK_DIAGRAM_EXPLANATION}\n\n```mermaid\n{_FALLBACK_MERMAID}\n```"
                    metadata = {
                        "intent": Intent.VISUALIZATION.value,
                        "mode": "diagram",
                        "mermaid": _FALLBACK_MERMAID,
                        "correlation_id": request.correlation_id,
                    }
                else:
                    content = _FALLBACK_GRAPH_EXPLANATION
                    metadata = {
                        "intent": Intent.VISUALIZATION.value,
                        "mode": "graph",
                        "chart_spec": _FALLBACK_CHART_SPEC,
                        "correlation_id": request.correlation_id,
                    }
        else:
            if mode == "diagram":
                content = f"{_FALLBACK_DIAGRAM_EXPLANATION}\n\n```mermaid\n{_FALLBACK_MERMAID}\n```"
                metadata = {
                    "intent": Intent.VISUALIZATION.value,
                    "mode": "diagram",
                    "mermaid": _FALLBACK_MERMAID,
                    "correlation_id": request.correlation_id,
                }
            else:
                content = _FALLBACK_GRAPH_EXPLANATION
                metadata = {
                    "intent": Intent.VISUALIZATION.value,
                    "mode": "graph",
                    "chart_spec": _FALLBACK_CHART_SPEC,
                    "correlation_id": request.correlation_id,
                }

        return AgentResponse(
            content=content,
            agent_id=self.agent_id,
            success=True,
            metadata=metadata,
            error_message=None,
        )
