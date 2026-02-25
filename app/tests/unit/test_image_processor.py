"""
Unit tests for image processing (OCR plumbing and error handling).

Uses a mock vision provider to verify process_problem_image delegates correctly
and that bad inputs fail gracefully. Optional test with a small synthetic image
verifies real OCR plumbing when Pillow and pytesseract are available.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agents.problem_solving.image_processor import process_problem_image
from app.agents.shared_tools.vision import (
    VisionError,
    VisionResult,
    extract_text,
    set_default_provider,
)


class StubVisionProvider:
    """Stub provider: returns fixed result for valid input, raises for invalid."""

    def __init__(self, valid_result: VisionResult | None = None, raise_for_bytes: bytes | None = None):
        self.valid_result = valid_result or VisionResult("stub text", hints={"stub": True})
        self.raise_for_bytes = raise_for_bytes  # if image bytes equals this, raise

    def extract(self, image: bytes | Path) -> VisionResult:
        if self.raise_for_bytes is not None and image == self.raise_for_bytes:
            raise VisionError("Stub: bad image bytes")
        if isinstance(image, Path) and not image.exists():
            raise VisionError("Stub: path does not exist")
        return self.valid_result


@pytest.fixture(autouse=True)
def reset_default_provider():
    """Reset default provider after each test so stubs don't leak."""
    yield
    set_default_provider(None)


def test_process_problem_image_with_mock_provider_returns_vision_result():
    """process_problem_image delegates to provider and returns VisionResult."""
    result = VisionResult("Hello from OCR", hints={"confidence_mean": 90.0})
    provider = StubVisionProvider(valid_result=result)

    out = process_problem_image(b"fake image bytes", provider=provider)

    assert out.text == "Hello from OCR"
    assert out.hints == {"confidence_mean": 90.0}


def test_process_problem_image_with_path_passes_path_to_provider():
    """When given a Path, process_problem_image passes it to the provider."""
    result = VisionResult("path-based text")
    provider = MagicMock(spec=["extract"])
    provider.extract.return_value = result
    path = Path("/some/image.png")

    out = process_problem_image(path, provider=provider)

    provider.extract.assert_called_once_with(path)
    assert out.text == "path-based text"


def test_process_problem_image_bad_image_bytes_raises_vision_error():
    """Bad image bytes cause the provider to raise; error propagates gracefully."""
    bad_bytes = b"not an image"
    provider = StubVisionProvider(raise_for_bytes=bad_bytes)

    with pytest.raises(VisionError, match="bad image bytes"):
        process_problem_image(bad_bytes, provider=provider)


def test_process_problem_image_nonexistent_path_raises():
    """Nonexistent file path leads to VisionError from provider (graceful failure)."""
    provider = StubVisionProvider()
    # Stub raises for path that does not exist
    nonexistent = Path("/nonexistent/image.png")
    assert not nonexistent.exists()

    with pytest.raises(VisionError, match="path does not exist"):
        process_problem_image(nonexistent, provider=provider)


def test_extract_text_with_stub_provider_returns_result():
    """Shared vision extract_text with stub provider returns result (OCR plumbing)."""
    result = VisionResult("extract_text result", hints={})
    provider = StubVisionProvider(valid_result=result)

    out = extract_text(b"any bytes", provider=provider)

    assert out.text == "extract_text result"


def test_vision_result_hints_default_empty():
    """VisionResult with no hints exposes empty dict for downstream."""
    r = VisionResult("text")
    assert r.text == "text"
    assert r.hints == {}


def test_vision_result_with_hints():
    """VisionResult stores optional hints (equations/symbols/confidence)."""
    r = VisionResult("x = 1", hints={"equations": ["x=1"], "confidence_mean": 85.0})
    assert r.text == "x = 1"
    assert r.hints["equations"] == ["x=1"]
    assert r.hints["confidence_mean"] == 85.0


def test_extract_text_synthetic_image_plumbing():
    """
    Real OCR plumbing: small synthetic image loads and runs through provider.
    Skips if Pillow/pytesseract are missing or Tesseract binary is not installed.
    """
    try:
        from PIL import Image
        import io
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (2, 2), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    try:
        from app.agents.shared_tools.vision import PytesseractVisionProvider

        provider = PytesseractVisionProvider()
        result = extract_text(image_bytes, provider=provider)
    except VisionError as e:
        pytest.skip(f"Vision provider unavailable (e.g. Tesseract not installed): {e}")

    assert isinstance(result, VisionResult)
    assert isinstance(result.text, str)
    assert isinstance(result.hints, dict)
    assert result.text is not None
