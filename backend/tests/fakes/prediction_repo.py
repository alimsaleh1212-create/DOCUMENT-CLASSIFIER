from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.contracts import PredictionLabel, PredictionOut
from app.repositories.interfaces import IPredictionRepository


class FakePredictionRepo(IPredictionRepository):
    """In-memory IPredictionRepository. create_idempotent upserts on id."""

    def __init__(self) -> None:
        self._store: dict[str, PredictionOut] = {}

    def seed(self, prediction: PredictionOut) -> PredictionOut:
        self._store[prediction.id] = prediction
        return prediction

    def _make(
        self,
        batch_id: str,
        document_id: str,
        label: PredictionLabel = PredictionLabel.memo,
        top1: float = 0.95,
    ) -> PredictionOut:
        pid = str(uuid.uuid4())
        p = PredictionOut(
            id=pid,
            batch_id=batch_id,
            document_id=document_id,
            label=label,
            top1_confidence=top1,
            top5=[(label, top1)],
            overlay_url=None,
            model_version="test-v0",
            created_at=datetime.now(UTC),
        )
        return self.seed(p)

    async def create_idempotent(self, prediction: PredictionOut) -> PredictionOut:
        self._store[prediction.id] = prediction
        return prediction

    async def list_recent(self, limit: int = 50) -> list[PredictionOut]:
        items = sorted(self._store.values(), key=lambda p: p.created_at, reverse=True)
        return items[:limit]

    async def get(self, prediction_id: str) -> PredictionOut:
        try:
            return self._store[prediction_id]
        except KeyError as exc:
            raise KeyError(f"Prediction {prediction_id} not found") from exc

    async def update_label(self, prediction_id: str, new_label: PredictionLabel) -> PredictionOut:
        prediction = await self.get(prediction_id)
        updated = prediction.model_copy(update={"label": new_label})
        self._store[prediction_id] = updated
        return updated
