"""Declarative base and shared column mixins.

SQLAlchemy 2.0 typed ORM style (``Mapped`` / ``mapped_column``) is used
throughout for full static-type support.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative base for all ORM models."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` audit columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
