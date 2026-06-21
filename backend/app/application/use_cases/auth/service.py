"""Authentication use cases.

Orchestrates registration, login, token refresh (with rotation), and logout.
Depends only on application-layer ports — no framework or ORM imports — so it is
fully unit-testable with fakes.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from app.application.interfaces.repositories import RefreshTokenRepository, UserRepository
from app.application.interfaces.security import IssuedToken, PasswordHasher, TokenService
from app.domain.entities.user import User
from app.domain.enums import TokenType, UserRole
from app.domain.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    NotFoundError,
)


@dataclass(slots=True)
class TokenPair:
    access: IssuedToken
    refresh: IssuedToken


def _hash_token(raw: str) -> str:
    """Deterministic hash for at-rest refresh-token storage (lookup key)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._tokens = tokens

    async def register(self, *, email: str, password: str, full_name: str | None) -> User:
        normalized = email.strip().lower()
        if await self._users.get_by_email(normalized) is not None:
            raise AlreadyExistsError("An account with this email already exists.")

        user = User(
            id=uuid.uuid4(),
            email=normalized,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
            role=UserRole.MEMBER,
            is_active=True,
            is_verified=False,
        )
        return await self._users.create(user)

    async def update_profile(
        self, *, user_id: uuid.UUID, full_name: str | None
    ) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        user.full_name = full_name
        return await self._users.update(user)

    async def change_password(
        self, *, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        if not self._hasher.verify(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")

        user.password_hash = self._hasher.hash(new_password)
        await self._users.update(user)
        # Invalidate existing sessions: refresh tokens must be re-issued via login.
        await self._refresh_tokens.revoke_all_for_user(user_id)

    async def authenticate(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self._users.get_by_email(email.strip().lower())
        # Verify even when user is missing to reduce timing/enumeration signal.
        candidate_hash = user.password_hash if user else self._hasher.hash("placeholder")
        password_ok = self._hasher.verify(password, candidate_hash)

        if user is None or not password_ok:
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")

        pair = await self._issue_pair(user.id)
        return user, pair

    async def refresh(self, *, raw_refresh_token: str) -> tuple[User, TokenPair]:
        claims = self._tokens.decode(raw_refresh_token, expected_type=TokenType.REFRESH)
        token_hash = _hash_token(raw_refresh_token)

        active = await self._refresh_tokens.get_active(token_hash)
        if active is None:
            # Token reuse or unknown token: revoke the whole family defensively.
            await self._refresh_tokens.revoke_all_for_user(claims.subject)
            raise AuthenticationError("Refresh token is invalid or has been revoked.")

        user = await self._users.get_by_id(claims.subject)
        if user is None or not user.is_active:
            await self._refresh_tokens.revoke_all_for_user(claims.subject)
            raise AuthenticationError("User account is invalid or disabled.")

        # Rotate: revoke the presented token, then issue a fresh pair.
        await self._refresh_tokens.revoke(token_hash)
        pair = await self._issue_pair(user.id)
        return user, pair

    async def logout(self, *, raw_refresh_token: str | None) -> None:
        if not raw_refresh_token:
            return
        await self._refresh_tokens.revoke(_hash_token(raw_refresh_token))

    async def _issue_pair(self, user_id: uuid.UUID) -> TokenPair:
        access = self._tokens.create_access_token(user_id)
        refresh = self._tokens.create_refresh_token(user_id)
        await self._refresh_tokens.add(
            user_id=user_id,
            token_hash=_hash_token(refresh.token),
            expires_at=refresh.expires_at,
        )
        return TokenPair(access=access, refresh=refresh)
