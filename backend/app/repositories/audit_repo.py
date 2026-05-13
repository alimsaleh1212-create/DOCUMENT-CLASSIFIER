from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.domain.contracts import AuditLogEntry
from app.repositories._mapping import audit_log_to_domain, metadata_or_none, parse_uuid
from app.repositories.interfaces import IAuditRepository


class AuditRepository(IAuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        audit_log = models.AuditLog(
            actor_id=parse_uuid(actor_id),
            action=action,
            target=target,
            metadata_=metadata_or_none(metadata),
        )
        self._session.add(audit_log)
        await self._session.flush()
        await self._session.refresh(audit_log)
        return audit_log_to_domain(audit_log)
