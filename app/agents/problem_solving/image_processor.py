"""
Image processor for the problem-solving agent.

Thin layer over shared vision utilities: accepts an image (bytes or path),
returns extracted text plus optional structured hints (equations, symbols).
Single responsibility: bridge problem-solving use case to the swappable
vision provider so agent logic stays testable and provider-agnostic.
"""

from __future__ import annotations

from pathlib import Path

from app.agents.shared_tools.vision import (
    VisionProvider,
    VisionResult,
    extract_text,
)


def process_problem_image(
    image: bytes | Path,
    *,
    provider: VisionProvider | None = None,
) -> VisionResult:
    """
    Process an image (e.g. student-uploaded problem) and return extracted text
    plus optional structured hints (equations, symbols, confidence).

    Accepts image as raw bytes or a path. Uses the given vision provider or
    the default (pytesseract + Pillow). Returns a VisionResult so callers can
    mock the provider in tests and swap to a cloud Vision API later without
    changing agent code.
    """
    return extract_text(image, provider=provider)
