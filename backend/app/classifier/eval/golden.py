"""
backend/app/classifier/eval/golden.py

Golden‑set replay test.
Pytest‑compatible: collects all entries from golden_expected.json,
runs prediction on each, asserts label identity and top-1 confidence
within 1e-6. Marked as @pytest.mark.golden for CI separation.
"""

import json
from pathlib import Path

import pytest

from backend.app.classifier.predictor import Predictor, get_predictor


# ---------------------------------------------------------------------------
# Paths relative to this file
# ---------------------------------------------------------------------------
GOLDEN_DIR = Path(__file__).resolve().parent / "golden_images"
EXPECTED_FILE = Path(__file__).resolve().parent / "golden_expected.json"
WEIGHTS_PATH = Path(__file__).resolve().parent.parent / "models" / "classifier.pt"


class GoldenDataError(RuntimeError):
    """Raised for missing or malformed golden test data."""


# ---------------------------------------------------------------------------
# Fixture (session‑scoped, loads predictor once)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def predictor() -> Predictor:
    """Return the singleton predictor, loading weights once per test session."""
    return get_predictor(WEIGHTS_PATH)


# ---------------------------------------------------------------------------
# Helper: load expected data (called once at collection time)
# ---------------------------------------------------------------------------
def load_expected():
    """Parse golden_expected.json. Raise GoldenDataError if missing or invalid."""
    if not EXPECTED_FILE.exists():
        raise GoldenDataError(f"Golden expected file not found: {EXPECTED_FILE}")

    with open(EXPECTED_FILE, "r") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as e:
            raise GoldenDataError(f"Golden expected JSON is invalid: {e}")

    if not isinstance(data, list):
        raise GoldenDataError("Golden expected JSON must be a list of entries.")
    return data


def read_golden_image_bytes(filename: str) -> bytes:
    """Return the raw bytes of a golden image, raising if missing."""
    path = GOLDEN_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Golden image not found: {path}")
    return path.read_bytes()


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------
@pytest.mark.golden
@pytest.mark.parametrize("entry", load_expected())
def test_golden_replay(predictor: Predictor, entry: dict) -> None:
    """
    For each golden image:
      - Predict label and confidence.
      - Assert predicted label matches expected label.
      - Assert confidence is within 1e-6 of the expected value
        (the model is deterministic; any deviation indicates a regression).
    """
    image_bytes = read_golden_image_bytes(entry["filename"])
    result = predictor.predict(image_bytes)

    # Label must be byte‑identical
    assert result.label == entry["expected_label"], (
        f"Label mismatch for {entry['filename']}: "
        f"expected '{entry['expected_label']}', got '{result.label}'"
    )

    # Deterministic confidence – tolerance 1e-6
    assert result.confidence == pytest.approx(entry["top1_confidence"], abs=1e-6), (
        f"Confidence mismatch for {entry['filename']}: "
        f"expected {entry['top1_confidence']}, got {result.confidence}"
    )