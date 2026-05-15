from __future__ import annotations

from app.domain.contracts import AuditLogEntry
from app.repositories.interfaces import IAuditRepository
from app.services.interfaces import IAuditService


class AuditService(IAuditService):
    def __init__(self, audit_repository: IAuditRepository) -> None:
        self._audit_repository = audit_repository

    async def record(
        self,
        actor_id: str | None,
        action: str,
        target: str,
        metadata: dict | None = None,
    ) -> AuditLogEntry:
        return await self._audit_repository.insert(
            actor_id=actor_id,
            action=action,
            target=target,
            metadata=metadata,
        )
