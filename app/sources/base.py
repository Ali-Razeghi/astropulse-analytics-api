"""The data-source abstraction.

This is the architectural centrepiece. Every provider -- an external HTTP API,
a synthetic generator, or (in future) a message queue -- implements the same
tiny contract: validate its parameters into a typed model, then turn them into
a list of :class:`NormalizedPoint`.

Because the rest of the system only ever sees ``NormalizedPoint``, adding a new
source is *open for extension, closed for modification*: you write one new
subclass and register it. Nothing else changes.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import ClassVar

import httpx
from pydantic import BaseModel

from app.core.exceptions import UpstreamError
from app.schemas.datapoint import NormalizedPoint

# httpx accepts scalar query values; this alias keeps the transport typed.
QueryValue = str | int | float | bool | None


class DataSource[P: BaseModel](ABC):
    """Contract shared by all data providers."""

    #: Stable identifier used in URLs and the ``data_points.source`` column.
    name: ClassVar[str]
    #: Pydantic model validating this source's parameters.
    params_model: type[P]

    @abstractmethod
    async def collect(self, params: P) -> list[NormalizedPoint]:
        """Fetch and normalise data, returning canonical points.

        ``params`` is already validated. Implementations translate any
        transport/parse failure into :class:`UpstreamError`.
        """
        raise NotImplementedError


class HttpDataSource[P: BaseModel](DataSource[P]):
    """Base for sources backed by an HTTP API.

    The ``httpx.AsyncClient`` is injected rather than created internally so
    that tests can mock the transport and production can share one pooled
    client across requests.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def _get_json(self, path: str, params: Mapping[str, QueryValue]) -> object:
        """GET a JSON document, mapping every failure to ``UpstreamError``.

        This covers connection/timeout errors, non-2xx responses, and bodies
        that are not valid JSON -- so a flaky upstream never leaks a raw,
        untranslated exception to the caller.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            response = await self._client.get(url, params=dict(params))
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise UpstreamError(
                f"{self.name} returned HTTP {exc.response.status_code}.",
                details={"url": url},
            ) from exc
        except httpx.HTTPError as exc:  # timeouts, DNS, connection resets
            raise UpstreamError(
                f"{self.name} is unreachable.",
                details={"url": url, "reason": str(exc)},
            ) from exc

        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise UpstreamError(
                f"{self.name} returned a non-JSON body.",
                details={"url": url},
            ) from exc
