from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.domain.contracts import AuditLogEntry
from app.services.audit_service import AuditService


class FakeAuditRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def insert(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict | None = None,
    ) -> AuditLogEntry:
        self.calls.append(
            {
                "actor_id": actor_id,
                "action": action,
                "target": target,
                "metadata": metadata,
            }
        )
        return AuditLogEntry(
            id=str(uuid.uuid4()),
            actor_id=actor_id,
            action=action,
            target=target,
            metadata=metadata,
            timestamp=datetime.now().astimezone(),
        )


@pytest.mark.asyncio
async def test_audit_service_delegates_to_repository() -> None:
    repository = FakeAuditRepository()
    service = AuditService(repository)  # type: ignore[arg-type]

    result = await service.record(
        actor_id="actor-1",
        action="role_change",
        target="users/user-1",
        metadata={"role": "admin"},
    )

    assert result.actor_id == "actor-1"
    assert repository.calls == [
        {
            "actor_id": "actor-1",
            "action": "role_change",
            "target": "users/user-1",
            "metadata": {"role": "admin"},
        }
    ]
