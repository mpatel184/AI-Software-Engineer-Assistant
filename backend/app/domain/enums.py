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


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DocumentType(str, Enum):
    README = "readme"
    API_DOCS = "api_docs"
    FUNCTION_DOCS = "function_docs"
    CLASS_DOCS = "class_docs"


class DocumentFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ReportType(str, Enum):
    FULL = "full"
    ANALYSIS = "analysis"
    SECURITY = "security"
    BUGS = "bugs"
