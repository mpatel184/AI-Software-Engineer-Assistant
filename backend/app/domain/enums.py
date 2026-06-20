"""Domain enumerations shared across entities and persistence.

Defined as str-backed enums so they serialize cleanly and map to native
PostgreSQL ENUM types via SQLAlchemy.
"""
from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
