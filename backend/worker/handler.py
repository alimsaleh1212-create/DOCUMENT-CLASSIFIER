"""
worker/handler.py

RQ job handler for document classification.
Uses the official domain contracts from backend.app.domain.contracts.
"""

from typing import Protocol

import structlog
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.classifier.overlay import render_overlay

# Predictor and overlay (your modules)
from backend.app.classifier.predictor import Predictor

# Official contracts (from M2)
from backend.app.domain.contracts import (
    ClassifyJob,
    PredictionLabel,
    PredictionOut,
)

# ---------------------------------------------------------------------------
# Label mapping – predictor’s space‑based labels → PredictionLabel enum
# ---------------------------------------------------------------------------
LABEL_TO_ENUM = {
    "letter": PredictionLabel.letter,
    "form": PredictionLabel.form,
    "email": PredictionLabel.email,
    "handwritten": PredictionLabel.handwritten,
    "advertisement": PredictionLabel.advertisement,
    "scientific report": PredictionLabel.scientific_report,
    "scientific publication": PredictionLabel.scientific_publication,
    "specification": PredictionLabel.specification,
    "file folder": PredictionLabel.file_folder,
    "news article": PredictionLabel.news_article,
    "budget": PredictionLabel.budget,
    "invoice": PredictionLabel.invoice,
    "presentation": PredictionLabel.presentation,
    "questionnaire": PredictionLabel.questionnaire,
    "resume": PredictionLabel.resume,
    "memo": PredictionLabel.memo,
}

# ---------------------------------------------------------------------------
# Synchronous adapter interfaces (used in the synchronous RQ worker)
# ---------------------------------------------------------------------------
class IBlobStorage(Protocol):
    def get(self, key: str) -> bytes: ...
    def put(self, key: str, data: bytes) -> None: ...

class IPredictionService(Protocol):
    def record_prediction(self, record: PredictionOut) -> None: ...

# ---------------------------------------------------------------------------
# Handler entry point
# ---------------------------------------------------------------------------
log = structlog.get_logger()


def classify_job(payload: dict) -> None:
    """
    RQ entry point.

    1. Validate payload -> ClassifyJob
    2. Fetch TIFF from blob storage
    3. Predict top‑5 in a single inference call
    4. Render overlay PNG
    5. Upload overlay to blob
    6. Construct a full PredictionOut (with batch_id, model_version, etc.)
    7. Record prediction via IPredictionService
    8. Retry transient blob/network errors with exponential backoff
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
    predictor: Predictor = _dependencies.predictor
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
                # a) Fetch the original TIFF
                log_ctx.info("worker.fetching_document", blob_key=job.blob_key)
                image_bytes = blob.get(job.blob_key)

                # b) Single inference – top‑5
                log_ctx.info("worker.predicting")
                top5_list = predictor.predict_topk(image_bytes, k=5)

                # Extract top‑1
                top1_label_str, top1_conf = top5_list[0]

                # Map to PredictionLabel enum
                pred_label = LABEL_TO_ENUM[top1_label_str]
                top5_converted = [(LABEL_TO_ENUM[lbl], conf) for lbl, conf in top5_list]

                # c) Render overlay using the original label string
                overlay_bytes = render_overlay(image_bytes, top1_label_str, top1_conf)

                # d) Upload overlay
                overlay_key = f"overlays/{job.batch_id}/{job.document_id}.png"
                blob.put(overlay_key, overlay_bytes)
                log_ctx.info("worker.overlay_uploaded", overlay_key=overlay_key)

                # e) Build the official PredictionOut record.
                #    Fields `id` and `created_at` will be set by the database/service.
                #    As a temporary measure we leave them as placeholders – the contract
                #    in domain/contracts.py should be updated to allow None for these.
                prediction_record = PredictionOut(
                    id="",
                    batch_id=job.batch_id,
                    document_id=job.document_id,
                    label=pred_label,
                    top1_confidence=top1_conf,
                    top5=top5_converted,
                    overlay_url=overlay_key,
                    model_version=model_version,
                    created_at=None,   # ❗ will raise ValidationError until contract is fixed
                )
                prediction_service.record_prediction(prediction_record)
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
    def __init__(self) -> None:
        self.predictor = None
        self.blob: IBlobStorage | None = None
        self.prediction_service: IPredictionService | None = None
        self.model_version: str | None = None

_dependencies = _Dependencies()


def inject_dependencies(
    predictor: Predictor,
    blob: IBlobStorage,
    prediction_service: IPredictionService,
    model_version: str,
) -> None:
    """Called once at worker startup to inject the real / fake adapters."""
    _dependencies.predictor = predictor
    _dependencies.blob = blob
    _dependencies.prediction_service = prediction_service
    _dependencies.model_version = model_version
