# Runbook — Document Classifier Service

## Starting the Stack

```bash
cp .env.example .env
# Edit .env: set VAULT_TOKEN
docker compose up -d
# Wait for all services healthy:
docker compose ps
# Seed Vault (first time only):
./docker/vault-init.sh
```

## Stopping the Stack

```bash
docker compose down
# To preserve data:
docker compose down  # volumes remain
# To wipe data:
docker compose down -v
```

## Recovery Procedures

### Redis Queue Lost

If Redis loses the in-memory queue (container recreated without `appendonly`):

1. Check `redis-cli LLEN rq:queue:classify` — if empty, jobs were lost
2. Source files still exist on SFTP under `processed/`
3. Re-enqueue from CLI: `python backend/scripts/enqueue_local.py <batch_id> <doc_id>`
4. Verify via `GET /batches/{bid}`

### Vault Kill Drill

1. `docker compose stop vault`
2. `docker compose restart api` — **must exit non-zero** (refuse-to-start invariant)
3. `docker compose start vault`
4. `docker compose restart api` — now boots successfully

### Model SHA Mismatch

1. `sha256sum backend/app/classifier/models/classifier.pt` — compare with `model_card.json`
2. If mismatch: re-download from LFS (`git lfs pull`)
3. API and worker both check SHA at startup; mismatch = exit(1)

### Rotate Vault Token

1. Generate new token: `vault token create`
2. Update `.env` with new `VAULT_TOKEN`
3. `docker compose restart api worker sftp-ingest`

### Database Migration

```bash
docker compose run migrate alembic upgrade head
# To create a new migration:
docker compose run migrate alembic revision --autogenerate -m "description"
```

# Member 1 – ML Runbook

## SHA-256 mismatch on startup

The worker and API automatically validate the SHA-256 checksum of `classifier.pt` against `model_card.json` during startup.

If validation fails, startup is blocked and an error similar to the following is logged:

startup_checks.sha_mismatch expected=<...> actual=<...>

### Action Steps

1. Verify that the correct `classifier.pt` and `model_card.json` files exist.
2. Re-download the original artifacts through Git LFS.
3. If retraining was intentional:
   - regenerate the model card
   - update the SHA-256 value
   - commit both updated artifacts

---

## Top-1 accuracy below threshold

The startup check validates `test_top1` in `model_card.json`.

Current minimum threshold:

`0.50`

If accuracy falls below this value, startup is blocked.

### Action Steps

1. Re-evaluate on the full test set or golden set.
2. Confirm whether degradation is genuine.
3. Retrain with additional data or more epochs if needed.
4. Update artifacts after retraining.

# Member 2 – API & Auth Runbook

## Service refuses to boot (Casbin/Vault error)

The API service performs strict startup checks for Vault connectivity and Casbin policy presence.

### Action Steps

1. Verify Vault is running and unsealed: `docker compose ps vault`.
2. Check `.env` for the correct `VAULT_TOKEN`.
3. If Casbin table is empty, ensure the `migrate` container finished successfully.

## User permissions not taking effect

Role changes are cached at the service layer to optimize performance.

### Action Steps

1. If a role change was made directly in the DB, the cache must be cleared manually: `redis-cli DEL "fastapi-cache:user:{user_id}"`.
2. Normal role changes via the API automatically trigger cache invalidation.

# Member 3 – Infra & Pipeline Runbook

## SFTP files stuck in `incoming/`

If the `sftp-ingest` worker is running but files are not moving, check for validation errors.

### Action Steps

1. Check logs: `docker compose logs sftp-ingest`.
2. Look for `sftp.quarantine` entries. If a file is in `quarantine/`, it failed validation (e.g., non-TIFF or too large).
3. Verify MinIO connectivity: `mc ls local/documents`.

## Redis Queue (RQ) recovery

If Redis data is lost and the queue is empty while files are still in `processed/`.

### Action Steps

1. Use the recovery script to re-enqueue batches: `python backend/scripts/enqueue_local.py <batch_id>`.
2. Ensure Redis is running with `--appendonly yes` to prevent future data loss.