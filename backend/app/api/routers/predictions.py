from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_audit_service,
    get_current_user,
    get_prediction_repo,
    require_role,
)
from app.domain.contracts import PredictionLabel, PredictionOut, UserOut
from app.repositories.interfaces import IPredictionRepository
from app.services.interfaces import IAuditService
from app.services.prediction_service import PredictionService
from pydantic import BaseModel

router = APIRouter(tags=["predictions"])


def _svc(
    repo: IPredictionRepository = Depends(get_prediction_repo),
    audit: IAuditService = Depends(get_audit_service),
) -> PredictionService:
    return PredictionService(repo, audit)


class _RelabelRequest(BaseModel):
    new_label: PredictionLabel


@router.get(
    "/predictions/recent",
    response_model=list[PredictionOut],
    dependencies=[Depends(require_role("read_batch"))],
)
async def list_recent(svc: PredictionService = Depends(_svc)) -> list[PredictionOut]:
    return await svc.list_recent()


@router.patch(
    "/predictions/{pid}/label",
    response_model=PredictionOut,
    dependencies=[Depends(require_role("relabel_prediction"))],
)
async def relabel(
    pid: str,
    body: _RelabelRequest,
    current_user: UserOut = Depends(get_current_user),
    svc: PredictionService = Depends(_svc),
) -> PredictionOut:
    return await svc.relabel(current_user, pid, body.new_label)
