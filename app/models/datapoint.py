"""Unified time-series storage.

Every value from every source -- asteroid metrics, space-weather events,
exoplanet aggregates, or a column from a user's CSV -- is normalised into a
single ``DataPoint`` shape:

    (source, series_key, ts, value, unit, meta)

This single-table design is what makes the analytics layer generic: one set of
aggregation functions works across all sources. Adding a new source never
requires a schema change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DataPoint(Base, TimestampMixin):
    __tablename__ = "data_points"
    __table_args__ = (
        # The dominant query is "give me one series over a time window",
        # so we index on (source, series_key, ts).
        Index("ix_data_points_series_ts", "source", "series_key", "ts"),
        # A single timestamp within a series must be unique, so re-ingesting
        # cannot create duplicate points that would skew analytics.
        UniqueConstraint("source", "series_key", "ts", name="uq_data_points_series_ts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    series_key: Mapped[str] = mapped_column(String(128), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Nullable owner: astronomy data is global (NULL), CSV series belong to a user.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
