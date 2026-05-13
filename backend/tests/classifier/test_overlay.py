""" tests/classifier/test_overlay.py """

from pathlib import Path

from backend.app.classifier.overlay import render_overlay

# Path to the tiny TIFF (goes up one level from classifier/ to tests/, then fixtures/)
SAMPLE_TIFF = Path(__file__).resolve().parent.parent / "fixtures" / "sample.tif"

def test_render_overlay_returns_bytes() -> None:
    img_bytes = SAMPLE_TIFF.read_bytes()
    result = render_overlay(img_bytes, "memo", 0.95)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_overlay_is_valid_png() -> None:
    img_bytes = SAMPLE_TIFF.read_bytes()
    result = render_overlay(img_bytes, "letter", 0.99)
    assert result[:8] == b'\x89PNG\r\n\x1a\n'
