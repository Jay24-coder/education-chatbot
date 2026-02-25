"""
OCR / vision utilities with a swappable provider abstraction.

Accept image (bytes or path) and return extracted text plus optional structured
hints (equations, symbols). Uses pytesseract + Pillow by default; the provider
interface allows mocking in tests and swapping to a cloud Vision API later.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Protocol, runtime_checkable

# Optional imports: allow running without tesseract installed (e.g. in CI without binary)
try:
    import pytesseract
    from PIL import Image
    _VISION_AVAILABLE = True
except ImportError:
    _VISION_AVAILABLE = False


class VisionError(Exception):
    """Raised when image cannot be processed or OCR fails."""


def _ensure_vision_available() -> None:
    if not _VISION_AVAILABLE:
        raise VisionError(
            "Vision dependencies (Pillow, pytesseract) are not installed. "
            "Install with: pip install Pillow pytesseract. "
            "Also ensure the Tesseract binary is installed on the system."
        )


@runtime_checkable
class VisionProvider(Protocol):
    """Protocol for OCR/vision backends. Implement this to swap providers (e.g. cloud API)."""

    def extract(self, image: bytes | Path) -> "VisionResult":
        """Extract text and optional structured hints from an image."""
        ...


class VisionResult:
    """
    Result of OCR/vision extraction: raw text plus optional structured hints.

    Structured hints can carry equation regions, symbol lists, or confidence
    metadata so downstream (e.g. problem-solving agent) can use them without
    tying to a specific OCR implementation.
    """

    __slots__ = ("text", "hints")

    def __init__(
        self,
        text: str,
        *,
        hints: dict | None = None,
    ) -> None:
        self.text = text
        self.hints = hints or {}

    def __repr__(self) -> str:
        return f"VisionResult(text={self.text!r}, hints={self.hints!r})"


def _load_image(image: bytes | Path) -> "Image.Image":
    _ensure_vision_available()
    if isinstance(image, Path):
        return Image.open(image).convert("RGB")
    return Image.open(io.BytesIO(image)).convert("RGB")


class PytesseractVisionProvider:
    """
    Vision provider using pytesseract and Pillow.

    Extracts plain text via Tesseract. Optionally adds minimal structured
    hints (e.g. confidence) from Tesseract data. For equation/symbol hints,
    a future implementation could use Tesseract config (e.g. equation mode)
    or a separate layer; this keeps the interface stable.
    """

    def __init__(self, lang: str = "eng", equation_mode: bool = False) -> None:
        _ensure_vision_available()
        self._lang = lang
        self._equation_mode = equation_mode

    def extract(self, image: bytes | Path) -> VisionResult:
        try:
            pil_image = _load_image(image)
        except Exception as exc:
            raise VisionError(f"Failed to load image: {exc}") from exc

        try:
            # Optional: pass config for equations/symbols (e.g. tessedit_char_whitelist)
            config = None
            if self._equation_mode:
                config = "--psm 6"  # Assume uniform block of text; adjust as needed

            raw = pytesseract.image_to_string(pil_image, lang=self._lang, config=config or "")
            text = (raw or "").strip()

            # Optional structured hints: include confidence if available (data API)
            hints: dict = {}
            try:
                data = pytesseract.image_to_data(pil_image, lang=self._lang, output_type=pytesseract.Output.DICT)
                confidences = [int(c) for c in data["conf"] if c != "-1"]
                if confidences:
                    hints["confidence_mean"] = sum(confidences) / len(confidences)
                    hints["confidence_min"] = min(confidences)
            except Exception:
                pass

            return VisionResult(text=text, hints=hints if hints else None)
        except pytesseract.TesseractError as exc:
            raise VisionError(f"OCR failed: {exc}") from exc


_default_provider: VisionProvider | None = None


def get_default_provider() -> VisionProvider:
    """Return the default vision provider (Pytesseract). Creates one on first use."""
    global _default_provider
    if _default_provider is None:
        _default_provider = PytesseractVisionProvider()
    return _default_provider


def set_default_provider(provider: VisionProvider | None) -> None:
    """Set the default provider. Pass None to reset to Pytesseract on next get."""
    global _default_provider
    _default_provider = provider


def extract_text(
    image: bytes | Path,
    *,
    provider: VisionProvider | None = None,
) -> VisionResult:
    """
    Extract text and optional structured hints from an image.

    Accepts either raw image bytes or a path to an image file. Uses the
    given provider or the default (Pytesseract). Clean separation allows
    tests to inject a mock provider and production to swap to a cloud API.
    """
    if provider is None:
        provider = get_default_provider()
    return provider.extract(image)
