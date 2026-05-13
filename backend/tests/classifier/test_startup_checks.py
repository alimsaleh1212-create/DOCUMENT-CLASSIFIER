""" tests/classifier/test_startup_checks.py """

import pytest
import shutil
import tempfile
from pathlib import Path
import hashlib, json

from backend.app.classifier.startup_checks import (
    ClassifierStartupError,
    assert_weights_present,
    assert_sha256_matches,
    assert_threshold_met,
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
with open(REAL_MODEL_CARD_PATH, "r") as f:
    REAL_MODEL_CARD = json.load(f)


def test_assert_weights_present_ok():
    assert_weights_present(REAL_WEIGHTS)

def test_assert_weights_present_raises():
    with pytest.raises(ClassifierStartupError):
        assert_weights_present(Path("nonexistent.pt"))

def test_assert_sha256_matches_ok():
    assert_sha256_matches(REAL_WEIGHTS, REAL_MODEL_CARD)   # passes with real data

def test_assert_sha256_matches_raises():
    # Tamper one byte of the weights
    tmp = tempfile.NamedTemporaryFile(suffix=".pt", delete=False)
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

def test_assert_threshold_met_ok():
    assert_threshold_met(REAL_MODEL_CARD, min_top1=50.0)   # model has 80.2% -> passes

def test_assert_threshold_met_raises():
    # Set the threshold impossibly high so that the model fails
    with pytest.raises(ClassifierStartupError):
        assert_threshold_met(REAL_MODEL_CARD, min_top1=100.0)

def test_run_all_checks_success():
    run_all_startup_checks(REAL_WEIGHTS, REAL_MODEL_CARD_PATH, min_top1=50.0)