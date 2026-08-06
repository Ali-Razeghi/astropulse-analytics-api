"""Reusable FastAPI dependencies for authentication and authorisation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

# ``tokenUrl`` powers the Swagger "Authorize" dialog (form-based token flow).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer token."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("Could not validate credentials.") from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User no longer exists or is inactive.")
    return user


def require_role(
    *allowed: UserRole,
) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that enforces one of the allowed roles."""

    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise AuthorizationError("Insufficient permissions for this action.")
        return user

    return _dependency


# Convenience: admin-only guard.
require_admin = require_role(UserRole.ADMIN)
