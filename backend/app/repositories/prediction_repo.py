from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.domain.contracts import PredictionLabel, PredictionOut
from app.repositories._mapping import (
    parse_uuid,
    prediction_to_domain,
    prediction_top5_to_json,
    require_row,
)
from app.repositories.interfaces import IPredictionRepository


class PredictionRepository(IPredictionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_idempotent(self, prediction: PredictionOut) -> PredictionOut:
        batch_id = parse_uuid(prediction.batch_id)
        document_id = parse_uuid(prediction.document_id)
        document = await self._session.get(models.Document, document_id)
        require_row(document, f"document not found: {prediction.document_id}")

        statement = (
            insert(models.Prediction)
            .values(
                id=parse_uuid(prediction.id),
                document_id=document_id,
                batch_id=batch_id,
                label=prediction.label.value,
                top1_confidence=prediction.top1_confidence,
                top5=prediction_top5_to_json(prediction.top5),
                overlay_url=prediction.overlay_url,
                model_version=prediction.model_version,
                latency_ms=prediction.latency_ms,
            )
            .on_conflict_do_update(
                constraint="uq_predictions_batch_document",
                set_={
                    "label": prediction.label.value,
                    "top1_confidence": prediction.top1_confidence,
                    "top5": prediction_top5_to_json(prediction.top5),
                    "overlay_url": prediction.overlay_url,
                    "model_version": prediction.model_version,
                    "latency_ms": prediction.latency_ms,
                },
            )
            .returning(models.Prediction)
        )
        result = await self._session.execute(statement)
        await self._session.flush()
        return prediction_to_domain(result.scalar_one())

    async def list_recent(self, limit: int = 50) -> list[PredictionOut]:
        result = await self._session.execute(
            select(models.Prediction).order_by(models.Prediction.created_at.desc()).limit(limit)
        )
        return [prediction_to_domain(prediction) for prediction in result.scalars()]

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        label_filter: PredictionLabel | None = None,
        color_filter: str | None = None,
    ) -> list[PredictionOut]:
        stmt = select(models.Prediction).order_by(models.Prediction.created_at.desc())
        if label_filter is not None:
            stmt = stmt.where(models.Prediction.label == label_filter.value)
        if color_filter is not None:
            stmt = stmt.where(models.Prediction.comment_color == color_filter)
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await self._session.execute(stmt)
        return [prediction_to_domain(p) for p in result.scalars()]

    async def get(self, prediction_id: str) -> PredictionOut:
        prediction = await self._session.get(models.Prediction, parse_uuid(prediction_id))
        return prediction_to_domain(
            require_row(prediction, f"prediction not found: {prediction_id}")
        )

    async def update_label(self, prediction_id: str, new_label: PredictionLabel) -> PredictionOut:
        prediction = await self._session.get(models.Prediction, parse_uuid(prediction_id))
        prediction = require_row(prediction, f"prediction not found: {prediction_id}")
        prediction.label = new_label.value
        await self._session.flush()
        await self._session.refresh(prediction)
        return prediction_to_domain(prediction)

    async def update_comment(
        self,
        prediction_id: str,
        comment: str | None,
        comment_color: str | None,
    ) -> PredictionOut:
        prediction = await self._session.get(models.Prediction, parse_uuid(prediction_id))
        prediction = require_row(prediction, f"prediction not found: {prediction_id}")
        prediction.comment = comment
        prediction.comment_color = comment_color
        await self._session.flush()
        await self._session.refresh(prediction)
        return prediction_to_domain(prediction)

    async def update_name(self, prediction_id: str, document_name: str | None) -> PredictionOut:
        prediction = await self._session.get(models.Prediction, parse_uuid(prediction_id))
        prediction = require_row(prediction, f"prediction not found: {prediction_id}")
        prediction.document_name = document_name
        await self._session.flush()
        await self._session.refresh(prediction)
        return prediction_to_domain(prediction)
