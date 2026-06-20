"""Repository ports for the auth module.

Concrete SQLAlchemy implementations live in infrastructure/db/repositories.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities.user import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def create(self, user: User) -> User: ...


class RefreshTokenRepository(Protocol):
    async def add(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> None: ...
    async def get_active(self, token_hash: str) -> tuple[uuid.UUID, datetime] | None: ...
    async def revoke(self, token_hash: str) -> None: ...
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None: ...
