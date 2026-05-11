# Collaboration — Document Classifier Service

## Team Members

- **M1** — ML & Inference Vertical: `backend/app/classifier/`, `backend/worker/`, model weights, golden set
- **M2** — API, Auth & Services Vertical: `backend/app/api/`, `backend/app/services/`, `backend/app/domain/`, `frontend/`
- **M3** — Data, Pipeline & Infra Vertical: `backend/app/db/`, `backend/app/repositories/`, `backend/app/infra/`, `backend/sftp_ingest/`, `docker-compose.yml`

## Merge & Review Process

- All PRs require at least 1 approving review before merging to `main`
- Branch naming: `feature/<short-desc>`, `bugfix/<short-desc>`, `chore/<short-desc>`
- Conventional commits: `type(scope): short imperative summary` ≤ 72 chars
- CI must be green (ruff, mypy, pytest) before merge

## Day 0 Contract Sign-Off

All contracts in `shared_tasks.md` §0.2 were agreed upon before feature branches opened:
- Pydantic domain models (`backend/app/domain/contracts.py`)
- Service interfaces (`backend/app/services/interfaces.py`)
- Repository interfaces (`backend/app/repositories/interfaces.py`)
- DB schema (`docs/erd.md`)
- MinIO layout (`docs/blob_layout.md`)
- Vault paths (`docs/vault_paths.md`)
- Casbin policy (`backend/app/infra/casbin/policy.csv`)
- API endpoint table and frontend route map (`ARCH.md`)
- Latency budgets and model threshold (`README.md`)

## One Disagreement & Resolution

*(To be filled during development.)*

## One Bug & Fix

*(To be filled during development.)*