# Report 012 — Lightweight Member 3 Test Environment

## Task

Added a lightweight test-only Python project so Member 3 tests can run without
installing the ML stack.

## What Changed

- Added `backend/tests/pyproject.toml`.

## Why This Matters

The main backend `pyproject.toml` includes `torch` and `torchvision` for Member
1's ML work. Running `uv run pytest` from the backend project triggers those
large dependencies, including NVIDIA/CUDA wheels.

The test-only project includes only the dependencies needed by current Member 3
tests:

- pytest and pytest-asyncio
- Pydantic/settings
- SQLAlchemy
- Pillow
- Tenacity
- structlog
- hvac
- MinIO, Redis, RQ, Paramiko client packages

## Command Used

```bash
cd backend
uv run --project tests pytest tests/sftp_ingest tests/repositories -q
```

## Result

```text
13 passed in 5.93s
```

After expanding repository, service, and infra unit tests, the broader command is:

```bash
cd backend
uv run --project tests pytest tests/sftp_ingest tests/repositories tests/services tests/infra -q
```

Current broader result:

```text
38 passed in 2.08s
```

## Files Changed

- `backend/tests/pyproject.toml`
