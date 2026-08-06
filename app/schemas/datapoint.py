"""Schemas for normalized points, ingestion and reads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NormalizedPoint(BaseModel):
    """The canonical shape every data source must emit.

    This is the contract between the source layer and the rest of the system.
    A source's only job is to turn its idiosyncratic payload into a list of
    these.
    """

    series_key: str
    ts: datetime
    value: float
    unit: str | None = None
    meta: dict[str, Any] | None = None


class IngestResponse(BaseModel):
    source: str
    series_keys: list[str]
    points_ingested: int


class DataPointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    series_key: str
    ts: datetime
    value: float
    unit: str | None


class SeriesQuery(BaseModel):
    """Common filter for reading a single series over a time window."""

    source: str
    series_key: str
    start: datetime | None = None
    end: datetime | None = None
    limit: int = Field(default=1000, ge=1, le=10_000)
