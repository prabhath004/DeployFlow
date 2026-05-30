from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "DeployFlow"
    environment: Literal["local", "aws-hybrid", "aws-demo"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # Phase 2 — PostgreSQL
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    database_url: str = (
        "postgresql+asyncpg://deployflow:deployflow@localhost:5433/deployflow"
    )
    db_echo: bool = False
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)

    # Phase 3 — Auth
    # Override in .env: any random 32+ byte string. Never commit a real secret.
    jwt_secret: str = "dev-secret-change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = Field(default=60 * 24, ge=1)  # 24h default

    # Phase 5 — Redis
    redis_url: str = "redis://localhost:6380/0"
    cache_deployment_status_ttl: int = Field(default=10, ge=1)        # seconds, PRD §9.6
    cache_project_metadata_ttl: int = Field(default=60, ge=1)
    cache_dashboard_summary_ttl: int = Field(default=30, ge=1)
    rate_limit_deploy_per_minute: int = Field(default=10, ge=1)        # per user
    worker_heartbeat_ttl: int = Field(default=30, ge=1)                # seconds


@lru_cache
def get_settings() -> Settings:
    return Settings()
