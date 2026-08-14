"""Environment-driven application settings.

Credentials and runtime options are loaded from environment variables
(or a local .env file). Nothing secret is hard-coded here.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the WorkPulse API."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"
    DEV_SEED_PASSWORD: str | None = None
    DEVICE_TOKEN_EXPIRE_MINUTES: int = 60
    AGENT_EVENT_MAX_BATCH: int = 100
    AGENT_EVENT_MAX_FUTURE_SECONDS: int = 7200
    AGENT_EVENT_MAX_AGE_DAYS: int = 400

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_postgresql(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must be set")
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("SECRET_KEY must be set")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.ENVIRONMENT.lower() == "production":
            if not origins or "*" in origins:
                raise ValueError("CORS_ORIGINS must be an explicit allowlist in production")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
