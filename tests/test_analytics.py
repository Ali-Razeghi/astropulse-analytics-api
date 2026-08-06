from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.datapoint_repository import DataPointRepository
from app.schemas.datapoint import NormalizedPoint
from app.services.analytics_service import AnalyticsService


async def seed(session: AsyncSession, n: int = 20) -> str:
    key = "neo/object_count"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    pts = [
        NormalizedPoint(
            series_key=key,
            ts=start + timedelta(days=i),
            value=float(i + 1),
            unit="objects",
        )
        for i in range(n)
    ]
    await DataPointRepository(session).bulk_insert("neo", pts)
    await session.commit()
    return key


async def test_summary_stats(session: AsyncSession):
    key = await seed(session)
    result = await AnalyticsService(session).summary("neo", key)
    assert result.count == 20 and result.pct_change and result.pct_change > 0


async def test_moving_average(session: AsyncSession):
    key = await seed(session)
    result = await AnalyticsService(session).moving_average("neo", key, window=5)
    assert result.points[3].moving_average is None
    assert math.isclose(result.points[4].moving_average, 3.0)


async def test_correlation(session: AsyncSession):
    key = await seed(session)
    result = await AnalyticsService(session).correlation("neo", key, "neo", key)
    assert result.overlapping_points == 20 and math.isclose(
        result.correlation or 0, 1.0
    )
