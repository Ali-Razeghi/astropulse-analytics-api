"""Construction registry for the three astronomy providers."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.sources.base import DataSource
from app.sources.exoplanets import NasaExoplanetSource
from app.sources.neo import NasaNeoSource
from app.sources.space_weather import NasaDonkiSource

AnySource = DataSource[Any]
SOURCE_NAMES = (NasaNeoSource.name, NasaDonkiSource.name, NasaExoplanetSource.name)


def build_sources(client: httpx.AsyncClient) -> dict[str, AnySource]:
    sources: list[AnySource] = [
        NasaNeoSource(client, settings.nasa_neo_base_url, settings.nasa_api_key),
        NasaDonkiSource(client, settings.nasa_donki_base_url),
        NasaExoplanetSource(client, settings.nasa_exoplanet_base_url),
    ]
    return {s.name: s for s in sources}


def get_source(name: str, client: httpx.AsyncClient) -> AnySource:
    sources = build_sources(client)
    try:
        return sources[name]
    except KeyError as exc:
        raise NotFoundError(
            f"Unknown data source '{name}'.", details={"available": sorted(sources)}
        ) from exc


def available_source_names() -> list[str]:
    return sorted(SOURCE_NAMES)
