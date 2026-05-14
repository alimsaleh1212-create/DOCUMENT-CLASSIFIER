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

# Document Classification System

A document classification system trained to classify 16 document layout categories using a ConvNeXt-Tiny backbone.

## Model Overview

- Backbone: `convnext_tiny`
- Weights: `ConvNeXt_Tiny_Weights.IMAGENET1K_V1`
- Fine-tuning: Full fine-tuning
- Classes: 16 document categories
- Dataset: RVL-CDIP

## Training Environment

Training was performed in Google Colab using GPU acceleration.

Google Colab notebook:  
https://colab.research.google.com/drive/14s1vsg8iVFfOQJxnOE5K4mwymwITiXSM?usp=sharing

The notebook includes:

- Dataset preparation
- Data preprocessing
- Training pipeline
- Model fine-tuning
- Evaluation
- Artifact generation

## Project Documentation

- `DECISIONS.md` — design and ML decisions
- `RUNBOOK.md` — troubleshooting and operational procedures
- `LICENSES.md` — licensing information

## API & Authentication (Member 2)

- **FastAPI**: Asynchronous API with structured logging and standard error handling.
- **Auth**: JWT-based authentication via `fastapi-users`. Signing keys are fetched securely from Vault.
- **RBAC**: Role-Based Access Control using Casbin. Policies are managed as data.
- **Frontend**: A React SPA built with Vite and TanStack Query, featuring real-time cache observability.

## Data Pipeline & Infrastructure (Member 3)

- **Orchestration**: Full stack defined in `docker-compose.yml` with health-checked boot ordering.
- **Persistence**: PostgreSQL 16 for metadata, MinIO for object storage (blobs and overlays).
- **Ingestion**: An autonomous SFTP polling worker that validates and quarantines incoming TIFFs.
- **Async Processing**: RQ (Redis Queue) handles background inference jobs with persistent queueing.