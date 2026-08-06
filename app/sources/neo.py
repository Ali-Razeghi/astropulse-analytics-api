"""NASA NeoWs adapter for daily near-Earth-object analytics."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from statistics import fmean

import httpx
from pydantic import BaseModel, Field

from app.core.exceptions import UpstreamError
from app.schemas.datapoint import NormalizedPoint
from app.sources.base import HttpDataSource


class NeoMetric(StrEnum):
    CLOSEST_MISS_DISTANCE_KM = "closest_miss_distance_km"
    AVERAGE_VELOCITY_KPH = "average_velocity_kph"
    HAZARDOUS_COUNT = "hazardous_count"
    OBJECT_COUNT = "object_count"


class NeoParams(BaseModel):
    days: int = Field(default=7, ge=1, le=7)
    metric: NeoMetric = NeoMetric.CLOSEST_MISS_DISTANCE_KM


class NasaNeoSource(HttpDataSource[NeoParams]):
    name = "neo"
    params_model = NeoParams

    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str) -> None:
        super().__init__(client, base_url)
        self._api_key = api_key

    async def collect(self, params: NeoParams) -> list[NormalizedPoint]:
        end = date.today()
        start = end - timedelta(days=params.days - 1)
        payload = await self._get_json(
            "feed",
            {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "api_key": self._api_key,
            },
        )
        if not isinstance(payload, dict) or not isinstance(
            payload.get("near_earth_objects"), dict
        ):
            raise UpstreamError("Unexpected NASA NeoWs payload shape.")

        points: list[NormalizedPoint] = []
        for day_str, objects in payload["near_earth_objects"].items():
            if not isinstance(objects, list):
                continue
            values: list[float] = []
            hazardous = 0
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                hazardous += int(bool(obj.get("is_potentially_hazardous_asteroid")))
                approaches = obj.get("close_approach_data")
                if not isinstance(approaches, list) or not approaches:
                    continue
                approach = approaches[0]
                try:
                    if params.metric is NeoMetric.CLOSEST_MISS_DISTANCE_KM:
                        values.append(float(approach["miss_distance"]["kilometers"]))
                    elif params.metric is NeoMetric.AVERAGE_VELOCITY_KPH:
                        values.append(
                            float(approach["relative_velocity"]["kilometers_per_hour"])
                        )
                except (KeyError, TypeError, ValueError):
                    continue

            if params.metric is NeoMetric.CLOSEST_MISS_DISTANCE_KM:
                if not values:
                    continue
                value, unit = min(values), "km"
            elif params.metric is NeoMetric.AVERAGE_VELOCITY_KPH:
                if not values:
                    continue
                value, unit = fmean(values), "km/h"
            elif params.metric is NeoMetric.HAZARDOUS_COUNT:
                value, unit = float(hazardous), "objects"
            else:
                value, unit = float(len(objects)), "objects"

            points.append(
                NormalizedPoint(
                    series_key=f"neo/{params.metric.value}",
                    ts=datetime.combine(
                        date.fromisoformat(day_str), time.min, tzinfo=UTC
                    ),
                    value=value,
                    unit=unit,
                    meta={"object_count": len(objects), "hazardous_count": hazardous},
                )
            )
        return sorted(points, key=lambda p: p.ts)
