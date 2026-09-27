"""
Warp Ladger — Application Configuration
All settings loaded from environment variables with full type safety.
"""
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "Warp Ladger"
    APP_VERSION: str = "0.1.0"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Argon2id parameters (OWASP recommended)
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536  # 64 MiB
    ARGON2_PARALLELISM: int = 2

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://warpladger:warpladger_dev@localhost:5432/warpladger"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── File Storage ─────────────────────────────────────────
    STORAGE_BACKEND: Literal["minio", "s3", "r2", "memory"] = "minio"
    STORAGE_BUCKET_NAME: str = "warpladger"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-1"
    AWS_S3_BUCKET: str = ""

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""

    # ── Email ─────────────────────────────────────────────────
    EMAIL_BACKEND: Literal["console", "smtp"] = "console"
    EMAIL_FROM_ADDRESS: str = "noreply@warpladger.com"
    EMAIL_FROM_NAME: str = "Warp Ladger"
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # ── Rate Limiting ─────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 120

    # ── Locale / Currency ─────────────────────────────────────
    DEFAULT_CURRENCY: str = "GBP"
    DEFAULT_LOCALE: str = "en-GB"
    DEFAULT_TIMEZONE: str = "Europe/London"

    # ── Logging ───────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # ── Feature Flags ───────────────────────────────────────────────
    FEATURE_MFA_ENABLED: bool = False
    FEATURE_OAUTH_ENABLED: bool = False
    FEATURE_PASSKEYS_ENABLED: bool = False

    # ── Phase 5: Document Processing ───────────────────────────
    # Provider selection: "fake" (dev/test) | "google_document_ai" | "azure_document_intelligence"
    DOCUMENT_PROVIDER: str = "fake"

    # File size limits (MB)
    DOCUMENT_MAX_IMAGE_SIZE_MB: int = 20
    DOCUMENT_MAX_PDF_SIZE_MB: int = 50
    DOCUMENT_MAX_PAGES: int = 50

    # Allowed MIME types for upload (comma-separated in env, list in code)
    DOCUMENT_ALLOWED_MIMES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    ]

    # Google Document AI
    GOOGLE_DOCUMENT_AI_PROJECT: str = ""
    GOOGLE_DOCUMENT_AI_LOCATION: str = "eu"
    GOOGLE_DOCUMENT_AI_PROCESSOR_ID: str = ""

    # Confidence thresholds (configurable — calibrate against real test data)
    EXTRACTION_CONFIDENCE_HIGH: float = 0.95
    EXTRACTION_CONFIDENCE_MEDIUM: float = 0.80
    EXTRACTION_CLASSIFICATION_MIN: float = 0.70  # below this → NEEDS_MANUAL_REVIEW

    # Duplicate detection thresholds
    DOCUMENT_DUPLICATE_WARN_SCORE: int = 70   # ≥ 70 → warn
    DOCUMENT_DUPLICATE_BLOCK_SCORE: int = 90  # ≥ 90 → block (requires override)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
