"""Data-access for :class:`~app.models.datapoint.DataPoint`."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.datapoint import DataPoint
from app.schemas.datapoint import NormalizedPoint


class DataPointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete_series(self, source: str, series_key: str) -> int:
        """Delete all points of one series; returns the number removed.

        Used to make ingestion idempotent: re-ingesting a series replaces its
        stored points rather than appending duplicates.
        """
        result = await self._session.execute(
            delete(DataPoint).where(
                DataPoint.source == source,
                DataPoint.series_key == series_key,
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def bulk_insert(
        self,
        source: str,
        points: Sequence[NormalizedPoint],
        *,
        user_id: int | None = None,
    ) -> int:
        """Insert many normalised points; return the number inserted."""
        rows = [
            DataPoint(
                source=source,
                series_key=p.series_key,
                ts=p.ts,
                value=p.value,
                unit=p.unit,
                meta=p.meta,
                user_id=user_id,
            )
            for p in points
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def get_series(
        self,
        source: str,
        series_key: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[DataPoint]:
        """Return one series ordered chronologically within an optional window."""
        stmt = (
            select(DataPoint)
            .where(DataPoint.source == source, DataPoint.series_key == series_key)
            .order_by(DataPoint.ts.asc())
            .limit(limit)
        )
        if start is not None:
            stmt = stmt.where(DataPoint.ts >= start)
        if end is not None:
            stmt = stmt.where(DataPoint.ts <= end)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
