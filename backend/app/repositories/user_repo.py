from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.domain.contracts import Role, UserOut
from app.repositories._mapping import parse_uuid, require_row, user_to_domain
from app.repositories.interfaces import IUserRepository


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: str) -> UserOut:
        user = await self._session.get(models.User, parse_uuid(user_id))
        return user_to_domain(require_row(user, f"user not found: {user_id}"))

    async def get_by_email(self, email: str) -> UserOut | None:
        result = await self._session.execute(
            select(models.User).where(models.User.email == email)
        )
        user = result.scalar_one_or_none()
        return None if user is None else user_to_domain(user)

    async def list_users(self) -> list[UserOut]:
        result = await self._session.execute(select(models.User).order_by(models.User.email))
        return [user_to_domain(user) for user in result.scalars()]

    async def update_role(self, user_id: str, new_role: Role) -> UserOut:
        user = await self._session.get(models.User, parse_uuid(user_id))
        user = require_row(user, f"user not found: {user_id}")
        user.role = new_role.value
        await self._session.flush()
        await self._session.refresh(user)
        return user_to_domain(user)

    async def count_admins(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(models.User).where(models.User.role == Role.admin)
        )
        return int(result.scalar_one())
