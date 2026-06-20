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


class RepoSource(str, Enum):
    GITHUB = "github"
    UPLOAD = "upload"


class RepoStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisType(str, Enum):
    ARCHITECTURE = "architecture"
    DEPENDENCIES = "dependencies"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    DEAD_CODE = "dead_code"
    BUGS = "bugs"
    SECURITY = "security"
