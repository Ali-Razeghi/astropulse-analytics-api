"""NASA Exoplanet Archive TAP adapter with discovery-year aggregation."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from statistics import median

from pydantic import BaseModel, Field, model_validator

from app.core.exceptions import UpstreamError
from app.schemas.datapoint import NormalizedPoint
from app.sources.base import HttpDataSource


class ExoplanetMetric(StrEnum):
    DISCOVERIES = "discoveries"
    MEDIAN_RADIUS_EARTH = "median_radius_earth"
    MEDIAN_ORBITAL_PERIOD_DAYS = "median_orbital_period_days"


class ExoplanetParams(BaseModel):
    start_year: int = Field(default=2010, ge=1990, le=2100)
    end_year: int = Field(default=2026, ge=1990, le=2100)
    metric: ExoplanetMetric = ExoplanetMetric.DISCOVERIES

    @model_validator(mode="after")
    def validate_years(self) -> ExoplanetParams:
        if self.start_year > self.end_year:
            raise ValueError("start_year must not exceed end_year")
        return self


class NasaExoplanetSource(HttpDataSource[ExoplanetParams]):
    name = "exoplanets"
    params_model = ExoplanetParams

    async def collect(self, params: ExoplanetParams) -> list[NormalizedPoint]:
        column = {
            ExoplanetMetric.DISCOVERIES: "pl_name",
            ExoplanetMetric.MEDIAN_RADIUS_EARTH: "pl_rade",
            ExoplanetMetric.MEDIAN_ORBITAL_PERIOD_DAYS: "pl_orbper",
        }[params.metric]
        query = (
            f"select disc_year,{column} from pscomppars "
            f"where disc_year between {params.start_year} and {params.end_year}"
        )
        payload = await self._get_json("sync", {"query": query, "format": "json"})
        if not isinstance(payload, list):
            raise UpstreamError("Unexpected NASA Exoplanet Archive payload shape.")

        yearly: dict[int, list[float]] = defaultdict(list)
        for row in payload:
            if not isinstance(row, dict):
                continue
            try:
                year = int(row["disc_year"])
                if params.metric is ExoplanetMetric.DISCOVERIES:
                    yearly[year].append(1.0)
                elif row.get(column) is not None:
                    yearly[year].append(float(row[column]))
            except (KeyError, TypeError, ValueError):
                continue

        unit = {
            ExoplanetMetric.DISCOVERIES: "planets",
            ExoplanetMetric.MEDIAN_RADIUS_EARTH: "Earth radii",
            ExoplanetMetric.MEDIAN_ORBITAL_PERIOD_DAYS: "days",
        }[params.metric]
        points = []
        for year, values in sorted(yearly.items()):
            value = (
                float(len(values))
                if params.metric is ExoplanetMetric.DISCOVERIES
                else float(median(values))
            )
            points.append(
                NormalizedPoint(
                    series_key=f"exoplanets/{params.metric.value}",
                    ts=datetime(year, 1, 1, tzinfo=UTC),
                    value=value,
                    unit=unit,
                    meta={"year": year, "records": len(values)},
                )
            )
        return points
