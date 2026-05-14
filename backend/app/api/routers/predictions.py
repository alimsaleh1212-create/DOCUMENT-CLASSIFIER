from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

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

router = APIRouter(tags=["predictions"])


def _svc(
    repo: IPredictionRepository = Depends(get_prediction_repo),
    audit: IAuditService = Depends(get_audit_service),
) -> PredictionService:
    return PredictionService(repo, audit)


class _RelabelRequest(BaseModel):
    new_label: PredictionLabel


class _CommentRequest(BaseModel):
    comment: str | None = None
    comment_color: str | None = None


class _RenameRequest(BaseModel):
    document_name: str | None = None


@router.get(
    "/predictions/recent",
    response_model=list[PredictionOut],
    dependencies=[Depends(require_role("read_batch"))],
)
async def list_recent(svc: PredictionService = Depends(_svc)) -> list[PredictionOut]:
    return await svc.list_recent()


@router.get(
    "/predictions",
    response_model=list[PredictionOut],
    dependencies=[Depends(require_role("read_batch"))],
)
async def list_predictions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    label: PredictionLabel | None = Query(default=None),
    color: str | None = Query(default=None),
    svc: PredictionService = Depends(_svc),
) -> list[PredictionOut]:
    return await svc.list_paginated(page=page, limit=limit, label_filter=label, color_filter=color)


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


@router.patch(
    "/predictions/{pid}/comment",
    response_model=PredictionOut,
    dependencies=[Depends(require_role("add_comment"))],
)
async def add_comment(
    pid: str,
    body: _CommentRequest,
    current_user: UserOut = Depends(get_current_user),
    svc: PredictionService = Depends(_svc),
) -> PredictionOut:
    return await svc.add_comment(current_user, pid, body.comment, body.comment_color)


@router.patch(
    "/predictions/{pid}/name",
    response_model=PredictionOut,
    dependencies=[Depends(require_role("rename_document"))],
)
async def rename_document(
    pid: str,
    body: _RenameRequest,
    current_user: UserOut = Depends(get_current_user),
    svc: PredictionService = Depends(_svc),
) -> PredictionOut:
    return await svc.rename_document(current_user, pid, body.document_name)


@router.get(
    "/predictions/{pid}/overlay",
    dependencies=[Depends(require_role("read_batch"))],
)
async def get_overlay(
    pid: str,
    request: Request,
    svc: PredictionService = Depends(_svc),
) -> Response:
    """Proxy the overlay image bytes from MinIO so the browser never needs
    direct access to the internal MinIO hostname. Returns image bytes inline."""
    prediction = await svc.get(pid)

    if not prediction.overlay_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No overlay generated")

    blob = getattr(request.app.state, "blob", None)
    if blob is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blob storage not configured",
        )

    # overlay_url stored as "overlays/{batch}/{doc}.png" — strip the bucket prefix
    raw = prediction.overlay_url
    key = raw.split("/", 1)[-1] if "/" in raw else raw
    try:
        data = await blob.get("overlays", key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Overlay not found: {exc}"
        ) from exc

    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get(
    "/predictions/{pid}/document-url",
    response_model=dict,
    dependencies=[Depends(require_role("read_batch"))],
)
async def get_document_url(
    pid: str,
    request: Request,
    svc: PredictionService = Depends(_svc),
) -> dict:
    """Return a short-lived presigned URL for the original document and overlay."""
    prediction = await svc.get(pid)

    blob = getattr(request.app.state, "blob", None)
    if blob is None:
        # Dev/fake mode — return keys as-is so the frontend can display something
        return {"overlay_url": prediction.overlay_url, "document_url": None}

    overlay_url = None
    if prediction.overlay_url:
        try:
            key = prediction.overlay_url.split("/", 1)[-1]
            overlay_url = await blob.presigned_get("overlays", key)
        except Exception:
            overlay_url = None

    return {"overlay_url": overlay_url, "document_url": None}
