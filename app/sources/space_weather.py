"""NASA DONKI adapter for solar flares, CMEs and geomagnetic storms."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.exceptions import UpstreamError
from app.schemas.datapoint import NormalizedPoint
from app.sources.base import HttpDataSource


class SpaceWeatherMetric(StrEnum):
    FLARE_MAX_CLASS_SCORE = "flare_max_class_score"
    FLARE_COUNT = "flare_count"
    CME_MAX_SPEED_KMS = "cme_max_speed_kms"
    GEOMAGNETIC_MAX_KP = "geomagnetic_max_kp"


class SpaceWeatherParams(BaseModel):
    days: int = Field(default=30, ge=1, le=30)
    metric: SpaceWeatherMetric = SpaceWeatherMetric.FLARE_MAX_CLASS_SCORE


def flare_score(class_type: str) -> float:
    """Map GOES class text to a sortable numeric score: C=1, M=10, X=100."""
    if not class_type:
        return 0.0
    prefix = class_type[0].upper()
    base = {"A": 0.01, "B": 0.1, "C": 1.0, "M": 10.0, "X": 100.0}.get(prefix)
    if base is None:
        return 0.0
    try:
        magnitude = float(class_type[1:])
    except ValueError:
        magnitude = 1.0
    return base * magnitude


class NasaDonkiSource(HttpDataSource[SpaceWeatherParams]):
    name = "space-weather"
    params_model = SpaceWeatherParams

    async def collect(self, params: SpaceWeatherParams) -> list[NormalizedPoint]:
        end = date.today()
        start = end - timedelta(days=params.days - 1)
        endpoint = {
            SpaceWeatherMetric.FLARE_MAX_CLASS_SCORE: "FLR",
            SpaceWeatherMetric.FLARE_COUNT: "FLR",
            SpaceWeatherMetric.CME_MAX_SPEED_KMS: "CME",
            SpaceWeatherMetric.GEOMAGNETIC_MAX_KP: "GST",
        }[params.metric]
        payload = await self._get_json(
            endpoint, {"startDate": start.isoformat(), "endDate": end.isoformat()}
        )
        if not isinstance(payload, list):
            raise UpstreamError("Unexpected NASA DONKI payload shape.")

        daily: dict[date, list[float]] = defaultdict(list)
        for event in payload:
            if not isinstance(event, dict):
                continue
            try:
                if params.metric in {
                    SpaceWeatherMetric.FLARE_MAX_CLASS_SCORE,
                    SpaceWeatherMetric.FLARE_COUNT,
                }:
                    day = datetime.fromisoformat(
                        str(event["beginTime"]).replace("Z", "+00:00")
                    ).date()
                    value = (
                        1.0
                        if params.metric is SpaceWeatherMetric.FLARE_COUNT
                        else flare_score(str(event.get("classType", "")))
                    )
                elif params.metric is SpaceWeatherMetric.CME_MAX_SPEED_KMS:
                    day = datetime.fromisoformat(
                        str(event["startTime"]).replace("Z", "+00:00")
                    ).date()
                    analyses = event.get("cmeAnalyses") or []
                    speeds = [
                        float(a["speed"])
                        for a in analyses
                        if isinstance(a, dict) and a.get("speed") is not None
                    ]
                    if not speeds:
                        continue
                    value = max(speeds)
                else:
                    day = datetime.fromisoformat(
                        str(event["startTime"]).replace("Z", "+00:00")
                    ).date()
                    kp = event.get("allKpIndex") or []
                    values = [
                        float(x["kpIndex"])
                        for x in kp
                        if isinstance(x, dict) and x.get("kpIndex") is not None
                    ]
                    if not values:
                        continue
                    value = max(values)
            except (KeyError, TypeError, ValueError):
                continue
            daily[day].append(value)

        unit = {
            SpaceWeatherMetric.FLARE_MAX_CLASS_SCORE: "GOES score",
            SpaceWeatherMetric.FLARE_COUNT: "events",
            SpaceWeatherMetric.CME_MAX_SPEED_KMS: "km/s",
            SpaceWeatherMetric.GEOMAGNETIC_MAX_KP: "Kp",
        }[params.metric]
        points = []
        for day, values in sorted(daily.items()):
            aggregate = (
                sum(values)
                if params.metric is SpaceWeatherMetric.FLARE_COUNT
                else max(values)
            )
            points.append(
                NormalizedPoint(
                    series_key=f"space-weather/{params.metric.value}",
                    ts=datetime.combine(day, time.min, tzinfo=UTC),
                    value=float(aggregate),
                    unit=unit,
                    meta={"events": len(values)},
                )
            )
        return points
