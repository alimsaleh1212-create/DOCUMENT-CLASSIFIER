from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.domain.contracts import AuditLogEntry
from app.services.interfaces import IAuditService


class FakeAuditService(IAuditService):
    """In-memory IAuditService that collects records for assertion in tests."""

    def __init__(self) -> None:
        self.records: list[AuditLogEntry] = []

    async def record(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            actor_id=actor_id,
            action=action,
            target=target,
            metadata=metadata,
            timestamp=datetime.now(UTC),
        )
        self.records.append(entry)
        return entry
