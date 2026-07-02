"""Application settings, loaded from environment / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_secret(path: str) -> str | None:
    p = Path(path)
    if p.exists():
        return p.read_text().strip()
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    environment: str = "development"
    port: int = 8000
    log_level: str = "INFO"

    # Database / broker
    database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    # Compose-style DB construction (used when DATABASE_URL isn't set directly,
    # e.g. in production containers that read the password from a Docker secret)
    postgres_user: str = "postgres"
    postgres_db: str = "mkjobs"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_password_file: str = "/run/secrets/postgres_password"

    # HTTP
    cors_allow_origins: str = "*"
    rate_limit_per_minute: int = 120

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        password = _read_secret(self.postgres_password_file) or ""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allow_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
