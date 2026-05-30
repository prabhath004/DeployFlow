from redis.asyncio import ConnectionPool, Redis

from app.core.config import Settings

_pool: ConnectionPool | None = None
_client: Redis | None = None


def init_redis(settings: Settings) -> Redis:
    """Create the process-wide Redis client. Call once at startup."""
    global _pool, _client
    _pool = ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,  # str in, str out — saves us .decode() everywhere
        max_connections=20,
    )
    _client = Redis(connection_pool=_pool)
    return _client


async def dispose_redis() -> None:
    global _pool, _client
    if _client is not None:
        await _client.aclose()
    if _pool is not None:
        await _pool.disconnect()
    _client = None
    _pool = None


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError("Redis not initialized; call init_redis() first.")
    return _client
