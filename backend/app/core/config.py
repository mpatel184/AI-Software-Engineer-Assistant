"""Application configuration loaded from environment variables.

All settings are validated by pydantic-settings. Secrets are never hard-coded;
they must be supplied via environment (see .env.example).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "AI Software Engineer Assistant"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Server / CORS ---
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Database ---
    database_url: PostgresDsn
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # --- Redis (Celery broker + cache + rate limit) ---
    redis_url: RedisDsn

    # --- Auth / JWT ---
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- Claude / AI ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 4096

    # --- Vector store ---
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # --- Repository storage ---
    repo_storage_path: str = "/data/repos"
    max_repo_size_mb: int = 500
    report_storage_path: str = "/data/reports"

    # --- Rate limiting ---
    rate_limit_per_minute: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sync_database_url(self) -> str:
        """Sync DSN for Alembic (psycopg2)."""
        return str(self.database_url).replace("+asyncpg", "").replace(
            "postgresql://", "postgresql+psycopg2://"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
