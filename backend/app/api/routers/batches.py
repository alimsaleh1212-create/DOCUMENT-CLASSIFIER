from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_batch_repo, require_role
from app.domain.contracts import BatchOut
from app.repositories.interfaces import IBatchRepository
from app.services.batch_service import BatchService

router = APIRouter(tags=["batches"])


def _svc(repo: IBatchRepository = Depends(get_batch_repo)) -> BatchService:
    return BatchService(repo)


@router.get(
    "/batches",
    response_model=list[BatchOut],
    dependencies=[Depends(require_role("read_batch"))],
)
async def list_batches(svc: BatchService = Depends(_svc)) -> list[BatchOut]:
    return await svc.list_batches()


@router.get(
    "/batches/{bid}",
    response_model=BatchOut,
    dependencies=[Depends(require_role("read_batch"))],
)
async def get_batch(bid: str, svc: BatchService = Depends(_svc)) -> BatchOut:
    return await svc.get_batch(bid)
