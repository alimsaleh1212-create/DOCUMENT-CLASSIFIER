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