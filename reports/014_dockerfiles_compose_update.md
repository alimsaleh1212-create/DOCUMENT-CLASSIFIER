# Report 014 — Dockerfiles and Compose Update

## Task

Added backend service Dockerfiles and updated Docker Compose to use them.

## What Changed

- Added `docker/api.Dockerfile`.
- Added `docker/worker.Dockerfile`.
- Added `docker/sftp_ingest.Dockerfile`.
- Added `docker/migrate.Dockerfile`.
- Updated `docker-compose.yml` to point each backend service at its Dockerfile:
  - `api` -> `docker/api.Dockerfile`
  - `worker` -> `docker/worker.Dockerfile`
  - `sftp-ingest` -> `docker/sftp_ingest.Dockerfile`
  - `migrate` -> `docker/migrate.Dockerfile`
- Added a one-shot `vault-init` service that runs `docker/vault-init.sh`.
- Updated service dependencies so API, worker, and SFTP ingest wait for
  `vault-init` to complete.
- Updated `sftp-ingest` to wait for `migrate` before starting because it writes
  `batches` and `documents` rows.
- Added an SFTP ingest heartbeat healthcheck.
- Updated `backend/alembic/env.py` to prefer `DATABASE_URL` from the environment.
- Updated `docker/vault-init.sh` to avoid requiring `openssl` in the Vault image.

## Why This Matters

The previous compose file pointed backend services at `backend/Dockerfile`, but
that file did not exist. The new Dockerfiles give each service an explicit build
target and command.

`migrate` also needs `DATABASE_URL` to point at the Compose `db` service, not the
local default in `alembic.ini`.

## Member 2 Auth Note

Member 2 owns FastAPI Users, JWT, SQLAlchemy auth adapter, and auth endpoints.
Member 3 only needs to support that work by providing:

- Postgres schema/migrations
- migrate-before-api boot order
- Vault client and seeded JWT signing key path
- compose env for `VAULT_ADDR` and `VAULT_TOKEN`

## Files Changed

- `docker/api.Dockerfile`
- `docker/worker.Dockerfile`
- `docker/sftp_ingest.Dockerfile`
- `docker/migrate.Dockerfile`
- `docker-compose.yml`
- `docker/vault-init.sh`
- `backend/alembic/env.py`

## Notes

- `frontend/Dockerfile` is still owned by Member 2 and was not added here.
- Image builds were not run in this step.

## Validation

- `python3 -m py_compile backend/alembic/env.py` passed.
- Line-length scan for Dockerfiles, Compose, Vault init, Alembic env, and this
  report passed.
- `docker compose config` could not run because Docker is not available in this
  WSL distro. Docker Desktop WSL integration must be enabled before validating
  or building images locally.
