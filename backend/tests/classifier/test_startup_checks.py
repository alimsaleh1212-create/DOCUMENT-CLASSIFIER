""" tests/classifier/test_startup_checks.py """

import json
import tempfile
from pathlib import Path

import pytest

from backend.app.classifier.startup_checks import (
    ClassifierStartupError,
    assert_sha256_matches,
    assert_threshold_met,
    assert_weights_present,
    run_all_startup_checks,
)

# Base path: from backend/tests/classifier/ go up to backend/, then app/classifier/models/
MODEL_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "app" / "classifier" / "models"
)
REAL_WEIGHTS = MODEL_DIR / "classifier.pt"
REAL_MODEL_CARD_PATH = MODEL_DIR / "model_card.json"

# Load the model card once so we can pass the dict to the functions that expect it
with open(REAL_MODEL_CARD_PATH) as f:
    REAL_MODEL_CARD = json.load(f)


def test_assert_weights_present_ok() -> None:
    assert_weights_present(REAL_WEIGHTS)

def test_assert_weights_present_raises() -> None:
    with pytest.raises(ClassifierStartupError):
        assert_weights_present(Path("nonexistent.pt"))

def test_assert_sha256_matches_ok() -> None:
    assert_sha256_matches(REAL_WEIGHTS, REAL_MODEL_CARD)   # passes with real data

def test_assert_sha256_matches_raises() -> None:
    # Tamper one byte of the weights
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        with open(REAL_WEIGHTS, "rb") as f:
            data = bytearray(f.read())
            data[0] ^= 0xFF   # corrupt
        tmp.write(data)
        tmp.close()
        try:
            with pytest.raises(ClassifierStartupError):
                assert_sha256_matches(Path(tmp.name), REAL_MODEL_CARD)
        finally:
            Path(tmp.name).unlink()

def test_assert_threshold_met_ok() -> None:
    assert_threshold_met(REAL_MODEL_CARD, min_top1=50.0)   # model has 80.2% -> passes

def test_assert_threshold_met_raises() -> None:
    # Set the threshold impossibly high so that the model fails
    with pytest.raises(ClassifierStartupError):
        assert_threshold_met(REAL_MODEL_CARD, min_top1=100.0)

def test_run_all_checks_success() -> None:
    run_all_startup_checks(REAL_WEIGHTS, REAL_MODEL_CARD_PATH, min_top1=50.0)
