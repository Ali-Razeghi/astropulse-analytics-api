"""Aggregate all v1 routers under a single object."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, analytics, auth, datasets, ingestion, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(ingestion.router)
api_router.include_router(analytics.router)
api_router.include_router(datasets.router)
