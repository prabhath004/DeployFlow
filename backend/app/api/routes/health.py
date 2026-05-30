from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.database import get_session
from app.db.redis import get_redis
from app.services.queue_service import RedisStreamQueue, make_queue

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: does NOT touch downstreams."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Readiness: pings every downstream. Returns 503 if any are down."""
    checks = {"api": "ok", "database": "ok", "redis": "ok", "queue": "ok"}

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "down"

    try:
        pong = await redis.ping()
        if not pong:
            checks["redis"] = "down"
    except Exception:
        checks["redis"] = "down"

    try:
        queue = make_queue(settings, redis)
        if isinstance(queue, RedisStreamQueue):
            await queue.ensure_group()
            await queue.depth()       # O(1) reachability check
        # For SQS we don't ping on every /ready to avoid burning AWS request quota.
        # The boto3 client validates URL at first publish/receive.
    except Exception:
        checks["queue"] = "down"

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
