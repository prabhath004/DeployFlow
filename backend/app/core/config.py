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

    # Phase 8 — Queue backend selection + AWS SQS
    queue_backend: Literal["redis", "sqs"] = "redis"
    aws_region: str = "us-east-1"
    # For LocalStack / dev: set AWS_ENDPOINT_URL=http://localhost:4566
    # In prod, leave this None so boto3 hits real AWS.
    aws_endpoint_url: str | None = None
    sqs_queue_url: str | None = None
    sqs_dlq_url: str | None = None
    sqs_visibility_timeout: int = Field(default=60, ge=1)   # how long a worker has to ack
    sqs_wait_time_seconds: int = Field(default=20, ge=0, le=20)  # long-poll

    # Phase 9 — S3 + ECR
    artifacts_backend: Literal["none", "s3"] = "none"
    s3_artifacts_bucket: str | None = None
    s3_artifacts_prefix: str = "deployments/"
    ecr_repository_uri: str | None = None    # e.g. 1234.dkr.ecr.us-east-1.amazonaws.com/deployflow

    # Real deployment target — ECS Fargate. Disabled for local-only mode.
    deploy_backend: Literal["none", "ecs"] = "none"
    deployed_app_port: int = Field(default=8000, ge=1, le=65535)
    deploy_image_platform: str = "linux/arm64"
    ecs_cluster_name: str | None = None
    ecs_subnet_ids: str | None = None          # comma-separated subnet IDs
    ecs_security_group_id: str | None = None
    ecs_task_execution_role_arn: str | None = None
    ecs_app_log_group: str | None = None
    ecs_task_cpu: int = Field(default=256, ge=256)
    ecs_task_memory: int = Field(default=512, ge=512)
    ecs_cpu_architecture: Literal["ARM64", "X86_64"] = "ARM64"


@lru_cache
def get_settings() -> Settings:
    return Settings()
