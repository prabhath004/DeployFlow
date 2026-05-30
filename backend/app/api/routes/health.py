from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    # Phase 1: no downstreams yet. Later phases will replace these stubs
    # with real ping checks (DB SELECT 1, Redis PING, queue describe).
    return {
        "api": "ok",
        "database": "ok",
        "redis": "ok",
        "queue": "ok",
    }
