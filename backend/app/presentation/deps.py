"""Dependency-injection providers wiring HTTP requests to use cases.

Keeps the composition root in one place: repositories, security adapters, and
services are assembled here and injected into routers.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.security import PasswordHasher, TokenService
from app.application.use_cases.auth.service import AuthService
from app.core.config import Settings, get_settings
from app.domain.entities.user import User
from app.domain.enums import TokenType
from app.domain.exceptions import AuthenticationError
from app.infrastructure.auth.jwt_service import JwtTokenService
from app.infrastructure.auth.password import Argon2PasswordHasher
from app.infrastructure.db.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.db.session import get_session

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Stateless singletons. Settings is itself a cached singleton (get_settings),
# so the token service can be built once lazily and reused.
_password_hasher = Argon2PasswordHasher()
_token_service_singleton: JwtTokenService | None = None


def get_password_hasher() -> PasswordHasher:
    return _password_hasher


def get_token_service(settings: SettingsDep) -> TokenService:
    global _token_service_singleton
    if _token_service_singleton is None:
        _token_service_singleton = JwtTokenService(settings)
    return _token_service_singleton


def get_auth_service(
    session: SessionDep,
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        hasher=hasher,
        tokens=tokens,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    tokens: Annotated[TokenService, Depends(get_token_service)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication credentials were not provided.")

    claims = tokens.decode(credentials.credentials, expected_type=TokenType.ACCESS)
    user = await SqlAlchemyUserRepository(session).get_by_id(claims.subject)
    if user is None or not user.is_active:
        raise AuthenticationError("User account is invalid or disabled.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
