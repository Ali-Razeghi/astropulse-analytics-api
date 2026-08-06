"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import LoginRequest, Token, UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db),
) -> UserRead:
    user = await AuthService(session).register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token, summary="Log in with JSON body")
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> Token:
    return await AuthService(session).login(payload.email, payload.password)


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 token endpoint (used by the Swagger Authorize button)",
)
async def token(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> Token:
    # OAuth2 form uses ``username``; here it carries the email.
    return await AuthService(session).login(form.username, form.password)
