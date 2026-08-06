"""Data-access for :class:`~app.models.user.User`.

The repository pattern isolates SQL from business logic. Services depend on
this class, never on raw queries, which keeps them testable and makes a future
storage change (or query optimisation) a one-file concern.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        result = await self._session.execute(
            select(User).order_by(User.id.asc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()  # populate PK without committing
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user
