"""
worker/__main__.py

Boot script for the inference worker.
Run from the repo root: python -m backend.worker
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path (so that 'backend' and 'tests' are
# discoverable packages).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent   # DOCUMENT-CLASSIFIER
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Now we can safely import from the backend package and from tests/
# ---------------------------------------------------------------------------
import redis  # noqa: E402
import structlog  # noqa: E402
from rq import Worker  # noqa: E402

from app.classifier.predictor import get_predictor  # noqa: E402
from app.classifier.startup_checks import run_all_startup_checks  # noqa: E402
from worker.handler import inject_dependencies  # noqa: E402

# ---------------------------------------------------------------------------
# Structured logger
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
# Paths – all relative to repo root (no double‑nesting)
# ---------------------------------------------------------------------------
CLASSIFIER_DIR = _REPO_ROOT / "backend" / "app" / "classifier"
WEIGHTS_PATH = CLASSIFIER_DIR / "models" / "classifier.pt"
MODEL_CARD_PATH = CLASSIFIER_DIR / "models" / "model_card.json"

# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------
try:
    run_all_startup_checks(weights_path=WEIGHTS_PATH, model_card_path=MODEL_CARD_PATH)
except Exception as e:
    log.error("startup_checks.failed", error=str(e))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Predictor singleton
# ---------------------------------------------------------------------------
predictor = get_predictor(WEIGHTS_PATH)
log.info("predictor.loaded")

# ---------------------------------------------------------------------------
# Model version (from model card)
# ---------------------------------------------------------------------------
try:
    with open(MODEL_CARD_PATH) as f:
        model_card = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    log.error("model_card.read_error", error=str(e))
    sys.exit(1)

model_version = (
    f"{model_card['backbone']}_{model_card['weights_enum']}_"
    f"{model_card['freeze_policy']}_{model_card['sha256'][:8]}_"
    f"{model_card['trained_at']}"
)[:50]  # predictions.model_version is VARCHAR(50)
log.info("model_version", version=model_version)

# ---------------------------------------------------------------------------
# Blob & Prediction Service – real vs fake
# ---------------------------------------------------------------------------
use_fakes = os.getenv("WORKER_USE_FAKES") == "1"

if use_fakes:
    from tests.fakes.blob import FakeBlob
    blob = FakeBlob()
    log.info("blob.using_fake")
else:
    from app.config import Settings as _Settings  # noqa: PLC0415
    from app.infra.vault import VaultClient  # noqa: PLC0415
    from app.infra.worker_blob import WorkerBlob  # noqa: PLC0415
    _s = _Settings()
    _vault = VaultClient(_s.vault_addr, _s.vault_token)
    _ak, _sk = _vault.get_minio_credentials()
    blob = WorkerBlob(endpoint=_s.minio_endpoint, access_key=_ak, secret_key=_sk)
    log.info("blob.using_real_minio")

if use_fakes:
    from tests.fakes.prediction_service import FakePredictionService
    prediction_service = FakePredictionService()
    log.info("prediction_service.using_fake")
else:
    from app.infra.worker_prediction_service import WorkerPredictionService  # noqa: PLC0415
    prediction_service = WorkerPredictionService(postgres_dsn=_vault.get_postgres_dsn())
    log.info("prediction_service.using_real")

# ---------------------------------------------------------------------------
# Inject dependencies
# ---------------------------------------------------------------------------
try:
    inject_dependencies(predictor, blob, prediction_service, model_version)
    log.info("dependencies.injected")
except Exception as e:
    log.error("dependencies.injection_failed", error=str(e))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Start the RQ worker
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = redis.from_url(REDIS_URL)
QUEUE_NAME = "classify"

# torch.set_num_threads(1) prevents BLAS thread deadlocks when RQ forks a
# work-horse process — forking a multi-threaded PyTorch process causes
# the child to hang waiting on locks held by threads that no longer exist.
import torch as _torch
_torch.set_num_threads(1)

worker = Worker([QUEUE_NAME], connection=redis_conn)
log.info("worker.starting", queue=QUEUE_NAME, fakes=use_fakes)
worker.work()
