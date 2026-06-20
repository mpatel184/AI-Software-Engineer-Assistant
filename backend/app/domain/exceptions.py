"""Domain-level exceptions.

These are pure (no framework imports) and are mapped to HTTP responses by the
presentation layer's exception handlers. Each carries a stable error code so the
frontend can react programmatically.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected, handled domain errors."""

    code: str = "domain_error"
    status: int = 400

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    code = "not_found"
    status = 404


class AlreadyExistsError(DomainError):
    code = "already_exists"
    status = 409


class ValidationError(DomainError):
    code = "validation_error"
    status = 422


class AuthenticationError(DomainError):
    code = "authentication_error"
    status = 401


class AuthorizationError(DomainError):
    code = "authorization_error"
    status = 403


class RateLimitError(DomainError):
    code = "rate_limited"
    status = 429


class ExternalServiceError(DomainError):
    """Upstream failure (Claude, git, vector store)."""

    code = "external_service_error"
    status = 502


class ConflictError(DomainError):
    code = "conflict"
    status = 409
