"""Application configuration loaded from environment variables.

All settings are validated by pydantic-settings. Secrets are never hard-coded;
they must be supplied via environment (see .env.example).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # NoDecode: keep pydantic-settings from JSON-decoding this list field so a
    # plain comma-separated value (e.g. in .env) reaches the validator below.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

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

    # --- LLM — Primary provider (default: Gemini 2.5 Flash via Google AI Studio) ---
    # Swap base URL / key / model to target any OpenAI-compatible API.
    llm_provider: Literal["openai", "gemini", "qwen", "claude"] = "openai"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_api_key: str = "your_google_aistudio_api_key_here"
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    # guided_json (vLLM only) | json_schema (Gemini/OpenAI) | ollama_format | json_object (fallback)
    llm_structured_mode: Literal[
        "guided_json", "json_schema", "ollama_format", "json_object"
    ] = "json_schema"
    llm_request_timeout: int = 120

    # --- LLM — Fallback provider (Z.ai GLM) ---
    # Set FALLBACK_PROVIDER=glm and supply GLM_API_KEY to enable automatic fallback.
    # Leave GLM_API_KEY empty (default) to disable fallback entirely.
    fallback_provider: Literal["glm", "none"] = "none"
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm_model: str = "glm-4-flash"
    glm_structured_mode: Literal[
        "guided_json", "json_schema", "ollama_format", "json_object"
    ] = "json_object"

    # --- LLM — Retry / fallback tuning ---
    llm_max_retries: int = 3          # attempts on the primary before switching
    llm_retry_backoff: float = 2.0    # base seconds for exponential backoff

    # --- Embeddings ---
    # Supports both local (sentence-transformers) and remote (OpenAI-compatible) providers
    embedding_provider: Literal["local", "openai_compat"] = "openai_compat"
    # Local provider settings
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    local_embedding_device: str | None = None  # None = auto-detect (cuda if available, else cpu)
    local_embedding_normalize: bool = True
    # Remote provider settings (OpenAI-compatible /embeddings endpoint)
    # Defaults to Google text-embedding-004 via the same Gemini API key.
    # Set EMBEDDING_BASE_URL / EMBEDDING_API_KEY to override independently.
    embedding_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    embedding_model: str = "text-embedding-004"
    # Falls back to the LLM API key when EMBEDDING_API_KEY is not set.
    embedding_api_key: str = ""
    retrieval_top_k: int = 6

    # --- Vector store (ChromaDB) ---
    chroma_host: str = "chroma"
    chroma_port: int = 8000

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

    @field_validator("embedding_api_key", mode="after")
    @classmethod
    def default_embedding_api_key(cls, v: str, info: object) -> str:  # type: ignore[override]
        """Fall back to llm_api_key when EMBEDDING_API_KEY is not set."""
        if not v:
            # info.data is populated with already-validated fields
            data = getattr(info, "data", {})
            return data.get("llm_api_key", v)
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