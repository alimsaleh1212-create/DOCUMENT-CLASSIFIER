# Member 1 — ML & Inference Vertical

You own the **classifier and the inference pipeline**. Your work is the substance behind the system; without your weights, the API has nothing to gate. Your vertical is end-to-end testable on your own machine and on Colab; you do not wait on M2 or M3 to ship.

> 📜 Read [shared_tasks.md](shared_tasks.md) first. Day-0 contracts (especially `ClassifyJob`, `PredictionOut`, `PredictionLabel`, the `IPredictionService` ABC, and the MinIO bucket layout) are your input. Do not start coding the worker until those are committed.

---

## What You Own

- `app/classifier/` — entire module: predictor, overlay generator, startup checks, golden-set assets.
- `worker/` — the RQ inference-worker container entrypoint.
- `app/classifier/models/classifier.pt` (git LFS) and `model_card.json`.
- `app/classifier/eval/` — `golden.py`, `golden_images/`, `golden_expected.json`.
- `tests/classifier/`, `tests/worker/`.
- One row in `DECISIONS.md` (choice of backbone + freeze policy + augmentation).
- One row in `RUNBOOK.md` (what to do if SHA mismatches or top-1 below threshold).
- The LICENSES.md row flagging RVL-CDIP academic use.

---

## Deliverables

### A. Training (on Colab — the full dataset never touches your laptop)
- [ ] Colab notebook in `notebooks/train_classifier.ipynb` (also exported as `.py` for diff-ability).
- [ ] Fine-tune `torchvision.models.convnext_tiny` (or `_small`) with `ConvNeXt_Tiny_Weights.DEFAULT` (or `_Small_`).
- [ ] Document and commit your freeze policy in the model card: `linear_probe | partial_unfreeze | full_fine_tune`.
- [ ] Train/val pipeline, mixed-precision OK, set `torch.manual_seed(...)` and log it in the model card.
- [ ] Evaluate on the **full 40k test split** — top-1, top-5, per-class accuracy, worst-class label.
- [ ] Pick **50 golden images** spanning all 16 classes, deliberately including easy + ambiguous cases. Record reasoning in `golden_expected.json` next to each entry.

### B. Artifacts that ship to the repo
- [ ] `app/classifier/models/classifier.pt` via git LFS (~110 MB Tiny / ~190 MB Small).
- [ ] `app/classifier/models/model_card.json`:
  ```json
  {
    "sha256": "<64-hex>",
    "backbone": "convnext_tiny",
    "weights_enum": "ConvNeXt_Tiny_Weights.IMAGENET1K_V1",
    "freeze_policy": "partial_unfreeze",
    "test_top1": 0.0,
    "test_top5": 0.0,
    "golden_top1": 0.0,
    "golden_top5": 0.0,
    "per_class_accuracy": {"letter": 0.0, "...": 0.0},
    "worst_class": ["...", 0.0],
    "env": {"python": "3.11.x", "torch": "2.x", "torchvision": "0.x", "cuda": "12.x"},
    "trained_at": "2026-05-...T...Z",
    "seed": 42
  }
  ```
- [ ] `app/classifier/eval/golden_images/` — the 50 TIFFs.
- [ ] `app/classifier/eval/golden_expected.json` — `[{ "filename": "...", "expected_label": "memo", "top1_confidence": 0.943, "note": "ambiguous between memo and letter" }, ...]`.

### C. Inference module — `app/classifier/`
- [ ] `predictor.py`:
  - `class Predictor` — built once via FastAPI lifespan (M2 instantiates and stashes on `app.state`).
  - Loads weights, runs `model.eval()`, wraps `model.predict()` calls in `torch.inference_mode()`.
  - Public API: `predict(image_bytes: bytes) -> PredictionOut` (from `app/domain/contracts.py`).
  - CPU-only inference; ensure p95 < 1.0 s on a modern dev laptop.
- [ ] `overlay.py`:
  - `render_overlay(image_bytes: bytes, label: PredictionLabel, confidence: float) -> bytes` — returns PNG bytes with a small banner/legend. Use PIL only.
- [ ] `startup_checks.py`:
  - `assert_weights_present(path)` — raises `ClassifierStartupError`.
  - `assert_sha256_matches(weights_path, model_card_path)` — raises.
  - `assert_threshold_met(model_card, min_top1)` — raises.
  - Called from the FastAPI lifespan **and** the worker `__main__`. If any check fails, exit non-zero before the server binds.
- [ ] `eval/golden.py`:
  - `pytest`-compatible. For each entry in `golden_expected.json`, run `Predictor.predict` and assert: label == expected, abs(confidence - expected) < 1e-6. Marked `@pytest.mark.golden` so CI runs it as a separate job.

