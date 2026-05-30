from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.redis import get_redis

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

    # Phase 6 will replace the queue stub with a real check.

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
