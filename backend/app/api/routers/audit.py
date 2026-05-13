from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_audit_repo, require_role
from app.domain.contracts import AuditLogEntry
from app.repositories.interfaces import IAuditRepository

router = APIRouter(tags=["audit"])


@router.get(
    "/audit",
    response_model=list[AuditLogEntry],
    dependencies=[Depends(require_role("read_audit"))],
)
async def list_audit(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    audit_repo: IAuditRepository = Depends(get_audit_repo),
) -> list[AuditLogEntry]:
    return await audit_repo.list(page=page, limit=limit)
