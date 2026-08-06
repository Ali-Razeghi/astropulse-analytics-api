"""Ingestion orchestration: validate -> source -> normalise -> persist.

The service is deliberately thin. All source-specific logic lives in the source
classes; all persistence lives in the repository. This class validates the
caller's parameters against the source's own schema, then wires collection to
storage and owns the transaction boundary.

Ingestion is **idempotent per series**: re-ingesting a series replaces its
stored points instead of appending duplicates (backed by a unique constraint on
``(source, series_key, ts)``).
"""

from __future__ import annotations

import httpx
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NoDataError, ValidationAppError
from app.repositories.datapoint_repository import DataPointRepository
from app.schemas.datapoint import IngestResponse, NormalizedPoint
from app.sources.registry import get_source


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._points = DataPointRepository(session)

    async def ingest(
        self,
        source_name: str,
        params: dict[str, object],
        *,
        user_id: int | None = None,
    ) -> IngestResponse:
        """Collect from one source and store the resulting points.

        The current sources all provide *public astronomy data*, so ``user_id`` is
        left ``None`` (global). The parameter exists for future private sources
        (e.g. a CSV imported as a personal series), where ownership matters.
        """
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            source = get_source(source_name, client)

            # Validate raw params against the source's own schema. Invalid
            # input fails fast here with a clear 422, before any network call.
            try:
                validated = source.params_model.model_validate(params)
            except ValidationError as exc:
                raise ValidationAppError(
                    f"Invalid parameters for source '{source_name}'.",
                    details=exc.errors(include_url=False),
                ) from exc

            points: list[NormalizedPoint] = await source.collect(validated)

        if not points:
            raise NoDataError(
                f"Source '{source_name}' returned no data for the requested parameters."
            )

        # Idempotent replace: clear each affected series, then insert fresh.
        for series_key in sorted({p.series_key for p in points}):
            await self._points.delete_series(source_name, series_key)

        inserted = await self._points.bulk_insert(source_name, points, user_id=user_id)
        await self._session.commit()

        series_keys = sorted({p.series_key for p in points})
        return IngestResponse(
            source=source_name,
            series_keys=series_keys,
            points_ingested=inserted,
        )
