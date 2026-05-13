from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.contracts import (
    AuditLogEntry,
    BatchOut,
    PredictionLabel,
    PredictionOut,
    Role,
    UserOut,
)


class IUserService(ABC):
    @abstractmethod
    async def get_me(self, user_id: str) -> UserOut: ...

    @abstractmethod
    async def list_users(self) -> list[UserOut]: ...

    @abstractmethod
    async def toggle_role(self, actor: UserOut, target_uid: str, new_role: Role) -> UserOut: ...


class IBatchService(ABC):
    @abstractmethod
    async def list_batches(self) -> list[BatchOut]: ...

    @abstractmethod
    async def get_batch(self, batch_id: str) -> BatchOut: ...


class IPredictionService(ABC):
    @abstractmethod
    async def record_prediction(
        self, prediction: PredictionOut, request_id: str
    ) -> PredictionOut: ...

    @abstractmethod
    async def list_recent(self) -> list[PredictionOut]: ...

    @abstractmethod
    async def get(self, prediction_id: str) -> PredictionOut: ...

    @abstractmethod
    async def relabel(
        self, actor: UserOut, prediction_id: str, new_label: PredictionLabel
    ) -> PredictionOut: ...


class IAuditService(ABC):
    @abstractmethod
    async def record(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry: ...
