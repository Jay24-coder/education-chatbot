"""Request/response models for the visualization API (v1)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class VisualizationGenerateRequest(BaseModel):
    """Request body for generating a visualization."""

    description: str = Field(..., min_length=1, description="What to draw or visualize")
    output_type: Literal["diagram", "graph"] | None = Field(
        default=None,
        description="Force diagram (Mermaid) or graph (chart spec); if omitted, inferred from description",
    )


class VisualizationGenerateResponse(BaseModel):
    """Response body for visualization generate."""

    content: str = Field(..., description="Explanation and/or Mermaid block (diagram) or brief explanation (graph)")
    success: bool = True
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Includes mode, and mermaid (diagram) or chart_spec (graph) when applicable",
    )
