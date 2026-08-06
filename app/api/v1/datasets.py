"""CSV dataset upload and profiling endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.dataset import DatasetProfile
from app.services.csv_service import profile_csv

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/upload",
    response_model=DatasetProfile,
    summary="Upload a CSV and receive a one-time structural + statistical profile",
    description=(
        "Parses the uploaded CSV in memory and returns a profile. Note: the "
        "file and profile are **not persisted** in this version -- the returned "
        "`dataset_id` is not retrievable later. Persistence is on the roadmap."
    ),
)
async def upload_dataset(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> DatasetProfile:
    raw = await file.read()
    return profile_csv(file.filename or "upload.csv", raw)
