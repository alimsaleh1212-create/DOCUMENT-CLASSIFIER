"""
JWT + password helpers used by the auth router.

Uses pwdlib (same library as fastapi-users v13) and pyjwt[crypto].
Kept separate from deps.py so that the token format can change without
touching the dependency injection logic.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

_pwd = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"
JWT_LIFETIME_SECONDS = 3600


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(user_id: str, signing_key: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=JWT_LIFETIME_SECONDS),
    }
    return jwt.encode(payload, signing_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, signing_key: str) -> dict[str, object]:
    """Raises jwt.InvalidTokenError on bad/expired tokens."""
    return jwt.decode(token, signing_key, algorithms=[JWT_ALGORITHM])
