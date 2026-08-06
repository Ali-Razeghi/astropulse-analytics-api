"""Authentication and user-management business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        """Create a new user, enforcing email uniqueness."""
        if await self._users.get_by_email(data.email):
            raise ConflictError("A user with this email already exists.")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        user = await self._users.create(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        """Return the user if credentials are valid, else raise 401.

        The same generic error is returned whether the email is unknown or the
        password is wrong, to avoid user-enumeration.
        """
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")
        return user

    async def login(self, email: str, password: str) -> Token:
        user = await self.authenticate(email, password)
        token = create_access_token(user.id, extra_claims={"role": user.role.value})
        return Token(access_token=token)
