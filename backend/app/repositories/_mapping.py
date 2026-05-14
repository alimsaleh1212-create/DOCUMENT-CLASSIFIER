from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TypeVar

from app.db import models
from app.domain.contracts import (
    AuditLogEntry,
    BatchOut,
    BatchStatus,
    DocumentOut,
    PredictionLabel,
    PredictionOut,
    Role,
    UserOut,
)

T = TypeVar("T")


def parse_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def user_to_domain(user: models.User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
        created_at=user.created_at,
    )


def batch_to_domain(batch: models.Batch) -> BatchOut:
    return BatchOut(
        id=str(batch.id),
        status=BatchStatus(batch.status),
        document_count=batch.document_count,
        created_at=batch.created_at,
    )


def document_to_domain(document: models.Document) -> DocumentOut:
    return DocumentOut(
        id=str(document.id),
        batch_id=str(document.batch_id),
        blob_key=document.blob_key,
        created_at=document.created_at,
    )


def prediction_to_domain(prediction: models.Prediction) -> PredictionOut:
    top5 = [(PredictionLabel(label), confidence) for label, confidence in prediction.top5]
    return PredictionOut(
        id=str(prediction.id),
        batch_id=str(prediction.batch_id),
        document_id=str(prediction.document_id),
        label=PredictionLabel(prediction.label),
        top1_confidence=prediction.top1_confidence,
        top5=top5,
        overlay_url=prediction.overlay_url,
        model_version=prediction.model_version,
        created_at=prediction.created_at,
        comment=prediction.comment,
        comment_color=prediction.comment_color,
        latency_ms=prediction.latency_ms,
        document_name=prediction.document_name,
    )


def prediction_top5_to_json(
    top5: list[tuple[PredictionLabel, float]],
) -> list[tuple[str, float]]:
    return [(label.value, confidence) for label, confidence in top5]


def audit_log_to_domain(
    audit_log: models.AuditLog, actor_email: str | None = None
) -> AuditLogEntry:
    actor_id = "" if audit_log.actor_id is None else str(audit_log.actor_id)
    return AuditLogEntry(
        id=str(audit_log.id),
        actor_id=actor_id,
        actor_email=actor_email,
        action=audit_log.action,
        target=audit_log.target,
        metadata=audit_log.metadata_,
        timestamp=audit_log.timestamp,
    )


def require_row(row: T | None, message: str) -> T:
    if row is None:
        raise LookupError(message)
    return row


def utc_now_if_missing(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now().astimezone()
    return value


def metadata_or_none(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    return None if metadata is None else dict(metadata)
