"""Schemas for analytics outputs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SeriesSummary(BaseModel):
    """Descriptive statistics for a single stored series."""

    source: str
    series_key: str
    count: int
    first_ts: datetime | None
    last_ts: datetime | None
    first_value: float | None
    last_value: float | None
    min_value: float | None
    max_value: float | None
    mean_value: float | None
    std_value: float | None
    pct_change: float | None  # (last - first) / first * 100


class MovingAveragePoint(BaseModel):
    ts: datetime
    value: float
    moving_average: float | None


class MovingAverageResult(BaseModel):
    source: str
    series_key: str
    window: int
    points: list[MovingAveragePoint]


class CorrelationResult(BaseModel):
    """Pearson correlation between two aligned series."""

    series_a: str
    series_b: str
    overlapping_points: int
    correlation: float | None
