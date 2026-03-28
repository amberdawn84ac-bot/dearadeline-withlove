"""
Redis async client for adeline-brain.
Used for: daily-bread caching, rate-limiting, auth sessions.
"""
import logging
import os

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Module-level singleton — connected lazily on first use
redis_client: aioredis.Redis = aioredis.from_url(
    _REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def ping() -> bool:
    """Returns True if Redis is reachable."""
    try:
        return await redis_client.ping()
    except Exception as e:
        logger.warning(f"[Redis] Ping failed: {e}")
        return False
