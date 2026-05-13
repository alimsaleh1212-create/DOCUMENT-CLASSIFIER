"""
Shared FastAPI dependencies.

All repository and service dependencies are defined here so they can be
overridden via app.dependency_overrides in fake mode or tests.
Production implementations are imported lazily to avoid circular imports.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable

import casbin
import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import decode_access_token
from app.domain.contracts import UserOut
from app.repositories.interfaces import (
    IAuditRepository,
    IBatchRepository,
    IPredictionRepository,
    IUserRepository,
)
from app.services.interfaces import IAuditService

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------


def get_request_id(request: Request) -> str:
    """Return the X-Request-ID stamped by RequestIDMiddleware."""
    return request.headers.get("X-Request-ID", "")


# ---------------------------------------------------------------------------
# DB session
# ---------------------------------------------------------------------------


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session from the engine initialised by the lifespan."""
    session_factory = getattr(request.app.state, "db", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready",
        )
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Repository dependencies (overridden in fake mode)
# ---------------------------------------------------------------------------


async def get_user_repo(
    session: AsyncSession = Depends(get_session),
) -> IUserRepository:
    from app.repositories.user_repo import UserRepository  # noqa: PLC0415

    return UserRepository(session)  # type: ignore[abstract]


async def get_batch_repo(
    session: AsyncSession = Depends(get_session),
) -> IBatchRepository:
    from app.repositories.batch_repo import BatchRepository  # noqa: PLC0415

    return BatchRepository(session)


async def get_prediction_repo(
    session: AsyncSession = Depends(get_session),
) -> IPredictionRepository:
    from app.repositories.prediction_repo import PredictionRepository  # noqa: PLC0415

    return PredictionRepository(session)


async def get_audit_repo(
    session: AsyncSession = Depends(get_session),
) -> IAuditRepository:
    from app.repositories.audit_repo import AuditRepository  # noqa: PLC0415

    return AuditRepository(session)  # type: ignore[abstract]


async def get_audit_service(
    audit_repo: IAuditRepository = Depends(get_audit_repo),
) -> IAuditService:
    # audit_service.py is M3's deliverable; mypy override covers the missing import.
    from app.services.audit_service import AuditService  # noqa: PLC0415

    return AuditService(audit_repo)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Current user (JWT validation + repo lookup)
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    user_repo: IUserRepository = Depends(get_user_repo),
) -> UserOut:
    """
    Validate the Bearer JWT and return the authenticated UserOut.

    Raises 401 on missing/invalid/expired token or unknown user.
    The signing key is read from app.state (set by the lifespan from Vault).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[len("Bearer ") :]

    signing_key: str | None = getattr(request.app.state, "jwt_signing_key", None)
    if not signing_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured",
        )

    try:
        payload = decode_access_token(token, signing_key)
        user_id: str = str(payload["sub"])
    except jwt.InvalidTokenError as exc:
        logger.warning("jwt.invalid", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        return await user_repo.get(user_id)
    except (KeyError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from exc


# ---------------------------------------------------------------------------
# Casbin role enforcement
# ---------------------------------------------------------------------------


def _get_enforcer(request: Request) -> casbin.Enforcer:
    enforcer: casbin.Enforcer | None = getattr(request.app.state, "enforcer", None)
    if enforcer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Policy enforcer not ready",
        )
    return enforcer


def require_role(*actions: str) -> Callable[..., UserOut]:
    """
    Factory that returns a Depends which enforces Casbin RBAC.

    Passes if the current user's role is allowed to perform ANY of the given actions.

    Usage::

        @router.get("/users", dependencies=[Depends(require_role("invite_user"))])
        async def list_users(...): ...
    """

    def _check(
        current_user: UserOut = Depends(get_current_user),
        enforcer: casbin.Enforcer = Depends(_get_enforcer),
    ) -> UserOut:
        role = str(current_user.role)
        for action in actions:
            if enforcer.enforce(role, action, "allow"):
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not permitted. Required: {', '.join(actions)}",
        )

    return _check
