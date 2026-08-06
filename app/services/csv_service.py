"""CSV upload profiling.

Demonstrates file handling, pandas-based data validation and defensive error
handling -- the tabular-data half of a multi-source platform (external APIs
being the other half).
"""

from __future__ import annotations

import io
import uuid

import pandas as pd
from pandas.api import types as ptypes

from app.core.exceptions import ValidationAppError
from app.schemas.dataset import ColumnProfile, DatasetProfile

# Guard against decompression-bomb style abuse. Kept small for the MVP.
MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MiB


def profile_csv(filename: str, raw: bytes) -> DatasetProfile:
    """Parse a CSV file and return a structural + statistical profile."""
    if not filename.lower().endswith(".csv"):
        raise ValidationAppError(
            "Only .csv files are accepted.", code="INVALID_FILE_FORMAT"
        )
    if len(raw) > MAX_CSV_BYTES:
        raise ValidationAppError(
            "File exceeds the maximum allowed size.", code="FILE_TOO_LARGE"
        )

    try:
        frame = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - surface any parse failure uniformly
        raise ValidationAppError(
            "The file could not be parsed as CSV.",
            details={"reason": str(exc)},
            code="CSV_PARSE_ERROR",
        ) from exc

    if frame.empty:
        raise ValidationAppError("The CSV file contains no rows.")

    profiles: list[ColumnProfile] = []
    for name in frame.columns:
        col = frame[name]
        is_numeric = ptypes.is_numeric_dtype(col)
        profiles.append(
            ColumnProfile(
                name=str(name),
                dtype=str(col.dtype),
                non_null=int(col.notna().sum()),
                nulls=int(col.isna().sum()),
                unique=int(col.nunique(dropna=True)),
                min=float(col.min()) if is_numeric and col.notna().any() else None,
                max=float(col.max()) if is_numeric and col.notna().any() else None,
                mean=float(col.mean()) if is_numeric and col.notna().any() else None,
            )
        )

    return DatasetProfile(
        dataset_id=uuid.uuid4().hex[:8],
        filename=filename,
        rows=int(len(frame)),
        columns=int(frame.shape[1]),
        missing_values=int(frame.isna().sum().sum()),
        duplicate_rows=int(frame.duplicated().sum()),
        column_profiles=profiles,
    )
