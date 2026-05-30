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


class SqsQueue(QueueService):
    """AWS SQS implementation.

    Mapping to the QueueService contract:
      publish()         → SendMessage
      consume()         → ReceiveMessage with WaitTimeSeconds (long poll)
      ack()             → DeleteMessage (using the ReceiptHandle)
      reclaim_orphans() → no-op; SQS auto-redelivers when VisibilityTimeout
                          expires without DeleteMessage.

    `message_id` here is actually the SQS ReceiptHandle, since that's what
    DeleteMessage needs. Callers shouldn't introspect it.
    """

    def __init__(
        self,
        *,
        queue_url: str,
        region: str,
        endpoint_url: str | None,
    ) -> None:
        import aioboto3  # local import keeps boto3 off the import path when not used
        self._session = aioboto3.Session()
        self._queue_url = queue_url
        self._region = region
        self._endpoint_url = endpoint_url

    def _client(self):
        return self._session.client(
            "sqs",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
        )

    async def publish(self, body: dict[str, Any]) -> str:
        async with self._client() as sqs:
            resp = await sqs.send_message(
                QueueUrl=self._queue_url,
                MessageBody=json.dumps(body),
            )
        return resp["MessageId"]

    async def consume(self, *, consumer: str, block_ms: int) -> QueueMessage | None:
        wait_seconds = min(20, max(0, block_ms // 1000))  # SQS max long-poll is 20s
        async with self._client() as sqs:
            resp = await sqs.receive_message(
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_seconds,
            )
        messages = resp.get("Messages") or []
        if not messages:
            return None
        m = messages[0]
        try:
            body = json.loads(m["Body"])
        except json.JSONDecodeError:
            # Bad payload — delete so it doesn't loop forever via the DLQ.
            await self.ack(m["ReceiptHandle"])
            return None
        return QueueMessage(message_id=m["ReceiptHandle"], body=body)

    async def ack(self, message_id: str) -> None:
        async with self._client() as sqs:
            await sqs.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=message_id,
            )

    async def reclaim_orphans(
        self, *, consumer: str, idle_ms: int
    ) -> list[QueueMessage]:
        # SQS does this for you: unacked messages reappear after VisibilityTimeout.
        return []


def make_queue(settings, redis) -> QueueService:
    """Factory: read settings.queue_backend and return the right implementation.

    Used by both the API (via routes/deps) and the worker (in its main()).
    """
    if settings.queue_backend == "sqs":
        if not settings.sqs_queue_url:
            raise RuntimeError("QUEUE_BACKEND=sqs but SQS_QUEUE_URL is not set")
        return SqsQueue(
            queue_url=settings.sqs_queue_url,
            region=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
        )
    return RedisStreamQueue(redis)
