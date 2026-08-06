"""Analytics computed over stored series.

These functions are what turn the project from a fetch-and-echo proxy into an
*analytics* platform. Pandas is used for the numeric work because it expresses
these operations clearly and is a skill worth demonstrating; for very large
series one would push aggregation into SQL instead (noted in the README).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.datapoint import DataPoint
from app.repositories.datapoint_repository import DataPointRepository
from app.schemas.analytics import (
    CorrelationResult,
    MovingAveragePoint,
    MovingAverageResult,
    SeriesSummary,
)


def _to_frame(rows: list[DataPoint]) -> pd.DataFrame:
    return pd.DataFrame({"ts": [r.ts for r in rows], "value": [r.value for r in rows]})


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._points = DataPointRepository(session)

    async def _load(
        self,
        source: str,
        series_key: str,
        start: datetime | None,
        end: datetime | None,
    ) -> list[DataPoint]:
        rows = await self._points.get_series(source, series_key, start=start, end=end)
        if not rows:
            raise NotFoundError(
                "No data found for the requested series.",
                details={"source": source, "series_key": series_key},
            )
        return rows

    async def summary(
        self,
        source: str,
        series_key: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> SeriesSummary:
        rows = await self._load(source, series_key, start, end)
        frame = _to_frame(rows)
        values = frame["value"]
        first_value = float(values.iloc[0])
        last_value = float(values.iloc[-1])
        pct_change = (
            (last_value - first_value) / first_value * 100 if first_value != 0 else None
        )
        # std has no meaning for a single point; pandas returns NaN there.
        std = values.std()
        return SeriesSummary(
            source=source,
            series_key=series_key,
            count=int(values.count()),
            first_ts=rows[0].ts,
            last_ts=rows[-1].ts,
            first_value=first_value,
            last_value=last_value,
            min_value=float(values.min()),
            max_value=float(values.max()),
            mean_value=float(values.mean()),
            std_value=None if pd.isna(std) else float(std),
            pct_change=pct_change,
        )

    async def moving_average(
        self,
        source: str,
        series_key: str,
        *,
        window: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> MovingAverageResult:
        if window < 1:
            raise ValidationAppError("`window` must be a positive integer.")
        rows = await self._load(source, series_key, start, end)
        frame = _to_frame(rows)
        frame["ma"] = frame["value"].rolling(window=window, min_periods=window).mean()

        points = [
            MovingAveragePoint(
                ts=row.ts,
                value=float(row.value),
                moving_average=None if pd.isna(ma) else float(ma),
            )
            for row, ma in zip(rows, frame["ma"], strict=True)
        ]
        return MovingAverageResult(
            source=source, series_key=series_key, window=window, points=points
        )

    async def correlation(
        self,
        source_a: str,
        series_key_a: str,
        source_b: str,
        series_key_b: str,
    ) -> CorrelationResult:
        """Pearson correlation between two series, aligned by day.

        Series are resampled to daily frequency and inner-joined so that only
        overlapping timestamps contribute -- comparing misaligned series would
        be meaningless.
        """
        rows_a = await self._load(source_a, series_key_a, None, None)
        rows_b = await self._load(source_b, series_key_b, None, None)

        frame_a = _to_frame(rows_a).set_index("ts").resample("D").mean()
        frame_b = _to_frame(rows_b).set_index("ts").resample("D").mean()
        joined = frame_a.join(frame_b, lsuffix="_a", rsuffix="_b", how="inner").dropna()

        n = int(len(joined))
        corr: float | None = None
        if n >= 2:
            corr_value = joined["value_a"].corr(joined["value_b"])
            corr = None if pd.isna(corr_value) else float(corr_value)

        return CorrelationResult(
            series_a=f"{source_a}:{series_key_a}",
            series_b=f"{source_b}:{series_key_b}",
            overlapping_points=n,
            correlation=corr,
        )
