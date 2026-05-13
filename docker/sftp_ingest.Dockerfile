FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /workspace
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend --frozen --no-dev

FROM python:3.11-slim AS runtime

ENV PATH="/workspace/backend/.venv/bin:${PATH}" \
    PYTHONPATH="/workspace/backend" \
    PYTHONUNBUFFERED=1

WORKDIR /workspace
COPY --from=builder /workspace/backend/.venv backend/.venv
COPY backend/app backend/app
COPY backend/sftp_ingest backend/sftp_ingest

CMD ["python", "-m", "sftp_ingest"]
