from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.redis import get_redis
from app.services.queue_service import RedisStreamQueue

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
        queue = RedisStreamQueue(redis)
        await queue.ensure_group()
        # XLEN is O(1); a successful call confirms the stream is reachable.
        await queue.depth()
    except Exception:
        checks["queue"] = "down"

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
