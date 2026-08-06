"""Tests for registration, login and protected-route access."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.security import hash_password, verify_password

CREDS = {"email": "alice@example.com", "password": "password123"}


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert verify_password("s3cret-pw", hashed) is True
    assert verify_password("wrong", hashed) is False


async def test_register_then_login(client: AsyncClient) -> None:
    reg = await client.post("/api/v1/auth/register", json=CREDS)
    assert reg.status_code == 201
    body = reg.json()
    assert body["email"] == CREDS["email"]
    assert "hashed_password" not in body  # never leak the hash

    login = await client.post("/api/v1/auth/login", json=CREDS)
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


async def test_duplicate_email_conflicts(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=CREDS)
    dup = await client.post("/api/v1/auth/register", json=CREDS)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT"


async def test_login_with_bad_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=CREDS)
    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": CREDS["email"], "password": "nope"},
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "AUTHENTICATION_FAILED"


async def test_me_requires_auth(client: AsyncClient) -> None:
    unauth = await client.get("/api/v1/users/me")
    assert unauth.status_code == 401


async def test_me_returns_profile(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "tester@example.com"
