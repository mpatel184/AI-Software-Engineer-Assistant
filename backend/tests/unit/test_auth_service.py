"""Unit tests for AuthService using in-memory fakes (no DB, no framework)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.application.interfaces.security import IssuedToken, TokenClaims
from app.application.use_cases.auth.service import AuthService, _hash_token
from app.domain.entities.user import User
from app.domain.enums import TokenType, UserRole
from app.domain.exceptions import AlreadyExistsError, AuthenticationError


class FakeUserRepo:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, User] = {}

    async def get_by_id(self, user_id):
        return self._by_id.get(user_id)

    async def get_by_email(self, email):
        return next((u for u in self._by_id.values() if u.email == email), None)

    async def create(self, user):
        self._by_id[user.id] = user
        return user


class FakeRefreshRepo:
    def __init__(self) -> None:
        self.active: dict[str, tuple[uuid.UUID, datetime]] = {}

    async def add(self, *, user_id, token_hash, expires_at):
        self.active[token_hash] = (user_id, expires_at)

    async def get_active(self, token_hash):
        return self.active.get(token_hash)

    async def revoke(self, token_hash):
        self.active.pop(token_hash, None)

    async def revoke_all_for_user(self, user_id):
        self.active = {h: v for h, v in self.active.items() if v[0] != user_id}


class FakeHasher:
    def hash(self, plain):
        return f"hashed::{plain}"

    def verify(self, plain, hashed):
        return hashed == f"hashed::{plain}"


class FakeTokens:
    def create_access_token(self, subject):
        return IssuedToken(f"access::{subject}", datetime.now(UTC) + timedelta(minutes=15), "a")

    def create_refresh_token(self, subject):
        return IssuedToken(
            f"refresh::{subject}::{uuid.uuid4()}",
            datetime.now(UTC) + timedelta(days=7),
            "r",
        )

    def decode(self, token, *, expected_type):
        subject = uuid.UUID(token.split("::")[1])
        return TokenClaims(subject, expected_type, "x", datetime.now(UTC) + timedelta(days=7))


def make_service():
    return AuthService(
        users=FakeUserRepo(),
        refresh_tokens=FakeRefreshRepo(),
        hasher=FakeHasher(),
        tokens=FakeTokens(),
    )


async def test_register_creates_member_user():
    svc = make_service()
    user = await svc.register(email="Test@Example.com", password="secret123", full_name="T")
    assert user.email == "test@example.com"  # normalized
    assert user.role is UserRole.MEMBER
    assert user.password_hash == "hashed::secret123"


async def test_register_rejects_duplicate_email():
    svc = make_service()
    await svc.register(email="a@b.com", password="secret123", full_name=None)
    with pytest.raises(AlreadyExistsError):
        await svc.register(email="a@b.com", password="secret123", full_name=None)


async def test_authenticate_success_returns_token_pair():
    svc = make_service()
    await svc.register(email="a@b.com", password="secret123", full_name=None)
    user, pair = await svc.authenticate(email="a@b.com", password="secret123")
    assert pair.access.token.startswith("access::")
    assert pair.refresh.token.startswith("refresh::")
    assert user.email == "a@b.com"


async def test_authenticate_wrong_password_raises():
    svc = make_service()
    await svc.register(email="a@b.com", password="secret123", full_name=None)
    with pytest.raises(AuthenticationError):
        await svc.authenticate(email="a@b.com", password="wrongpass1")


async def test_authenticate_unknown_user_raises():
    svc = make_service()
    with pytest.raises(AuthenticationError):
        await svc.authenticate(email="ghost@b.com", password="secret123")


async def test_refresh_rotates_and_invalidates_old_token():
    svc = make_service()
    await svc.register(email="a@b.com", password="secret123", full_name=None)
    _, pair = await svc.authenticate(email="a@b.com", password="secret123")
    old = pair.refresh.token

    _, new_pair = await svc.refresh(raw_refresh_token=old)
    assert new_pair.refresh.token != old

    # Reusing the old (now-rotated) token must fail.
    with pytest.raises(AuthenticationError):
        await svc.refresh(raw_refresh_token=old)


async def test_logout_revokes_refresh_token():
    svc = make_service()
    await svc.register(email="a@b.com", password="secret123", full_name=None)
    _, pair = await svc.authenticate(email="a@b.com", password="secret123")

    await svc.logout(raw_refresh_token=pair.refresh.token)
    with pytest.raises(AuthenticationError):
        await svc.refresh(raw_refresh_token=pair.refresh.token)


def test_hash_token_is_deterministic_sha256():
    assert _hash_token("abc") == _hash_token("abc")
    assert len(_hash_token("abc")) == 64
