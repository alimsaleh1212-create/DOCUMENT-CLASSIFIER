"""
UserService — business logic for user management.

Owns cache reads (@cache) and cache invalidation (FastAPICache.clear).
Calls audit_service.record() inside every mutating operation.
Never touches HTTP types or SQLAlchemy.
"""

from __future__ import annotations

import structlog
from fastapi import HTTPException, status

from app.domain.contracts import Role, UserOut
from app.repositories.interfaces import IUserRepository
from app.services.interfaces import IAuditService, IUserService

logger = structlog.get_logger()

_CACHE_TTL = 60
_CACHE_NS_PREFIX = "user"


def _user_cache_key(user_id: str) -> str:
    return f"{_CACHE_NS_PREFIX}:{user_id}"


async def _cache_get(key: str) -> str | None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        backend = FastAPICache.get_backend()
        result = await backend.get(key)
        if result is None:
            return None
        return result.decode() if isinstance(result, bytes) else result
    except Exception:
        return None


async def _cache_set(key: str, value: str) -> None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        backend = FastAPICache.get_backend()
        await backend.set(key, value.encode(), _CACHE_TTL)
    except Exception:
        pass


async def _cache_clear(key: str) -> None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        await FastAPICache.clear(namespace=key)
    except Exception:
        pass


class UserService(IUserService):
    def __init__(self, repo: IUserRepository, audit: IAuditService) -> None:
        self._repo = repo
        self._audit = audit

    async def get_me(self, user_id: str) -> UserOut:
        cache_key = _user_cache_key(user_id)
        cached = await _cache_get(cache_key)
        if cached:
            return UserOut.model_validate_json(cached)
        user = await self._repo.get(user_id)
        await _cache_set(cache_key, user.model_dump_json())
        return user

    async def list_users(self) -> list[UserOut]:
        return await self._repo.list_users()

    async def toggle_role(self, actor: UserOut, target_uid: str, new_role: Role) -> UserOut:
        target = await self._repo.get(target_uid)
        old_role = target.role

        # Guard: prevent the last admin from demoting themselves
        if (
            actor.id == target_uid
            and actor.role == Role.admin
            and new_role != Role.admin
            and await self._repo.count_admins() == 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote the only admin account",
            )

        updated = await self._repo.update_role(target_uid, new_role)

        await self._audit.record(
            actor_id=actor.id,
            action="role_change",
            target=target_uid,
            metadata={"from": str(old_role), "to": str(new_role)},
        )

        await _cache_clear(_user_cache_key(target_uid))
        logger.info("role.changed", actor=actor.id, target=target_uid, new_role=new_role)
        return updated

    async def delete_user(self, actor: UserOut, target_uid: str) -> None:
        if actor.id == target_uid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete your own account",
            )

        if actor.role == Role.admin and await self._repo.count_admins() == 1:
            target = await self._repo.get(target_uid)
            if target.role == Role.admin:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete the only admin account",
                )

        await self._repo.delete(target_uid)

        await self._audit.record(
            actor_id=actor.id,
            action="delete_user",
            target=target_uid,
            metadata=None,
        )

        await _cache_clear(_user_cache_key(target_uid))
        logger.info("user.deleted", actor=actor.id, target=target_uid)
