"""Security primitives: password hashing and JWT encode/decode.

We use ``bcrypt`` directly (rather than through passlib) to avoid the
well-known passlib/bcrypt 4.x version-detection warnings, and ``PyJWT`` for
tokens. Keeping these concerns in one small module makes them easy to audit.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with a per-password random salt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Returns ``False`` (instead of raising) on malformed hashes so that an
    attacker cannot distinguish "user not found" from "bad hash" by the
    error behaviour.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(
    subject: str | int,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    ``subject`` is stored in the standard ``sub`` claim (as a string, per the
    JWT spec). ``extra_claims`` can carry non-sensitive metadata such as the
    user role.
    """
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.

    Raises ``jwt.PyJWTError`` (or a subclass) on any validation failure,
    including expiry and signature mismatch. Callers are expected to translate
    that into an HTTP 401.
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
