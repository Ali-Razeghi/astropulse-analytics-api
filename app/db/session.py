"""Async SQLAlchemy engine and session management.

The FastAPI dependency ``get_db`` yields a request-scoped ``AsyncSession`` and
guarantees it is closed afterwards. Transaction boundaries are handled by the
service layer, not here, to keep this module free of business logic.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ``future=True`` is implicit in SQLAlchemy 2.0. ``pool_pre_ping`` avoids
# handing out dead connections after a database restart.
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async session (FastAPI dependency)."""
    async with AsyncSessionFactory() as session:
        yield session
