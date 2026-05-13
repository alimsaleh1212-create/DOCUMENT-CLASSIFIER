from __future__ import annotations

import sys
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import Settings

logger = structlog.get_logger()
settings = Settings()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate or generate X-Request-ID; bind it into structlog context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id")
        return response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.use_fakes:
        await _boot_with_fakes(app)
    else:
        await _boot_production(app)

    yield

    # Shutdown
    if not settings.use_fakes:
        from app.infra.cache import close_cache  # noqa: PLC0415

        await close_cache()
        engine = getattr(app.state, "db_engine", None)
        if engine:
            await engine.dispose()


async def _boot_production(app: FastAPI) -> None:
    """Full production startup: Vault → DB → Casbin → cache."""
    import pathlib  # noqa: PLC0415

    import casbin  # noqa: PLC0415
    from casbin_sqlalchemy_adapter import Adapter as CasbinAdapter  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.infra.cache import init_cache  # noqa: PLC0415
    from app.infra.vault import VaultClient  # noqa: PLC0415

    vault = VaultClient(url=settings.vault_addr, token=settings.vault_token)

    try:
        jwt_key = vault.get_jwt_signing_key()
    except Exception as exc:
        logger.error("vault.unreachable", error=str(exc))
        sys.exit(1)

    dsn = vault.get_postgres_dsn()
    engine = create_async_engine(dsn, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app.state.db_engine = engine
    app.state.db = session_factory
    app.state.jwt_signing_key = jwt_key

    model_path = str(pathlib.Path(__file__).parent / "infra" / "casbin" / "model.conf")
    # casbin_sqlalchemy_adapter uses sync DSN (no +asyncpg)
    sync_dsn = dsn.replace("+asyncpg", "")
    adapter = CasbinAdapter(sync_dsn)
    enforcer = casbin.Enforcer(model_path, adapter)
    enforcer.load_policy()

    if not enforcer.get_all_subjects():
        logger.error("casbin.empty_policy")
        sys.exit(1)

    app.state.enforcer = enforcer

    await init_cache(app)


async def _boot_with_fakes(app: FastAPI) -> None:
    """Fake startup for local dev and testing — no Vault, DB, or Redis needed."""
    import pathlib  # noqa: PLC0415

    import casbin  # noqa: PLC0415

    from app.api.deps import (  # noqa: PLC0415
        get_audit_repo,
        get_audit_service,
        get_batch_repo,
        get_prediction_repo,
        get_user_repo,
    )
    from tests.fakes.audit_service import FakeAuditService  # noqa: PLC0415
    from tests.fakes.batch_repo import FakeBatchRepo  # noqa: PLC0415
    from tests.fakes.prediction_repo import FakePredictionRepo  # noqa: PLC0415
    from tests.fakes.user_repo import FakeUserRepo  # noqa: PLC0415

    # Static JWT signing key for dev (not a real secret)
    app.state.jwt_signing_key = "dev-secret-key-change-in-production"

    # Casbin enforcer loaded from the flat file — no DB needed
    model_path = str(pathlib.Path(__file__).parent / "infra" / "casbin" / "model.conf")
    policy_path = str(pathlib.Path(__file__).parent / "infra" / "casbin" / "policy.csv")
    enforcer = casbin.Enforcer(model_path, policy_path)
    app.state.enforcer = enforcer

    # Shared fake instances — one object per app lifetime so state is consistent
    fake_user_repo = FakeUserRepo()
    fake_batch_repo = FakeBatchRepo()
    fake_prediction_repo = FakePredictionRepo()
    fake_audit_service = FakeAuditService()
    fake_audit_repo = _FakeAuditRepo(fake_audit_service)

    # Wire all repo / service dependencies to return the fakes
    app.dependency_overrides[get_user_repo] = lambda: fake_user_repo
    app.dependency_overrides[get_batch_repo] = lambda: fake_batch_repo
    app.dependency_overrides[get_prediction_repo] = lambda: fake_prediction_repo
    app.dependency_overrides[get_audit_repo] = lambda: fake_audit_repo
    app.dependency_overrides[get_audit_service] = lambda: fake_audit_service

    # Try to init cache (requires Redis on localhost:6379, optional for dev)
    try:
        from app.infra.cache import init_cache  # noqa: PLC0415

        await init_cache(app)
        logger.info("cache.ready")
    except Exception as exc:
        logger.warning("cache.unavailable", error=str(exc))

    logger.info("booted.with.fakes")


class _FakeAuditRepo:
    """Thin shim so the audit router can call audit_repo.list() in fake mode."""

    def __init__(self, svc: object) -> None:
        self._svc = svc

    async def insert(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> object:
        import uuid  # noqa: PLC0415
        from datetime import datetime  # noqa: PLC0415

        from app.domain.contracts import AuditLogEntry  # noqa: PLC0415
        from tests.fakes.audit_service import FakeAuditService  # noqa: PLC0415

        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            actor_id=actor_id,
            action=action,
            target=target,
            metadata=metadata,
            timestamp=datetime.now(UTC),
        )
        if isinstance(self._svc, FakeAuditService):
            self._svc.records.append(entry)
        return entry

    async def list(self, page: int = 1, limit: int = 50) -> list[Any]:
        from tests.fakes.audit_service import FakeAuditService  # noqa: PLC0415

        if isinstance(self._svc, FakeAuditService):
            records = self._svc.records
            start = (page - 1) * limit
            return records[start : start + limit]
        return []


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(
    title="Document Classifier",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Cache"],
)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.exception("unhandled_exception", request_id=request_id, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
    )


# Routers — mounted after the app is defined so middleware is already registered
from app.api.routers import audit, auth, batches, predictions, users  # noqa: E402

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(batches.router)
app.include_router(predictions.router)
app.include_router(audit.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
