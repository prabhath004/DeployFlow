"""Real-time log fanout via Redis Pub/Sub.

Worker publishes to `logs:{deployment_id}`. The SSE endpoint in the API
subscribes to the same channel and streams lines to the client. The
DB is the durable record — Pub/Sub is fire-and-forget; if no one is
listening, the message is just dropped.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from redis.asyncio import Redis


def _channel(deployment_id: str) -> str:
    return f"logs:{deployment_id}"


class LogStreamService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def publish(
        self,
        *,
        deployment_id: str,
        level: str,
        source: str,
        message: str,
    ) -> None:
        payload = json.dumps(
            {
                "level": level,
                "source": source,
                "message": message,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self.redis.publish(_channel(deployment_id), payload)

    async def subscribe(
        self, deployment_id: str
    ) -> AsyncIterator[dict[str, str]]:
        """Yields log dicts as they arrive. Caller is responsible for closing
        the iterator (which the SSE endpoint does on client disconnect)."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(_channel(deployment_id))
        try:
            async for raw in pubsub.listen():
                if raw.get("type") != "message":
                    continue
                try:
                    yield json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    continue
        finally:
            await pubsub.unsubscribe(_channel(deployment_id))
            await pubsub.aclose()
