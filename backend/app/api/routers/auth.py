from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import create_access_token, hash_password, verify_password
from app.api.deps import get_session, get_user_repo
from app.domain.contracts import Role, UserCreate, UserOut
from app.repositories.interfaces import IUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


class _LoginBody(UserCreate):
    pass


class _TokenOut(UserOut):
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_repo: IUserRepository = Depends(get_user_repo),
) -> UserOut:
    """Register a new user. The first registrant is automatically promoted to admin."""
    if await user_repo.get_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    hashed = hash_password(body.password)
    admin_count = await user_repo.count_admins()
    role = Role.admin if admin_count == 0 else Role.reviewer
    user = await user_repo.create_user(body.email, hashed, role=role)
    await session.commit()
    return user


@router.post("/jwt/login", response_model=_TokenOut)
async def login(
    body: _LoginBody,
    request: Request,
    user_repo: IUserRepository = Depends(get_user_repo),
) -> _TokenOut:
    """Authenticate with email + password, receive a JWT access token."""
    user = await user_repo.get_by_email(body.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    stored_hash = await _get_hashed_password(user_repo, user.id)
    if not verify_password(body.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    signing_key: str = request.app.state.jwt_signing_key
    token = create_access_token(user.id, signing_key)
    return _TokenOut(**user.model_dump(), access_token=token)


async def _get_hashed_password(repo: IUserRepository, user_id: str) -> str:
    """
    Retrieve the stored hashed password for a user.

    In production this is fetched from the DB via the real UserRepository.
    FakeUserRepo exposes get_hashed_password() for the fake mode.
    """
    if hasattr(repo, "get_hashed_password"):
        result = repo.get_hashed_password(user_id)  # type: ignore[no-any-return]
        # Handle both sync and async implementations
        if hasattr(result, "__await__"):
            return await result
        return result
    # Production repositories must expose this; if they don't, raise early.
    raise NotImplementedError(
        "IUserRepository implementation must expose get_hashed_password(user_id)"
    )
