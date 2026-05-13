"""Sync bridge: RQ worker (sync) → async PredictionService → Postgres."""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.contracts import PredictionOut
from app.repositories.audit_repo import AuditRepository
from app.repositories.prediction_repo import PredictionRepository
from app.services.audit_service import AuditService
from app.services.prediction_service import PredictionService


class WorkerPredictionService:
    def __init__(self, postgres_dsn: str) -> None:
        engine = create_async_engine(postgres_dsn, pool_pre_ping=True)
        self._factory = async_sessionmaker(engine, expire_on_commit=False)

    def record_prediction(self, record: PredictionOut) -> None:
        asyncio.run(self._record(record))

    async def _record(self, record: PredictionOut) -> None:
        async with self._factory() as session:
            pred_repo = PredictionRepository(session)
            audit_repo = AuditRepository(session)
            svc = PredictionService(pred_repo, AuditService(audit_repo))
            await svc.record_prediction(record, request_id=record.document_id)
            await session.commit()
