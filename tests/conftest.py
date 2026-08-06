"""Shared test fixtures.

Tests run against an in-memory async SQLite database (fast, isolated, no
external service) and never touch a real network: external sources are mocked
with ``respx``. The app's ``get_db`` dependency is overridden so that every
test shares one session bound to the in-memory schema.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

# Single shared in-memory DB for the test session. ``cache=shared`` keeps the
# same in-memory database across connections in the pool.
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """An HTTP client wired to the app, with the DB dependency overridden."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as sess:
            yield sess

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register + log in a user and return a ready-to-use Authorization header."""
    creds = {"email": "tester@example.com", "password": "supersecret1"}
    await client.post("/api/v1/auth/register", json=creds)
    resp = await client.post("/api/v1/auth/login", json=creds)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
