from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_audit_service, get_current_user, get_user_repo, require_role
from app.domain.contracts import Role, UserOut
from app.repositories.interfaces import IUserRepository
from app.services.interfaces import IAuditService
from app.services.user_service import UserService

router = APIRouter(tags=["users"])


def _svc(
    user_repo: IUserRepository = Depends(get_user_repo),
    audit: IAuditService = Depends(get_audit_service),
) -> UserService:
    return UserService(user_repo, audit)


class _ToggleRoleRequest(BaseModel):
    new_role: Role


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: UserOut = Depends(get_current_user),
    svc: UserService = Depends(_svc),
) -> UserOut:
    return await svc.get_me(current_user.id)


@router.get(
    "/users",
    response_model=list[UserOut],
    dependencies=[Depends(require_role("invite_user"))],
)
async def list_users(svc: UserService = Depends(_svc)) -> list[UserOut]:
    return await svc.list_users()


@router.patch(
    "/users/{uid}/role",
    response_model=UserOut,
    dependencies=[Depends(require_role("toggle_role"))],
)
async def toggle_role(
    uid: str,
    body: _ToggleRoleRequest,
    current_user: UserOut = Depends(get_current_user),
    svc: UserService = Depends(_svc),
) -> UserOut:
    return await svc.toggle_role(current_user, uid, body.new_role)
