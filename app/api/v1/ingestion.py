"""Astronomy source discovery and ingestion endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.openapi.models import Example
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.datapoint import IngestResponse
from app.services.ingestion_service import IngestionService
from app.sources.registry import available_source_names

router = APIRouter(tags=["data-sources"])
_INGEST_EXAMPLES: dict[str, Example] = {
    "neo": Example(
        summary="NASA Near-Earth Objects",
        value={"days": 7, "metric": "closest_miss_distance_km"},
    ),
    "space-weather": Example(
        summary="NASA DONKI space weather",
        value={"days": 30, "metric": "flare_max_class_score"},
    ),
    "exoplanets": Example(
        summary="NASA Exoplanet Archive",
        value={"start_year": 2010, "end_year": 2026, "metric": "discoveries"},
    ),
}


@router.get("/sources", summary="List available data sources")
async def list_sources() -> dict[str, list[str]]:
    return {"sources": available_source_names()}


@router.post(
    "/ingest/{source_name}",
    response_model=IngestResponse,
    summary="Fetch astronomy data and store normalized points",
)
async def ingest(
    source_name: str,
    params: dict[str, Any] = Body(
        default_factory=dict, openapi_examples=_INGEST_EXAMPLES
    ),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IngestResponse:
    return await IngestionService(session).ingest(source_name, params)
