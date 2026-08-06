"""Tests for CSV upload and profiling."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.exceptions import ValidationAppError
from app.services.csv_service import profile_csv

SAMPLE_CSV = (
    b"date,category,revenue\n"
    b"2026-01-01,A,100\n"
    b"2026-01-02,A,200\n"
    b"2026-01-02,A,200\n"
    b"2026-01-03,B,\n"
)


def test_profile_counts_and_stats() -> None:
    profile = profile_csv("sales.csv", SAMPLE_CSV)
    assert profile.rows == 4
    assert profile.columns == 3
    assert profile.duplicate_rows == 1  # row 3 duplicates row 2
    assert profile.missing_values == 1  # empty revenue on last row

    revenue = next(c for c in profile.column_profiles if c.name == "revenue")
    assert revenue.max == 200.0
    assert revenue.min == 100.0


def test_rejects_non_csv_extension() -> None:
    try:
        profile_csv("data.txt", SAMPLE_CSV)
    except ValidationAppError as exc:
        assert exc.code == "INVALID_FILE_FORMAT"
    else:  # pragma: no cover
        raise AssertionError("expected ValidationAppError")


async def test_upload_endpoint(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sales.csv", SAMPLE_CSV, "text/csv")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["duplicate_rows"] == 1
