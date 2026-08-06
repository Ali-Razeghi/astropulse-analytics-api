"""Schemas for CSV upload and profiling."""

from __future__ import annotations

from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null: int
    nulls: int
    unique: int
    # Numeric-only fields; ``None`` for non-numeric columns.
    min: float | None = None
    max: float | None = None
    mean: float | None = None


class DatasetProfile(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    missing_values: int
    duplicate_rows: int
    column_profiles: list[ColumnProfile]
    status: str = "processed"
