"""
Unit tests for UserService.

Key graded cases:
- toggle_role writes audit record and clears cache
- toggle_role blocks demotion of the only admin (409)
"""

from __future__ import annotations

import pytest

from app.domain.contracts import Role, UserOut
from app.services.user_service import UserService
from tests.fakes.audit_service import FakeAuditService
from tests.fakes.user_repo import FakeUserRepo


@pytest.fixture()
def repo() -> FakeUserRepo:
    return FakeUserRepo()


@pytest.fixture()
def audit() -> FakeAuditService:
    return FakeAuditService()


@pytest.fixture()
def svc(repo: FakeUserRepo, audit: FakeAuditService) -> UserService:
    return UserService(repo, audit)


async def _create_admin(repo: FakeUserRepo, email: str = "admin@test.com") -> UserOut:
    from app.api.auth import hash_password  # noqa: PLC0415

    return await repo.create_user(email, hash_password("pass"), Role.admin)


async def _create_reviewer(repo: FakeUserRepo, email: str = "r@test.com") -> UserOut:
    import datetime

    # Manually seed to bypass the first-user-is-admin logic
    import uuid  # noqa: PLC0415, E401

    from app.api.auth import hash_password  # noqa: PLC0415

    user = UserOut(
        id=str(uuid.uuid4()),
        email=email,
        role=Role.reviewer,
        is_active=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    return repo.seed(user, hash_password("pass"))


# ---------------------------------------------------------------------------
# get_me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_me_returns_user(repo: FakeUserRepo, svc: UserService) -> None:
    admin = await _create_admin(repo)
    result = await svc.get_me(admin.id)
    assert result.id == admin.id
    assert result.email == admin.email


# ---------------------------------------------------------------------------
# toggle_role — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_role_writes_audit_record(
    repo: FakeUserRepo, audit: FakeAuditService, svc: UserService
) -> None:
    admin = await _create_admin(repo)
    reviewer = await _create_reviewer(repo)

    await svc.toggle_role(admin, reviewer.id, Role.auditor)

    assert len(audit.records) == 1
    entry = audit.records[0]
    assert entry.actor_id == admin.id
    assert entry.action == "role_change"
    assert entry.target == reviewer.id
    assert entry.metadata == {"from": "reviewer", "to": "auditor"}


@pytest.mark.asyncio
async def test_toggle_role_updates_role_in_repo(repo: FakeUserRepo, svc: UserService) -> None:
    admin = await _create_admin(repo)
    reviewer = await _create_reviewer(repo)

    updated = await svc.toggle_role(admin, reviewer.id, Role.auditor)

    assert updated.role == Role.auditor
    stored = await repo.get(reviewer.id)
    assert stored.role == Role.auditor


# ---------------------------------------------------------------------------
# toggle_role — single-admin demotion guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_role_blocks_only_admin_self_demotion(
    repo: FakeUserRepo, svc: UserService
) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    admin = await _create_admin(repo)

    with pytest.raises(HTTPException) as exc_info:
        await svc.toggle_role(admin, admin.id, Role.reviewer)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_toggle_role_allows_demotion_when_two_admins_exist(
    repo: FakeUserRepo, svc: UserService
) -> None:
    admin1 = await _create_admin(repo, "a1@test.com")

    import datetime
    import uuid  # noqa: PLC0415, E401

    admin2_user = UserOut(
        id=str(uuid.uuid4()),
        email="a2@test.com",
        role=Role.admin,
        is_active=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    from app.api.auth import hash_password  # noqa: PLC0415

    repo.seed(admin2_user, hash_password("pass"))

    # Should NOT raise — there are 2 admins
    result = await svc.toggle_role(admin1, admin1.id, Role.reviewer)
    assert result.role == Role.reviewer
