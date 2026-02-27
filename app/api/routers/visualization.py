"""Visualization API: generate diagram (Mermaid) or graph (chart spec)."""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_visualization_agent
from app.api.schemas.v1.visualization import (
    VisualizationGenerateRequest,
    VisualizationGenerateResponse,
)
from app.observability.logging import get_logger
from app.orchestrator.types import AgentRequest, Intent

if TYPE_CHECKING:
    from app.agents.specialized.visualization_agent import VisualizationAgent

router = APIRouter(prefix="/visualization", tags=["visualization"])
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=VisualizationGenerateResponse,
    responses={
        400: {"description": "Invalid request"},
        503: {"description": "Visualization service unavailable"},
    },
)
async def generate_visualization(
    body: VisualizationGenerateRequest,
    visualization_agent: "VisualizationAgent | None" = Depends(get_visualization_agent),
) -> VisualizationGenerateResponse:
    """Generate a diagram (Mermaid) or graph (chart spec) from a description. Output type inferred if omitted."""
    logger.info(
        "visualization_generate_received",
        output_type=body.output_type or None,
    )
    if not body.description or not body.description.strip():
        raise HTTPException(status_code=400, detail="description is required")
    if visualization_agent is None:
        raise HTTPException(status_code=503, detail="Visualization service unavailable")

    message = body.description.strip()
    if body.output_type == "diagram":
        message = f"draw a diagram: {message}"
    elif body.output_type == "graph":
        message = f"plot a graph: {message}"

    request = AgentRequest(
        message=message,
        session_id=None,
        correlation_id=None,
        intent=Intent.VISUALIZATION,
        context={},
    )
    response = await visualization_agent.process_request(request)
    logger.info(
        "visualization_generate_done",
        output_type=body.output_type or None,
        success=response.success,
    )
    return VisualizationGenerateResponse(
        content=response.content,
        success=response.success,
        metadata=response.metadata or {},
    )
