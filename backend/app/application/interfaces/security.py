"""Ports for password hashing and token issuance.

The application layer depends on these abstractions; concrete implementations
live in infrastructure (argon2 hasher, JWT service).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.enums import TokenType


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...
    def verify(self, plain: str, hashed: str) -> bool: ...


@dataclass(slots=True)
class TokenClaims:
    subject: uuid.UUID
    token_type: TokenType
    jti: str
    expires_at: datetime


@dataclass(slots=True)
class IssuedToken:
    token: str
    expires_at: datetime
    jti: str


class TokenService(Protocol):
    def create_access_token(self, subject: uuid.UUID) -> IssuedToken: ...
    def create_refresh_token(self, subject: uuid.UUID) -> IssuedToken: ...
    def decode(self, token: str, *, expected_type: TokenType) -> TokenClaims: ...
