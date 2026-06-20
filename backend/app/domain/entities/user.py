"""User domain entity — pure, framework-free."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import UserRole


@dataclass(slots=True)
class User:
    id: uuid.UUID
    email: str
    password_hash: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN
