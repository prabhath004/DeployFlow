"""Worker liveness via short-TTL Redis keys.

Each worker calls `touch()` every few seconds. The key auto-expires if a
worker dies or hangs, so listing live workers is just SCAN with the prefix.

Phase 6 will wire the worker loop to call this. Phase 2's `worker_heartbeats`
table is the durable record; this is the cheap real-time check.
"""

from redis.asyncio import Redis

from app.core.config import Settings


def _hb_key(worker_id: str) -> str:
    return f"worker:hb:{worker_id}"


class HeartbeatService:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def touch(self, worker_id: str, status: str) -> None:
        await self.redis.set(
            _hb_key(worker_id), status, ex=self.settings.worker_heartbeat_ttl
        )

    async def is_alive(self, worker_id: str) -> bool:
        return bool(await self.redis.exists(_hb_key(worker_id)))

    async def list_alive(self) -> dict[str, str]:
        result: dict[str, str] = {}
        async for raw_key in self.redis.scan_iter(match="worker:hb:*", count=100):
            worker_id = raw_key.split(":", 2)[2]
            status = await self.redis.get(raw_key)
            if status is not None:
                result[worker_id] = status
        return result
