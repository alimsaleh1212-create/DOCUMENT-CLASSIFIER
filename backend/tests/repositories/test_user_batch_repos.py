from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pytest

from app.db import models
from app.domain.contracts import BatchStatus, Role
from app.repositories.batch_repo import BatchRepository
from app.repositories.user_repo import UserRepository


def now() -> datetime:
    return datetime.now().astimezone()


def make_user(email: str, role: Role = Role.reviewer) -> models.User:
    user = models.User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashed",
        role=role.value,
        is_active=True,
    )
    user.created_at = now()
    return user


def make_batch(status: BatchStatus = BatchStatus.pending) -> models.Batch:
    batch = models.Batch(id=uuid.uuid4(), status=status.value, document_count=0)
    batch.created_at = now()
    return batch


class FakeResult:
    def __init__(self, value: Any = None, values: list[Any] | None = None) -> None:
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self) -> Any | None:
        return self.value

    def scalar_one(self) -> Any:
        return self.value

    def scalars(self) -> list[Any]:
        return self.values


class FakeSession:
    def __init__(
        self,
        get_result: Any | None = None,
        execute_result: FakeResult | None = None,
    ) -> None:
        self.get_result = get_result
        self.execute_result = execute_result or FakeResult()
        self.flush_count = 0
        self.refreshed: list[Any] = []

    async def get(self, model: type, primary_key: uuid.UUID) -> Any | None:
        return self.get_result

    async def execute(self, statement: Any) -> FakeResult:
        return self.execute_result

    async def flush(self) -> None:
        self.flush_count += 1

    async def refresh(self, instance: Any) -> None:
        self.refreshed.append(instance)


@pytest.mark.asyncio
async def test_user_repository_get_returns_user() -> None:
    user = make_user("reviewer@example.com")
    repository = UserRepository(FakeSession(get_result=user))  # type: ignore[arg-type]

    result = await repository.get(str(user.id))

    assert result.id == str(user.id)
    assert result.email == "reviewer@example.com"
    assert result.role == Role.reviewer


@pytest.mark.asyncio
async def test_user_repository_get_missing_raises_lookup_error() -> None:
    repository = UserRepository(FakeSession())  # type: ignore[arg-type]

    with pytest.raises(LookupError, match="user not found"):
        await repository.get(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_user_repository_get_by_email_returns_none_when_missing() -> None:
    repository = UserRepository(FakeSession())  # type: ignore[arg-type]

    assert await repository.get_by_email("missing@example.com") is None


@pytest.mark.asyncio
async def test_user_repository_list_users_maps_results() -> None:
    users = [make_user("a@example.com"), make_user("b@example.com", Role.admin)]
    session = FakeSession(execute_result=FakeResult(values=users))
    repository = UserRepository(session)  # type: ignore[arg-type]

    result = await repository.list_users()

    assert [user.email for user in result] == ["a@example.com", "b@example.com"]


@pytest.mark.asyncio
async def test_user_repository_update_role_flushes_and_refreshes() -> None:
    user = make_user("reviewer@example.com")
    session = FakeSession(get_result=user)
    repository = UserRepository(session)  # type: ignore[arg-type]

    result = await repository.update_role(str(user.id), Role.admin)

    assert result.role == Role.admin
    assert user.role == Role.admin.value
    assert session.flush_count == 1
    assert session.refreshed == [user]


@pytest.mark.asyncio
async def test_user_repository_count_admins_returns_count() -> None:
    session = FakeSession(execute_result=FakeResult(value=2))
    repository = UserRepository(session)  # type: ignore[arg-type]

    assert await repository.count_admins() == 2


@pytest.mark.asyncio
async def test_batch_repository_get_returns_batch() -> None:
    batch = make_batch(BatchStatus.processing)
    repository = BatchRepository(FakeSession(get_result=batch))  # type: ignore[arg-type]

    result = await repository.get(str(batch.id))

    assert result.id == str(batch.id)
    assert result.status == BatchStatus.processing


@pytest.mark.asyncio
async def test_batch_repository_list_batches_maps_results() -> None:
    batches = [make_batch(BatchStatus.pending), make_batch(BatchStatus.complete)]
    session = FakeSession(execute_result=FakeResult(values=batches))
    repository = BatchRepository(session)  # type: ignore[arg-type]

    result = await repository.list_batches()

    assert [batch.status for batch in result] == [
        BatchStatus.pending,
        BatchStatus.complete,
    ]


@pytest.mark.asyncio
async def test_batch_repository_update_status_flushes_and_refreshes() -> None:
    batch = make_batch(BatchStatus.pending)
    session = FakeSession(get_result=batch)
    repository = BatchRepository(session)  # type: ignore[arg-type]

    result = await repository.update_status(str(batch.id), BatchStatus.failed)

    assert result.status == BatchStatus.failed
    assert batch.status == BatchStatus.failed.value
    assert session.flush_count == 1
    assert session.refreshed == [batch]
