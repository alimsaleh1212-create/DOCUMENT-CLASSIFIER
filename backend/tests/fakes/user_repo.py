from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.contracts import Role, UserOut
from app.repositories.interfaces import IUserRepository


class FakeUserRepo(IUserRepository):
    """In-memory IUserRepository. First registered user is auto-promoted to admin."""

    def __init__(self) -> None:
        self._store: dict[str, UserOut] = {}
        self._by_email: dict[str, str] = {}  # email → id
        self._hashed_passwords: dict[str, str] = {}  # user_id → hashed_password

    def seed(self, user: UserOut, hashed_password: str = "") -> UserOut:
        self._store[user.id] = user
        self._by_email[user.email] = user.id
        self._hashed_passwords[user.id] = hashed_password
        return user

    def get_hashed_password(self, user_id: str) -> str:
        return self._hashed_passwords.get(user_id, "")

    def _make(self, email: str, role: Role = Role.reviewer) -> UserOut:
        uid = str(uuid.uuid4())
        user = UserOut(
            id=uid,
            email=email,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return self.seed(user)

    async def create_user(
        self, email: str, hashed_password: str, role: Role = Role.reviewer
    ) -> UserOut:
        if email in self._by_email:
            raise ValueError(f"Email already registered: {email}")
        if not self._store:
            role = Role.admin  # first user becomes admin
        uid = str(uuid.uuid4())
        user = UserOut(
            id=uid,
            email=email,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return self.seed(user, hashed_password)

    async def get(self, user_id: str) -> UserOut:
        try:
            return self._store[user_id]
        except KeyError as exc:
            raise KeyError(f"User {user_id} not found") from exc

    async def get_by_email(self, email: str) -> UserOut | None:
        uid = self._by_email.get(email)
        return self._store[uid] if uid else None

    async def list_users(self) -> list[UserOut]:
        return list(self._store.values())

    async def update_role(self, user_id: str, new_role: Role) -> UserOut:
        user = await self.get(user_id)
        updated = user.model_copy(update={"role": new_role})
        self._store[user_id] = updated
        return updated

    async def count_admins(self) -> int:
        return sum(1 for u in self._store.values() if u.role == Role.admin)
