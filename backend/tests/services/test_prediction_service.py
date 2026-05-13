"""
Unit tests for PredictionService.

Key graded cases:
- relabel blocks top-1 >= 0.7 (422)
- relabel writes audit record
- record_prediction writes audit record
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.contracts import PredictionLabel, PredictionOut, Role, UserOut
from app.services.prediction_service import PredictionService
from tests.fakes.audit_service import FakeAuditService
from tests.fakes.prediction_repo import FakePredictionRepo


@pytest.fixture()
def repo() -> FakePredictionRepo:
    return FakePredictionRepo()


@pytest.fixture()
def audit() -> FakeAuditService:
    return FakeAuditService()


@pytest.fixture()
def svc(repo: FakePredictionRepo, audit: FakeAuditService) -> PredictionService:
    return PredictionService(repo, audit)


@pytest.fixture()
def actor() -> UserOut:
    return UserOut(
        id=str(uuid.uuid4()),
        email="reviewer@test.com",
        role=Role.reviewer,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def _make_prediction(top1: float = 0.5, **kwargs: object) -> PredictionOut:
    return PredictionOut(
        id=str(uuid.uuid4()),
        batch_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        label=PredictionLabel.memo,
        top1_confidence=top1,
        top5=[(PredictionLabel.memo, top1)],
        overlay_url=None,
        model_version="test-v0",
        created_at=datetime.now(UTC),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# relabel guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_relabel_blocks_high_confidence(
    repo: FakePredictionRepo, svc: PredictionService, actor: UserOut
) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    p = await repo.create_idempotent(_make_prediction(top1=0.75))

    with pytest.raises(HTTPException) as exc_info:
        await svc.relabel(actor, p.id, PredictionLabel.letter)

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_relabel_blocks_exactly_0_7(
    repo: FakePredictionRepo, svc: PredictionService, actor: UserOut
) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    p = await repo.create_idempotent(_make_prediction(top1=0.7))

    with pytest.raises(HTTPException):
        await svc.relabel(actor, p.id, PredictionLabel.letter)


@pytest.mark.asyncio
async def test_relabel_succeeds_below_threshold(
    repo: FakePredictionRepo, svc: PredictionService, actor: UserOut
) -> None:
    p = await repo.create_idempotent(_make_prediction(top1=0.55))
    updated = await svc.relabel(actor, p.id, PredictionLabel.form)
    assert updated.label == PredictionLabel.form


# ---------------------------------------------------------------------------
# relabel audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_relabel_writes_audit_record(
    repo: FakePredictionRepo, audit: FakeAuditService, svc: PredictionService, actor: UserOut
) -> None:
    p = await repo.create_idempotent(_make_prediction(top1=0.4))
    await svc.relabel(actor, p.id, PredictionLabel.invoice)

    assert len(audit.records) == 1
    entry = audit.records[0]
    assert entry.action == "relabel"
    assert entry.actor_id == actor.id
    assert entry.target == p.id
    assert entry.metadata == {"from": "memo", "to": "invoice"}


# ---------------------------------------------------------------------------
# record_prediction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_prediction_persists_and_writes_audit(
    repo: FakePredictionRepo, audit: FakeAuditService, svc: PredictionService
) -> None:
    p = _make_prediction(top1=0.9)
    saved = await svc.record_prediction(p, request_id="req-001")

    assert saved.id == p.id
    assert len(audit.records) == 1
    assert audit.records[0].action == "batch_state"


@pytest.mark.asyncio
async def test_record_prediction_is_idempotent(
    repo: FakePredictionRepo, svc: PredictionService
) -> None:
    p = _make_prediction(top1=0.9)
    await svc.record_prediction(p, request_id="req-1")
    await svc.record_prediction(p, request_id="req-2")  # same id

    recent = await svc.list_recent()
    ids = [x.id for x in recent]
    assert ids.count(p.id) == 1
