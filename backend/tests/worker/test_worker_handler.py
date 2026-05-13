""" tests/worker/test_worker_handler.py """

from pathlib import Path

import pytest

from app.classifier.predictor import get_predictor
from tests.fakes.blob import FakeBlob
from tests.fakes.prediction_service import FakePredictionService

# Ensure repo root is in sys.path (pytest usually adds it)
from worker.handler import classify_job, inject_dependencies

SAMPLE_TIFF = Path(__file__).resolve().parent.parent / "fixtures" / "sample.tif"

@pytest.fixture
def fakes() -> tuple[FakeBlob, FakePredictionService]:
    blob = FakeBlob()
    service = FakePredictionService()
    predictor = get_predictor()
    inject_dependencies(predictor, blob, service, "test_model_version")
    # Put sample TIFF into blob
    blob.put("documents/batch1/doc1.tif", SAMPLE_TIFF.read_bytes())
    return blob, service

def test_classify_job_success(fakes: tuple[FakeBlob, FakePredictionService]) -> None:
    blob, service = fakes
    classify_job({
        "batch_id": "batch1",
        "document_id": "doc1",
        "blob_key": "documents/batch1/doc1.tif",
        "request_id": "req-123"
    })
    assert len(service.records) == 1
    record = service.records[0]
    assert record.label is not None
    assert record.model_version == "test_model_version"
    assert record.batch_id == "batch1"
    assert record.document_id == "doc1"
    assert record.latency_ms is not None
    assert record.latency_ms > 0
    print(f"\n[DEMO] Prediction Latency: {record.latency_ms:.2f}ms")

def test_classify_job_retries_on_blob_error(
    fakes: tuple[FakeBlob, FakePredictionService], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate blob failure -> retry, then success."""
    blob, service = fakes
    # Replace blob.get to fail once then succeed
    original_get = blob.get
    call_count = 0
    def failing_get(key: str) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("simulated")
        return original_get(key)
    monkeypatch.setattr(blob, "get", failing_get)

    classify_job({
        "batch_id": "batch1",
        "document_id": "doc1",
        "blob_key": "documents/batch1/doc1.tif",
        "request_id": "req-123"
    })
    assert len(service.records) == 1   # eventually recorded
