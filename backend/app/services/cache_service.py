"""Thin cache helpers. Source of truth is always Postgres — these keys are
disposable speed-ups and are allowed to be missing or stale."""

from redis.asyncio import Redis

from app.core.config import Settings


def _deployment_status_key(deployment_id: str) -> str:
    return f"deployment:{deployment_id}:status"


class CacheService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def get_deployment_status(self, deployment_id: str) -> str | None:
        return await self.redis.get(_deployment_status_key(deployment_id))

    async def set_deployment_status(self, deployment_id: str, status: str) -> None:
        await self.redis.set(
            _deployment_status_key(deployment_id),
            status,
            ex=self.settings.cache_deployment_status_ttl,
        )

    async def invalidate_deployment_status(self, deployment_id: str) -> None:
        await self.redis.delete(_deployment_status_key(deployment_id))
