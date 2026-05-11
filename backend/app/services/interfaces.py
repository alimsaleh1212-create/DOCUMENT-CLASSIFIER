from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.contracts import (
    AuditLogEntry,
    BatchOut,
    PredictionLabel,
    PredictionOut,
    UserOut,
)


class IUserService(ABC):
    @abstractmethod
    async def get_me(self, user_id: str) -> UserOut: ...

    @abstractmethod
    async def list_users(self) -> list[UserOut]: ...

    @abstractmethod
    async def toggle_role(self, actor_id: str, target_uid: str, new_role: str) -> UserOut: ...


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
        self, actor_id: str, prediction_id: str, new_label: PredictionLabel
    ) -> PredictionOut: ...


class IAuditService(ABC):
    @abstractmethod
    async def record(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict | None = None,
    ) -> AuditLogEntry: ...
