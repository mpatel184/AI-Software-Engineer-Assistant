"""JWT token service implementing the TokenService port (python-jose)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.application.interfaces.security import IssuedToken, TokenClaims, TokenService
from app.core.config import Settings
from app.domain.enums import TokenType
from app.domain.exceptions import AuthenticationError


class JwtTokenService(TokenService):
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = timedelta(minutes=settings.access_token_expire_minutes)
        self._refresh_ttl = timedelta(days=settings.refresh_token_expire_days)

    def create_access_token(self, subject: uuid.UUID) -> IssuedToken:
        return self._create(subject, TokenType.ACCESS, self._access_ttl)

    def create_refresh_token(self, subject: uuid.UUID) -> IssuedToken:
        return self._create(subject, TokenType.REFRESH, self._refresh_ttl)

    def decode(self, token: str, *, expected_type: TokenType) -> TokenClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            raise AuthenticationError("Could not validate credentials.") from exc

        if payload.get("type") != expected_type.value:
            raise AuthenticationError("Invalid token type.")

        try:
            subject = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("Malformed token subject.") from exc

        return TokenClaims(
            subject=subject,
            token_type=expected_type,
            jti=payload.get("jti", ""),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )

    def _create(
        self, subject: uuid.UUID, token_type: TokenType, ttl: timedelta
    ) -> IssuedToken:
        now = datetime.now(UTC)
        expires_at = now + ttl
        jti = uuid.uuid4().hex
        payload = {
            "sub": str(subject),
            "type": token_type.value,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return IssuedToken(token=token, expires_at=expires_at, jti=jti)
