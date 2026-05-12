"""
worker/handler.py

RQ job handler for document classification.
Called by the RQ worker for every ClassifyJob on the 'classify' queue.
"""

from typing import Optional, Protocol

import structlog
from pydantic import BaseModel, Field
from tenacity import (
    Retrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

# ---------------------------------------------------------------------------
# Shared contracts – keep in sync with backend.app.classifier.predictor
# ---------------------------------------------------------------------------
# Import PredictionOut from its canonical location to avoid duplication
from backend.app.classifier.predictor import PredictionOut
# Overlay renderer
from backend.app.classifier.overlay import render_overlay

# ---------------------------------------------------------------------------
# Job‑specific Pydantic models
# ---------------------------------------------------------------------------
class ClassifyJob(BaseModel):
    """Payload dropped onto the RQ queue."""
    batch_id: str
    document_id: str
    blob_key: str          # e.g. documents/{batch_id}/{document_id}.tif
    request_id: str

class PredictionRecord(BaseModel):
    """Complete prediction record sent to the prediction service."""
    label: str
    confidence: float
    batch_id: str
    document_id: str
    request_id: str
    model_version: str

# ---------------------------------------------------------------------------
# Synchronous adapter interfaces (used in a synchronous RQ worker)
# ---------------------------------------------------------------------------
class IBlobStorage(Protocol):
    def get(self, key: str) -> bytes: ...
    def put(self, key: str, data: bytes) -> None: ...

class IPredictionService(Protocol):
    def record_prediction(self, record: PredictionRecord) -> None: ...

# ---------------------------------------------------------------------------
# Handler entry point
# ---------------------------------------------------------------------------
log = structlog.get_logger()


def classify_job(payload: dict) -> None:
    """
    RQ entry point.

    1. Validate payload -> ClassifyJob.
    2. Fetch TIFF from blob storage.
    3. Run Predictor.predict.
    4. Render overlay PNG.
    5. Upload overlay.
    6. Record prediction via IPredictionService.
    7. Retry transient blob / network errors with exponential backoff.
    """

    # ---- 1. Validate at the boundary ---------------------------------------
    try:
        job = ClassifyJob(**payload)
    except Exception:
        log.exception("worker.invalid_payload", payload=payload)
        raise

    # ---- 2. Request‑scoped logging -----------------------------------------
    log_ctx = log.bind(
        request_id=job.request_id,
        batch_id=job.batch_id,
        document_id=job.document_id,
    )
    log_ctx.info("worker.job.started")

    # ---- 3. Obtain injected dependencies -----------------------------------
    predictor = _dependencies.predictor
    blob: IBlobStorage = _dependencies.blob
    prediction_service: IPredictionService = _dependencies.prediction_service
    model_version: str = _dependencies.model_version

    if None in (predictor, blob, prediction_service, model_version):
        log_ctx.error("worker.dependencies_missing")
        raise RuntimeError("Worker dependencies were not injected at startup")

    # ---- 4. Processing with retries ----------------------------------------
    try:
        for attempt in Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((OSError, ConnectionError, TimeoutError)),
            reraise=True,
        ):
            with attempt:
                # a) Fetch TIFF
                log_ctx.info("worker.fetching_document", blob_key=job.blob_key)
                image_bytes = blob.get(job.blob_key)          # synchronous

                # b) Inference (CPU, not retried)
                log_ctx.info("worker.predicting")
                prediction = predictor.predict(image_bytes)

                # c) Overlay (local, not retried)
                overlay_bytes = render_overlay(
                    image_bytes, prediction.label, prediction.confidence
                )

                # d) Upload overlay
                overlay_key = f"overlays/{job.batch_id}/{job.document_id}.png"
                blob.put(overlay_key, overlay_bytes)         # synchronous
                log_ctx.info("worker.overlay_uploaded", overlay_key=overlay_key)

                # e) Record prediction
                record = PredictionRecord(
                    label=prediction.label,
                    confidence=prediction.confidence,
                    batch_id=job.batch_id,
                    document_id=job.document_id,
                    request_id=job.request_id,
                    model_version=model_version,
                )
                prediction_service.record_prediction(record)  # synchronous
                log_ctx.info("worker.prediction_recorded")

    except RetryError:
        log_ctx.error("worker.retry_exhausted")
        raise
    except Exception:
        log_ctx.exception("worker.job.failed")
        raise

    log_ctx.info("worker.job.completed")


# ---------------------------------------------------------------------------
# Dependency injection container (set once at startup)
# ---------------------------------------------------------------------------
class _Dependencies:
    def __init__(self):
        self.predictor = None
        self.blob: Optional[IBlobStorage] = None
        self.prediction_service: Optional[IPredictionService] = None
        self.model_version: Optional[str] = None

_dependencies = _Dependencies()


def inject_dependencies(
    predictor,
    blob: IBlobStorage,
    prediction_service: IPredictionService,
    model_version: str,
) -> None:
    """Called once at worker startup to set the real / fake adapters."""
    _dependencies.predictor = predictor
    _dependencies.blob = blob
    _dependencies.prediction_service = prediction_service
    _dependencies.model_version = model_version