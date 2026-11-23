from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Finance4Dummies"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    allow_public_registration: bool = True

    jwt_secret_key: str = Field(
        default="change-me-in-production-use-at-least-32-random-bytes",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = (
        "postgresql+asyncpg://finance:finance_dev_password@localhost:5432/finance4dummies"
    )
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("api_v1_prefix")
    @classmethod
    def ensure_leading_slash(cls, value: str) -> str:
        return value if value.startswith("/") else f"/{value}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
