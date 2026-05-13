""" tests/classifier/test_predictor.py """

import pytest
from pathlib import Path
from backend.app.classifier.predictor import get_predictor, PredictionOut

# Tiny fixture – lives in backend/tests/fixtures/sample.tif
SAMPLE_TIFF = Path(__file__).resolve().parent.parent / "fixtures" / "sample.tif"

@pytest.fixture(scope="module")
def predictor():
    """Load the predictor once for all tests in this module."""
    return get_predictor()

def test_predictor_returns_prediction_out(predictor):
    img_bytes = SAMPLE_TIFF.read_bytes()
    result = predictor.predict(img_bytes)
    assert isinstance(result, PredictionOut)
    assert result.label in predictor.CLASSES if hasattr(predictor, 'CLASSES') else True
    assert 0.0 <= result.confidence <= 1.0

def test_prediction_on_real_golden_image(predictor):
    # From backend/tests/classifier/ go up three levels to backend/
    # then follow app/classifier/eval/golden_images/
    golden_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "app" / "classifier" / "eval" / "golden_images"
    )
    img = sorted(golden_dir.glob("*.tif"))[0]
    result = predictor.predict(img.read_bytes())
    assert isinstance(result, PredictionOut)
    assert 0.0 <= result.confidence <= 1.0