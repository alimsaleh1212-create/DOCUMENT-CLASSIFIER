from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pytest

from app.db import models
from app.domain.contracts import PredictionLabel, PredictionOut
from app.repositories.audit_repo import AuditRepository
from app.repositories.prediction_repo import PredictionRepository


def now() -> datetime:
    return datetime.now().astimezone()


def make_document(batch_id: uuid.UUID | None = None) -> models.Document:
    document = models.Document(
        id=uuid.uuid4(),
        batch_id=batch_id or uuid.uuid4(),
        blob_key="documents/batch/document.tif",
    )
    document.created_at = now()
    return document


def make_prediction(
    batch_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    label: PredictionLabel = PredictionLabel.invoice,
) -> models.Prediction:
    prediction = models.Prediction(
        id=uuid.uuid4(),
        batch_id=batch_id or uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        label=label.value,
        top1_confidence=0.91,
        top5=[(label.value, 0.91), (PredictionLabel.memo.value, 0.05)],
        overlay_url="http://example.test/overlay.png",
        model_version="model-v1",
    )
    prediction.created_at = now()
    return prediction


def make_prediction_out(batch_id: uuid.UUID, document_id: uuid.UUID) -> PredictionOut:
    return PredictionOut(
        id=str(uuid.uuid4()),
        batch_id=str(batch_id),
        document_id=str(document_id),
        label=PredictionLabel.invoice,
        top1_confidence=0.91,
        top5=[
            (PredictionLabel.invoice, 0.91),
            (PredictionLabel.memo, 0.05),
        ],
        overlay_url="http://example.test/overlay.png",
        model_version="model-v1",
        created_at=now(),
    )


class FakeResult:
    def __init__(self, value: Any = None, values: list[Any] | None = None) -> None:
        self.value = value
        self.values = values or []

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
        self.added: list[Any] = []
        self.flush_count = 0
        self.refreshed: list[Any] = []
        self.executed_statement: Any | None = None

    async def get(self, model: type, primary_key: uuid.UUID) -> Any | None:
        return self.get_result

    async def execute(self, statement: Any) -> FakeResult:
        self.executed_statement = statement
        return self.execute_result

    def add(self, instance: Any) -> None:
        self.added.append(instance)
        if isinstance(instance, models.AuditLog):
            instance.id = uuid.uuid4()
            instance.timestamp = now()

    async def flush(self) -> None:
        self.flush_count += 1

    async def refresh(self, instance: Any) -> None:
        self.refreshed.append(instance)


@pytest.mark.asyncio
async def test_prediction_create_idempotent_requires_existing_document() -> None:
    prediction = make_prediction_out(uuid.uuid4(), uuid.uuid4())
    repository = PredictionRepository(FakeSession())  # type: ignore[arg-type]

    with pytest.raises(LookupError, match="document not found"):
        await repository.create_idempotent(prediction)


@pytest.mark.asyncio
async def test_prediction_create_idempotent_returns_saved_prediction() -> None:
    document = make_document()
    prediction_input = make_prediction_out(document.batch_id, document.id)
    saved_prediction = make_prediction(document.batch_id, document.id)
    session = FakeSession(
        get_result=document,
        execute_result=FakeResult(value=saved_prediction),
    )
    repository = PredictionRepository(session)  # type: ignore[arg-type]

    result = await repository.create_idempotent(prediction_input)

    assert result.batch_id == str(document.batch_id)
    assert result.document_id == str(document.id)
    assert result.model_version == "model-v1"
    assert result.label == PredictionLabel.invoice
    assert session.executed_statement is not None
    assert session.flush_count == 1


@pytest.mark.asyncio
async def test_prediction_list_recent_maps_results() -> None:
    predictions = [
        make_prediction(label=PredictionLabel.invoice),
        make_prediction(label=PredictionLabel.memo),
    ]
    session = FakeSession(execute_result=FakeResult(values=predictions))
    repository = PredictionRepository(session)  # type: ignore[arg-type]

    result = await repository.list_recent(limit=2)

    assert [prediction.label for prediction in result] == [
        PredictionLabel.invoice,
        PredictionLabel.memo,
    ]


@pytest.mark.asyncio
async def test_prediction_update_label_flushes_and_refreshes() -> None:
    prediction = make_prediction(label=PredictionLabel.invoice)
    session = FakeSession(get_result=prediction)
    repository = PredictionRepository(session)  # type: ignore[arg-type]

    result = await repository.update_label(str(prediction.id), PredictionLabel.memo)

    assert result.label == PredictionLabel.memo
    assert prediction.label == PredictionLabel.memo.value
    assert session.flush_count == 1
    assert session.refreshed == [prediction]


@pytest.mark.asyncio
async def test_audit_repository_insert_flushes_and_maps_entry() -> None:
    actor_id = uuid.uuid4()
    session = FakeSession()
    repository = AuditRepository(session)  # type: ignore[arg-type]

    result = await repository.insert(
        actor_id=str(actor_id),
        action="role_change",
        target="users/123",
        metadata={"role": "admin"},
    )

    assert result.actor_id == str(actor_id)
    assert result.action == "role_change"
    assert result.target == "users/123"
    assert result.metadata == {"role": "admin"}
    assert len(session.added) == 1
    assert session.flush_count == 1
    assert session.refreshed == session.added
