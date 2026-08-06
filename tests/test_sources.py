from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import ValidationError

from app.sources.exoplanets import ExoplanetMetric, ExoplanetParams, NasaExoplanetSource
from app.sources.neo import NasaNeoSource, NeoMetric, NeoParams
from app.sources.space_weather import (
    NasaDonkiSource,
    SpaceWeatherMetric,
    SpaceWeatherParams,
    flare_score,
)


@respx.mock
async def test_neo_daily_closest_distance():
    respx.get(url__regex=r".*/feed").mock(
        return_value=httpx.Response(
            200,
            json={
                "near_earth_objects": {
                    "2026-07-01": [
                        {
                            "is_potentially_hazardous_asteroid": True,
                            "close_approach_data": [
                                {
                                    "miss_distance": {"kilometers": "1000"},
                                    "relative_velocity": {
                                        "kilometers_per_hour": "50000"
                                    },
                                }
                            ],
                        },
                        {
                            "is_potentially_hazardous_asteroid": False,
                            "close_approach_data": [
                                {
                                    "miss_distance": {"kilometers": "800"},
                                    "relative_velocity": {
                                        "kilometers_per_hour": "30000"
                                    },
                                }
                            ],
                        },
                    ]
                }
            },
        )
    )
    async with httpx.AsyncClient() as c:
        pts = await NasaNeoSource(
            c, "https://api.nasa.gov/neo/rest/v1", "DEMO_KEY"
        ).collect(NeoParams(metric=NeoMetric.CLOSEST_MISS_DISTANCE_KM))
    assert pts[0].value == 800 and pts[0].meta["hazardous_count"] == 1


@respx.mock
async def test_donki_flare_score_normalisation():
    respx.get(url__regex=r".*/FLR").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"beginTime": "2026-07-01T10:00Z", "classType": "M2.5"},
                {"beginTime": "2026-07-01T12:00Z", "classType": "C9.0"},
            ],
        )
    )
    async with httpx.AsyncClient() as c:
        pts = await NasaDonkiSource(
            c, "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get"
        ).collect(SpaceWeatherParams(metric=SpaceWeatherMetric.FLARE_MAX_CLASS_SCORE))
    assert pts[0].value == 25.0
    assert flare_score("X1.2") == 120.0


@respx.mock
async def test_exoplanet_yearly_discovery_count():
    respx.get(url__regex=r".*/sync").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"disc_year": 2025, "pl_name": "A"},
                {"disc_year": 2025, "pl_name": "B"},
                {"disc_year": 2026, "pl_name": "C"},
            ],
        )
    )
    async with httpx.AsyncClient() as c:
        pts = await NasaExoplanetSource(
            c, "https://exoplanetarchive.ipac.caltech.edu/TAP"
        ).collect(
            ExoplanetParams(
                start_year=2025, end_year=2026, metric=ExoplanetMetric.DISCOVERIES
            )
        )
    assert [p.value for p in pts] == [2.0, 1.0]


def test_param_validation():
    with pytest.raises(ValidationError):
        NeoParams(days=8)
    with pytest.raises(ValidationError):
        ExoplanetParams(start_year=2026, end_year=2020)
