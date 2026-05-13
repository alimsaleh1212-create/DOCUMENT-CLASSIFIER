"""
backend/app/classifier/startup_checks.py

Refuse-to-start assertions for the classifier service.
Called both by the API lifespan and the inference worker.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

log = structlog.get_logger()


class ClassifierStartupError(RuntimeError):
    """Raised when any startup precondition fails. The caller should exit non-zero."""


def assert_weights_present(weights_path: Path) -> None:
    """Raise if the weights file does not exist."""
    if not weights_path.exists():
        log.error("startup_check.weights_missing", path=str(weights_path))
        raise ClassifierStartupError(f"Classifier weights not found: {weights_path}")


def _load_model_card(model_card_path: Path) -> Dict[str, Any]:
    """Load and return model card JSON, raising on missing or malformed file."""
    if not model_card_path.exists():
        log.error("startup_check.model_card_missing", path=str(model_card_path))
        raise ClassifierStartupError(f"Model card not found: {model_card_path}")
    try:
        with open(model_card_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error("startup_check.model_card_invalid", path=str(model_card_path), error=str(e))
        raise ClassifierStartupError(f"Model card is not valid JSON: {e}")


def assert_sha256_matches(weights_path: Path, model_card: Dict[str, Any]) -> None:
    """Raise if the SHA-256 of the weights differs from model card."""
    expected_sha = model_card.get("sha256")
    if not expected_sha:
        raise ClassifierStartupError("Model card is missing 'sha256' field")

    with open(weights_path, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()

    if actual_sha != expected_sha:
        log.error("startup_check.sha_mismatch",
                  expected=expected_sha,
                  actual=actual_sha)
        raise ClassifierStartupError(
            f"SHA-256 mismatch: expected {expected_sha}, computed {actual_sha}"
        )


def assert_threshold_met(model_card: Dict[str, Any], min_top1: float) -> None:
    """Raise if model card test top-1 is below the required minimum."""
    test_top1 = model_card.get("test_top1")
    if test_top1 is None:
        raise ClassifierStartupError("Model card is missing 'test_top1' field")

    if test_top1 < min_top1:
        log.error("startup_check.top1_below_threshold",
                  test_top1=test_top1,
                  min_top1=min_top1)
        raise ClassifierStartupError(
            f"Model top-1 ({test_top1}) below required threshold ({min_top1})"
        )


def run_all_startup_checks(
    weights_path: Optional[Path] = None,
    model_card_path: Optional[Path] = None,
    min_top1: Optional[float] = None,
) -> None:
    """
    Run all startup checks in order, using sensible defaults when arguments are None.

    Defaults:
        weights_path  -> ../models/classifier.pt
        model_card    -> ../models/model_card.json
        min_top1      -> 0.50
    """
    base = Path(__file__).resolve().parent / "models"

    weights_path = weights_path or base / "classifier.pt"
    model_card_path = model_card_path or base / "model_card.json"
    min_top1 = min_top1 if min_top1 is not None else 0.50

    log.info(
        "startup_checks.starting",
        weights=str(weights_path),
        model_card=str(model_card_path),
        min_top1=min_top1,
    )

    assert_weights_present(weights_path)

    # Load model card once and reuse
    model_card = _load_model_card(model_card_path)

    assert_sha256_matches(weights_path, model_card)
    assert_threshold_met(model_card, min_top1)

    log.info("startup_checks.passed")