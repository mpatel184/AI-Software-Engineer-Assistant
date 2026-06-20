"""Argon2 password hasher implementing the PasswordHasher port."""
from __future__ import annotations

from passlib.context import CryptContext


class Argon2PasswordHasher:
    """Argon2id hashing. No length limit (unlike bcrypt's 72 bytes)."""

    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["argon2"], deprecated="auto")

    def hash(self, plain: str) -> str:
        return self._ctx.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return self._ctx.verify(plain, hashed)
        except (ValueError, TypeError):
            return False
