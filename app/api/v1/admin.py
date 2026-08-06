"""Admin-only endpoints.

These make the role model real: they are guarded by ``require_admin``, so a
regular ``user`` token receives HTTP 403. This is the minimal, honest form of
role-based access control -- a foundation the roadmap extends to more routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import RoleUpdate, UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="List all users (admin only)",
)
async def list_users(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserRead]:
    users = await UserRepository(session).list_all()
    return [UserRead.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserRead,
    summary="Change a user's role (admin only)",
)
async def set_user_role(
    user_id: int,
    payload: RoleUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserRead:
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.", details={"user_id": user_id})
    user.role = payload.role
    saved = await repo.save(user)
    await session.commit()
    return UserRead.model_validate(saved)
