from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    admin = "admin"
    reviewer = "reviewer"
    auditor = "auditor"


class BatchStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class PredictionLabel(StrEnum):
    letter = "letter"
    form = "form"
    email = "email"
    handwritten = "handwritten"
    advertisement = "advertisement"
    scientific_report = "scientific_report"
    scientific_publication = "scientific_publication"
    specification = "specification"
    file_folder = "file_folder"
    news_article = "news_article"
    budget = "budget"
    invoice = "invoice"
    presentation = "presentation"
    questionnaire = "questionnaire"
    resume = "resume"
    memo = "memo"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BatchOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: BatchStatus
    document_count: int
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    batch_id: str
    blob_key: str
    created_at: datetime


class PredictionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    batch_id: str  # matches predictions.batch_id FK; needed for cache invalidation
    document_id: str
    label: PredictionLabel
    top1_confidence: float
    top5: list[tuple[PredictionLabel, float]]
    overlay_url: str | None = None
    model_version: str  # matches predictions.model_version; required for model-swap tracking
    created_at: datetime | None = None


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    actor_id: str
    action: str
    target: str
    metadata: dict[str, Any] | None = None
    timestamp: datetime


class ClassifyJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_id: str
    document_id: str
    blob_key: str
    request_id: str
