"""Queue abstraction. Phase 6 = Redis Streams; Phase 8 will add SQS.

Routes call `publish()`. Workers call `consume()` to get a message, then
`ack()` after successful processing. Unacked messages become visible to
other consumers after a timeout (Redis: XAUTOCLAIM; SQS: visibility timeout).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis


@dataclass(slots=True)
class QueueMessage:
    message_id: str  # opaque handle used to ack
    body: dict[str, Any]


class QueueService(ABC):
    @abstractmethod
    async def publish(self, body: dict[str, Any]) -> str:
        """Publish a job. Returns the message id."""

    @abstractmethod
    async def consume(self, *, consumer: str, block_ms: int) -> QueueMessage | None:
        """Block up to `block_ms` waiting for a message. Returns None on timeout."""

    @abstractmethod
    async def ack(self, message_id: str) -> None:
        """Mark a message as successfully processed."""

    @abstractmethod
    async def reclaim_orphans(self, *, consumer: str, idle_ms: int) -> list[QueueMessage]:
        """Claim messages that were consumed but not ack'd within idle_ms."""


class RedisStreamQueue(QueueService):
    """Redis Streams + consumer groups.

    All workers share one stream + one group, so each message goes to exactly
    one worker. Unacked messages can be reclaimed by another worker via
    XAUTOCLAIM (covers worker crash mid-job).
    """

    STREAM = "deployflow:deployments"
    GROUP = "workers"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def ensure_group(self) -> None:
        """Create the consumer group if it doesn't exist (idempotent)."""
        try:
            await self.redis.xgroup_create(
                self.STREAM, self.GROUP, id="$", mkstream=True
            )
        except Exception as exc:
            # BUSYGROUP means the group already exists — fine.
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish(self, body: dict[str, Any]) -> str:
        return await self.redis.xadd(self.STREAM, {"body": json.dumps(body)})

    async def consume(self, *, consumer: str, block_ms: int) -> QueueMessage | None:
        try:
            result = await self.redis.xreadgroup(
                self.GROUP,
                consumer,
                streams={self.STREAM: ">"},  # ">" = only new (unread) messages
                count=1,
                block=block_ms,
            )
        except Exception as exc:
            # If the stream or group got wiped (e.g. Redis restart, FLUSHDB),
            # recreate them and treat this poll as a timeout.
            if "NOGROUP" in str(exc):
                await self.ensure_group()
                return None
            raise
        if not result:
            return None
        _stream_name, entries = result[0]
        message_id, fields = entries[0]
        return QueueMessage(
            message_id=message_id, body=json.loads(fields["body"])
        )

    async def ack(self, message_id: str) -> None:
        await self.redis.xack(self.STREAM, self.GROUP, message_id)

    async def reclaim_orphans(
        self, *, consumer: str, idle_ms: int
    ) -> list[QueueMessage]:
        try:
            _next_id, claimed, _deleted = await self.redis.xautoclaim(
                self.STREAM,
                self.GROUP,
                consumer,
                min_idle_time=idle_ms,
                count=10,
            )
        except Exception as exc:
            if "NOGROUP" in str(exc):
                await self.ensure_group()
                return []
            raise
        out: list[QueueMessage] = []
        for message_id, fields in claimed:
            try:
                out.append(
                    QueueMessage(
                        message_id=message_id, body=json.loads(fields["body"])
                    )
                )
            except json.JSONDecodeError:
                # Garbage payload — ack and drop so it doesn't loop forever.
                await self.ack(message_id)
        return out

    async def depth(self) -> int:
        return await self.redis.xlen(self.STREAM)
