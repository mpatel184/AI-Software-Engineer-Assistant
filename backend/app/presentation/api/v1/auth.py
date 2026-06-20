"""Authentication endpoints: register, login, refresh, logout, me."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Response, status

from app.application.use_cases.auth.service import TokenPair
from app.core.config import get_settings
from app.domain.entities.user import User
from app.domain.exceptions import AuthenticationError
from app.presentation.deps import AuthServiceDep, CurrentUser
from app.presentation.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, pair: TokenPair) -> None:
    settings = get_settings()
    max_age = int((pair.refresh.expires_at - datetime.now(UTC)).total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=pair.refresh.token,
        max_age=max_age,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(user: User, pair: TokenPair) -> TokenResponse:
    expires_in = int((pair.access.expires_at - datetime.now(UTC)).total_seconds())
    return TokenResponse(
        access_token=pair.access.token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> UserResponse:
    user = await service.register(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, service: AuthServiceDep, response: Response
) -> TokenResponse:
    user, pair = await service.authenticate(email=payload.email, password=payload.password)
    _set_refresh_cookie(response, pair)
    return _token_response(user, pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    service: AuthServiceDep,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
) -> TokenResponse:
    if not refresh_token:
        raise AuthenticationError("Missing refresh token.")
    user, pair = await service.refresh(raw_refresh_token=refresh_token)
    _set_refresh_cookie(response, pair)
    return _token_response(user, pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    service: AuthServiceDep,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
) -> Response:
    await service.logout(raw_refresh_token=refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