### D. Inference worker — `worker/`
- [ ] `worker/__main__.py` — RQ entrypoint: connects to Redis (DSN from settings), listens on queue `classify` only.
- [ ] `worker/handler.py`:
  - Function `classify_job(payload: dict) -> None` — RQ calls this with the serialized `ClassifyJob`.
  - Reconstruct `ClassifyJob` via Pydantic (validate at the boundary).
  - Bind `request_id` into the structlog context for the whole job.
  - Fetch the TIFF from blob (`IBlobStorage` adapter, injected via DI module-level singleton — see Engineering Standards § 3).
  - Run `Predictor.predict`, render overlay, upload overlay PNG to MinIO under `overlays/{batch_id}/{document_id}.png`.
  - Call `IPredictionService.record_prediction(prediction, request_id=...)`.
  - Tenacity retries on transient `MinIOError`/`httpx.NetworkError` (3 attempts, exponential backoff). Non-transient errors → log + mark job failed.
- [ ] Refuse-to-start: import-time call to `startup_checks` set; if any fails, log JSON + `sys.exit(1)`.

### E. Tests — `tests/classifier/`, `tests/worker/`
- [ ] `test_predictor.py` — sample 3 small TIFFs (committed in `tests/fixtures/`), assert deterministic outputs.
- [ ] `test_overlay.py` — output is a valid PNG, dimensions match input.
- [ ] `test_startup_checks.py` — tamper a byte of the weights, assert SHA check fails; remove the file, assert missing-weights raises.
- [ ] `test_golden_replay.py` — wrapper that pytest-collects `eval/golden.py`.
- [ ] `test_worker_handler.py` — with `FakeBlob`, `FakePredictionService`, `FakeQueue`, end-to-end one job; assert prediction recorded, overlay bytes uploaded, retries on simulated MinIO outage.

---

## Independent Dev Path (No Teammates Required)

You do **not** need M2's API or M3's MinIO/Postgres to develop or test. Build against these stubs which live in `tests/fakes/` (or your branch until M3's adapters land):

```python
# tests/fakes/blob.py
class FakeBlob:
    def __init__(self): self.store: dict[str, bytes] = {}
    async def get(self, key): return self.store[key]
    async def put(self, key, data): self.store[key] = data

# tests/fakes/prediction_service.py
class FakePredictionService:
    def __init__(self): self.records: list[PredictionOut] = []
    async def record_prediction(self, p, request_id): self.records.append(p)
```

Run worker locally with `python -m worker` against a local Redis container (`docker run -p 6379:6379 redis:7`). Enqueue a `ClassifyJob` with a small RQ client script in `scripts/enqueue_local.py`.

---

## End-to-End Self-Test (You can demo this alone)

1. Boot local Redis: `docker run --rm -p 6379:6379 redis:7`.
2. Put a sample TIFF into `./fake_blob/documents/test_batch/doc_001.tif`.
3. Start worker: `python -m worker` (uses `FakeBlob` + `FakePredictionService` via env flag `WORKER_USE_FAKES=1`).
4. Enqueue: `python scripts/enqueue_local.py test_batch doc_001`.
5. Assert: `./fake_blob/overlays/test_batch/doc_001.png` exists; `FakePredictionService.records` is len 1 with the right label.
6. Run `pytest tests/classifier/ tests/worker/ -v` — all green.
7. Run `pytest -m golden` — all green.

If those six steps pass on a clean clone, your vertical is shippable.

---

## Friday-Readiness Checklist

You will be asked about your code AND your teammates'. For your own:

- [ ] Explain ConvNeXt at a one-paragraph level: depthwise convolution, layer norm, GELU.
- [ ] Defend your freeze policy: which layers, why, what would you change with more time.
- [ ] Defend your 50 golden images: how you picked them, why these ambiguities matter.
- [ ] Walk through `predict()` line by line, including `torch.inference_mode()` vs `no_grad()`.
- [ ] Show the SHA-256 check fires when you tamper a byte of `classifier.pt`.
- [ ] Answer: *worker dies mid-job, what happens?* (RQ + appendonly Redis = job stays in `started`, requeued after timeout; idempotency via `(batch_id, document_id)` upsert in prediction service).
- [ ] Answer: *MinIO is down, what happens?* (Tenacity retries 3× with backoff; after exhaustion the job is moved to the failed registry; an alert log line is emitted; nothing crashes the worker).
- [ ] Answer: *you ship a new model — how do you migrate without dropping in-flight jobs?* (Drain workers, swap `classifier.pt`, restart; `prediction_id` carries `model_version` so downstream knows which weights produced the row).

---

## What You Do NOT Touch

- API code in `app/api/` (M2).
- Service implementations in `app/services/*_service.py` except calling `IPredictionService.record_prediction` (M2).
- DB models, migrations, or repositories (M3).
- `docker-compose.yml` or Dockerfiles for any container that isn't `worker` (M3 — but you draft `docker/worker.Dockerfile` for M3 to review).
- Vault / SFTP / Casbin / fastapi-cache2 wiring (M3 / M2).
