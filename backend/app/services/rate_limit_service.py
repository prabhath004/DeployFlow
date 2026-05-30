from redis.asyncio import Redis

from app.core.config import Settings


class RateLimitExceededError(Exception):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


class RateLimitService:
    """Fixed-window counter: 1 key per (action, subject, current minute).

    `INCR` is atomic, so two concurrent calls cannot both believe they were
    the first. The TTL is set only on the first call (when count == 1), so
    the window starts at first use and naturally expires.
    """

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def hit_deploy(self, user_id: str) -> None:
        limit = self.settings.rate_limit_deploy_per_minute
        window = 60
        key = f"rl:deploy:{user_id}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, window)
        if count > limit:
            ttl = await self.redis.ttl(key)
            raise RateLimitExceededError(retry_after_seconds=max(ttl, 1))
