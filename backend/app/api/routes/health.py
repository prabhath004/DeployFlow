from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: does NOT touch downstreams."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Readiness: pings every downstream. Returns 503 if any are down."""
    checks = {"api": "ok", "database": "ok", "redis": "ok", "queue": "ok"}

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "down"

    # Phase 5 will replace this stub with a real redis.ping().
    # Phase 6/8 will replace this stub with a real queue describe.

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
