"""
worker/__main__.py

Boot script for the inference worker.
Loads dependencies, runs startup checks, injects singletons
into the handler, and starts an RQ worker listening on the
'classify' queue.
"""

import os
import sys
import json
from pathlib import Path

import structlog
from rq import Worker, Connection
import redis

# ---------------------------------------------------------------------------
# 1. Structured logger
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()

# ---------------------------------------------------------------------------
# 2. Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # repo root
CLASSIFIER_DIR = BASE_DIR / "backend" / "app" / "classifier"
WEIGHTS_PATH = CLASSIFIER_DIR / "models" / "classifier.pt"
MODEL_CARD_PATH = CLASSIFIER_DIR / "models" / "model_card.json"

# ---------------------------------------------------------------------------
# 3. Startup checks – must pass before anything else
# ---------------------------------------------------------------------------
try:
    from backend.app.classifier.startup_checks import run_all_startup_checks
    run_all_startup_checks(weights_path=WEIGHTS_PATH, model_card_path=MODEL_CARD_PATH)
    # run_all_startup_checks already emits a success log; don’t duplicate.
except Exception as e:
    log.error("startup_checks.failed", error=str(e))
    sys.exit(1)

# ---------------------------------------------------------------------------
# 4. Predictor singleton
# ---------------------------------------------------------------------------
from backend.app.classifier.predictor import get_predictor
predictor = get_predictor(WEIGHTS_PATH)
log.info("predictor.loaded")

# ---------------------------------------------------------------------------
# 5. Model version (from model card) – re‑read because startup checks don’t expose it
# ---------------------------------------------------------------------------
try:
    with open(MODEL_CARD_PATH, "r") as f:
        model_card = json.load(f)
except (json.JSONDecodeError, IOError) as e:
    log.error("model_card.read_error", error=str(e))
    sys.exit(1)

# Construct a concise, unique version string for audit trails
model_version = (
    f"{model_card['backbone']}_{model_card['weights_enum']}_"
    f"{model_card['freeze_policy']}_{model_card['sha256'][:8]}_"
    f"{model_card['trained_at']}"
)
log.info("model_version", version=model_version)

# ---------------------------------------------------------------------------
# 6. Blob & Prediction Service – real vs fake, gated by env var
# ---------------------------------------------------------------------------
use_fakes = os.getenv("WORKER_USE_FAKES") == "1"

if use_fakes:
    from tests.fakes.blob import FakeBlob
    blob = FakeBlob()
    log.info("blob.using_fake")
else:
    # Will be implemented by M3
    raise NotImplementedError(
        "Real blob adapter not available yet. Set WORKER_USE_FAKES=1 to test with fake."
    )

if use_fakes:
    from tests.fakes.prediction_service import FakePredictionService
    prediction_service = FakePredictionService()
    log.info("prediction_service.using_fake")
else:
    raise NotImplementedError(
        "Real prediction service not available yet. Set WORKER_USE_FAKES=1 to test with fake."
    )

# ---------------------------------------------------------------------------
# 7. Inject dependencies into the handler
# ---------------------------------------------------------------------------
from worker.handler import inject_dependencies

try:
    inject_dependencies(predictor, blob, prediction_service, model_version)
    log.info("dependencies.injected")
except Exception as e:
    log.error("dependencies.injection_failed", error=str(e))
    sys.exit(1)

# ---------------------------------------------------------------------------
# 8. Start the RQ worker
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_conn = redis.from_url(REDIS_URL)
    QUEUE_NAME = "classify"

    with Connection(redis_conn):
        worker = Worker([QUEUE_NAME])
        log.info("worker.starting", queue=QUEUE_NAME, fakes=use_fakes)
        worker.work()