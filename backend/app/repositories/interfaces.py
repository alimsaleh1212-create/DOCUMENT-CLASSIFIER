from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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


class IUserRepository(ABC):
    @abstractmethod
    async def create_user(
        self, email: str, hashed_password: str, role: Role = Role.reviewer
    ) -> UserOut: ...

    @abstractmethod
    async def get(self, user_id: str) -> UserOut: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> UserOut | None: ...

    @abstractmethod
    async def list_users(self) -> list[UserOut]: ...

    @abstractmethod
    async def update_role(self, user_id: str, new_role: Role) -> UserOut: ...

    @abstractmethod
    async def count_admins(self) -> int: ...

    @abstractmethod
    async def delete(self, user_id: str) -> None: ...


class IBatchRepository(ABC):
    @abstractmethod
    async def list_batches(self) -> list[BatchOut]: ...

    @abstractmethod
    async def get(self, batch_id: str) -> BatchOut: ...

    @abstractmethod
    async def update_status(self, batch_id: str, status: BatchStatus) -> BatchOut: ...


class IDocumentRepository(ABC):
    @abstractmethod
    async def ensure_for_ingest(
        self,
        batch_id: str,
        document_id: str,
        blob_key: str,
    ) -> DocumentOut: ...


class IPredictionRepository(ABC):
    @abstractmethod
    async def create_idempotent(self, prediction: PredictionOut) -> PredictionOut: ...

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> list[PredictionOut]: ...

    @abstractmethod
    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        label_filter: PredictionLabel | None = None,
        color_filter: str | None = None,
    ) -> list[PredictionOut]: ...

    @abstractmethod
    async def get(self, prediction_id: str) -> PredictionOut: ...

    @abstractmethod
    async def update_label(
        self, prediction_id: str, new_label: PredictionLabel
    ) -> PredictionOut: ...

    @abstractmethod
    async def update_comment(
        self,
        prediction_id: str,
        comment: str | None,
        comment_color: str | None,
    ) -> PredictionOut: ...


class IAuditRepository(ABC):
    @abstractmethod
    async def insert(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry: ...

    @abstractmethod
    async def list(self, page: int = 1, limit: int = 50) -> list[AuditLogEntry]: ...
