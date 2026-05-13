FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /workspace
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend --frozen --no-dev

FROM python:3.11-slim AS runtime

# site-packages must come BEFORE /workspace/backend so that `import alembic`
# resolves to the installed package, not the local backend/alembic/ migrations dir.
ENV PATH="/workspace/backend/.venv/bin:${PATH}" \
    PYTHONPATH="/workspace/backend/.venv/lib/python3.11/site-packages:/workspace/backend" \
    PYTHONUNBUFFERED=1

WORKDIR /workspace
COPY --from=builder /workspace/backend/.venv backend/.venv
COPY alembic.ini alembic.ini
COPY backend/alembic backend/alembic
COPY backend/app backend/app

CMD ["alembic", "upgrade", "head"]
