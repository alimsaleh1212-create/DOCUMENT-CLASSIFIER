# Document Classifier as an Authenticated Service

## Model Threshold

- **ConvNeXt test top-1 accuracy ≥ 0.85** (committed threshold; the model card must meet or exceed this)

## Latency Budgets

| Path | p95 Budget | Status |
|---|---|---|
| API cached read | < 50 ms | Placeholder — benchmark after integration |
| API uncached read | < 200 ms | Placeholder — benchmark after integration |
| Inference per document (CPU, ConvNeXt Tiny/Small) | < 1.0 s | Placeholder — benchmark after integration |
| End-to-end (SFTP drop → visible in `GET /batches/{bid}`) | < 10 s | Placeholder — benchmark after integration |

### Benchmark Methodology

Run `hey -n 200 -c 10` against the local compose stack with 50 warmed-up requests. Record date and exact command alongside numbers.

```bash
# Cached read
hey -n 200 -c 10 -H "Authorization: Bearer $TOKEN" http://localhost:8000/batches

# Uncached read (after cache invalidation)
hey -n 200 -c 10 -H "Authorization: Bearer $TOKEN" http://localhost:8000/batches/{bid}
```

Results to be filled in after Day 4 integration pass.

## Quick Start

```bash
cp .env.example .env
# Edit .env: set VAULT_TOKEN
docker compose up -d
# Wait for all services healthy
# Frontend: http://localhost:5173
# API: http://localhost:8000/docs
# MinIO Console: http://localhost:9001
# Vault: http://localhost:8200
```

## Stack

- **Backend:** Python 3.11, FastAPI, fastapi-users[sqlalchemy], Casbin, fastapi-cache2[redis], RQ, SQLAlchemy 2 (async), Alembic, asyncpg, hvac, minio, paramiko, structlog
- **Frontend:** React 18, TypeScript, Vite, TanStack Query v5, React Router v6, Tailwind CSS
- **Infra:** Postgres 16, Redis 7, MinIO, atmoz/sftp, HashiCorp Vault dev mode
- **ML:** torchvision ConvNeXt (Tiny or Small), fine-tuned on RVL-CDIP 16-class subset

## Team

- **M1** — ML & Inference Vertical: `backend/app/classifier/`, `backend/worker/`
- **M2** — API, Auth & Services Vertical: `backend/app/api/`, `backend/app/services/`, `backend/app/domain/`, `frontend/`
- **M3** — Data, Pipeline & Infra Vertical: `backend/app/db/`, `backend/app/repositories/`, `backend/app/infra/`, `backend/sftp_ingest/`, `docker-compose.yml`