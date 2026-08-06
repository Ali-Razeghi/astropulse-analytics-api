"""Analytics and raw-series read endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.datapoint_repository import DataPointRepository
from app.schemas.analytics import (
    CorrelationResult,
    MovingAverageResult,
    SeriesSummary,
)
from app.schemas.datapoint import DataPointRead
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get(
    "/data/series",
    response_model=list[DataPointRead],
    summary="Read a raw stored series",
)
async def read_series(
    source: str,
    series_key: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=1000, ge=1, le=10_000),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DataPointRead]:
    rows = await DataPointRepository(session).get_series(
        source, series_key, start=start, end=end, limit=limit
    )
    return [DataPointRead.model_validate(r) for r in rows]


@router.get(
    "/analytics/summary",
    response_model=SeriesSummary,
    summary="Descriptive statistics for a series",
)
async def summary(
    source: str,
    series_key: str,
    start: datetime | None = None,
    end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SeriesSummary:
    return await AnalyticsService(session).summary(
        source, series_key, start=start, end=end
    )


@router.get(
    "/analytics/moving-average",
    response_model=MovingAverageResult,
    summary="Rolling moving average of a series",
)
async def moving_average(
    source: str,
    series_key: str,
    window: int = Query(ge=1, le=365),
    start: datetime | None = None,
    end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> MovingAverageResult:
    return await AnalyticsService(session).moving_average(
        source, series_key, window=window, start=start, end=end
    )


@router.get(
    "/analytics/correlation",
    response_model=CorrelationResult,
    summary="Pearson correlation between two series",
)
async def correlation(
    source_a: str,
    series_key_a: str,
    source_b: str,
    series_key_b: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CorrelationResult:
    return await AnalyticsService(session).correlation(
        source_a, series_key_a, source_b, series_key_b
    )
