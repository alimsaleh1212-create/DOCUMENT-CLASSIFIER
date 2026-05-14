# Runbook — Document Classifier Operations

Procedures for deployment, recovery, and vertical-specific troubleshooting.

## 🚀 Standard Operations

### Starting the Stack
```bash
cp .env.example .env
# Set VAULT_TOKEN in .env
docker compose up -d

# Seed Vault (Initial setup only)
./docker/vault-init.sh
```

### Stopping the Stack
- **Standard**: `docker compose down` (preserves volumes)
- **Wipe Data**: `docker compose down -v` (deletes all databases/blobs)

---

## 🛠 Maintenance & Recovery

### [REC-01] Redis Queue Recovery
If the task queue is lost but source files exist on SFTP:
1. Verify SFTP files are in `processed/`.
2. Run re-enqueue script: `python backend/scripts/enqueue_local.py <batch_id>`
3. Monitor status via `GET /batches/{bid}`.

### [REC-02] Database Migrations
```bash
# Apply latest migrations
docker compose run migrate alembic upgrade head

# Generate new migration
docker compose run migrate alembic revision --autogenerate -m "description"
```

### [MAINT-01] Disk Space Management
Docker builds for this stack consume ~11GB. To reclaim space:
- `docker system prune -a` (Global cleanup)
- `docker builder prune -a` (Clear build cache)

---

## 🔍 Vertical Troubleshooting

### Member 1 — ML & Inference
> [!IMPORTANT]
> **Issue: SHA-256 Checksum Mismatch**
> The worker validates `classifier.pt` against `model_card.json` at startup.

**Action Steps:**
1. Verify `classifier.pt` exists and was pulled via Git LFS.
2. If the model was intentionally updated, regenerate the SHA-256 in `model_card.json`.

---

### Member 2 — API & Authentication
> [!WARNING]
> **Issue: Service Refuses to Start (Vault/Casbin)**
> The API blocks startup if secrets or policies are missing.

**Action Steps:**
1. Check Vault status: `docker compose ps vault`.
2. Ensure the `migrate` container finished successfully (populates Casbin table).
3. Verify `VAULT_TOKEN` in `.env`.

---

### Member 3 — Data & Ingestion
> [!NOTE]
> **Issue: Files Stuck in SFTP `incoming/`**
> Ingest worker might be quarantining invalid files.

**Action Steps:**
1. Check ingest logs: `docker compose logs sftp-ingest`.
2. Look for `sftp.quarantine` entries (indicates non-TIFF or oversized files).
3. Verify MinIO connectivity and bucket existence.