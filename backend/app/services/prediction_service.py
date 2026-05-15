"""
PredictionService — record predictions and relabel them.

Owns cache reads, invalidation, and audit writes for all prediction mutations.
"""

from __future__ import annotations

import json

import structlog
from fastapi import HTTPException, status

from app.domain.contracts import PredictionLabel, PredictionOut, UserOut
from app.repositories.interfaces import IPredictionRepository
from app.services.interfaces import IAuditService, IPredictionService

logger = structlog.get_logger()

_RECENT_CACHE_KEY = "predictions:recent"
_RECENT_TTL = 15


async def _cache_get(key: str) -> str | None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        result = await FastAPICache.get_backend().get(key)
        if result is None:
            return None
        return result.decode() if isinstance(result, bytes) else result
    except Exception:
        return None


async def _cache_set(key: str, value: str, ttl: int) -> None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        await FastAPICache.get_backend().set(key, value.encode(), ttl)
    except Exception:
        pass


async def _cache_clear(key: str) -> None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        await FastAPICache.clear(namespace=key)
    except Exception:
        pass


class PredictionService(IPredictionService):
    def __init__(self, repo: IPredictionRepository, audit: IAuditService) -> None:
        self._repo = repo
        self._audit = audit

    async def record_prediction(self, prediction: PredictionOut, request_id: str) -> PredictionOut:
        saved = await self._repo.create_idempotent(prediction)

        await self._audit.record(
            actor_id=None,
            action="batch_state",
            target=prediction.batch_id,
            metadata={
                "document_id": prediction.document_id,
                "request_id": request_id,
                "source": "worker",
            },
        )

        await _cache_clear(f"batches:{prediction.batch_id}")
        await _cache_clear("batches:list")
        await _cache_clear(_RECENT_CACHE_KEY)

        return saved

    async def list_recent(self) -> list[PredictionOut]:
        cached = await _cache_get(_RECENT_CACHE_KEY)
        if cached:
            return [PredictionOut.model_validate(p) for p in json.loads(cached)]
        items = await self._repo.list_recent()
        await _cache_set(
            _RECENT_CACHE_KEY,
            json.dumps([p.model_dump(mode="json") for p in items]),
            _RECENT_TTL,
        )
        return items

    async def get(self, prediction_id: str) -> PredictionOut:
        return await self._repo.get(prediction_id)

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        label_filter: PredictionLabel | None = None,
        color_filter: str | None = None,
    ) -> list[PredictionOut]:
        return await self._repo.list_paginated(
            page=page, limit=limit, label_filter=label_filter, color_filter=color_filter
        )

    async def add_comment(
        self,
        actor: UserOut,
        prediction_id: str,
        comment: str | None,
        comment_color: str | None,
    ) -> PredictionOut:
        existing = await self._repo.get(prediction_id)
        updated = await self._repo.update_comment(prediction_id, comment, comment_color)

        await self._audit.record(
            actor_id=actor.id,
            action="add_comment",
            target=prediction_id,
            metadata={
                "comment": comment,
                "color": comment_color,
                "document_id": existing.document_id,
            },
        )

        await _cache_clear(f"batches:{existing.batch_id}")
        await _cache_clear(_RECENT_CACHE_KEY)

        logger.info("prediction.comment_added", actor=actor.id, prediction_id=prediction_id)
        return updated

    async def rename_document(
        self,
        actor: UserOut,
        prediction_id: str,
        document_name: str | None,
    ) -> PredictionOut:
        existing = await self._repo.get(prediction_id)
        old_name = existing.document_name
        cleaned = document_name.strip() if document_name else None
        if not cleaned:
            cleaned = None
        updated = await self._repo.update_name(prediction_id, cleaned)

        await self._audit.record(
            actor_id=actor.id,
            action="rename_document",
            target=prediction_id,
            metadata={
                "from": old_name,
                "to": cleaned,
                "document_id": existing.document_id,
            },
        )

        await _cache_clear(f"batches:{existing.batch_id}")
        await _cache_clear(_RECENT_CACHE_KEY)

        logger.info(
            "prediction.renamed",
            actor=actor.id,
            prediction_id=prediction_id,
            new_name=cleaned,
        )
        return updated

    async def relabel(
        self, actor: UserOut, prediction_id: str, new_label: PredictionLabel
    ) -> PredictionOut:
        from app.domain.contracts import Role  # noqa: PLC0415

        existing = await self._repo.get(prediction_id)

        # Admins can override any confidence; reviewers are restricted to low-confidence docs
        if actor.role != Role.admin and existing.top1_confidence >= 0.7:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Relabeling not allowed: top-1 confidence {existing.top1_confidence:.3f} ≥ 0.7"
                ),
            )

        updated = await self._repo.update_label(prediction_id, new_label)

        await self._audit.record(
            actor_id=actor.id,
            action="relabel",
            target=prediction_id,
            metadata={"from": str(existing.label), "to": str(new_label)},
        )

        await _cache_clear(f"batches:{existing.batch_id}")
        await _cache_clear(_RECENT_CACHE_KEY)

        logger.info(
            "prediction.relabeled",
            actor=actor.id,
            prediction_id=prediction_id,
            new_label=new_label,
        )
        return updated
