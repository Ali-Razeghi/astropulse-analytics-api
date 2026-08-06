"""Application factory and ASGI entrypoint.

Run locally with::

    uvicorn app.main:app --reload

Interactive docs are then available at ``/docs`` (Swagger UI) and ``/redoc``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    """Build and configure the FastAPI application (app-factory pattern).

    Using a factory (rather than a module-level app) makes it trivial to spin
    up isolated instances in tests and to vary configuration per environment.
    """
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Astronomy data integration and analytics platform using NASA NeoWs, "
            "CCMC DONKI and the NASA Exoplanet Archive."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["system"], summary="Liveness/readiness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.get("/", tags=["system"], include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "docs": "/docs"}

    return app


app = create_app()
