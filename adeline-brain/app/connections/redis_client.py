"""
Redis async client for adeline-brain.
Used for: daily-bread caching, rate-limiting, auth sessions.

Supports two backends:
  - Upstash Redis REST (cloud): set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN
  - Standard Redis (local/Docker): set REDIS_URL=redis://localhost:6379

Upstash takes precedence when UPSTASH_REDIS_REST_URL is present.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_UPSTASH_URL   = os.getenv("UPSTASH_REDIS_REST_URL")
_UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
_REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/0")


# ── Upstash REST adapter ──────────────────────────────────────────────────────

class _UpstashRedis:
    """
    Minimal async Redis-compatible client backed by the Upstash REST API.
    Implements only the operations used by adeline-brain: get, set, ping.
    """

    def __init__(self, url: str, token: str) -> None:
        self._url   = url.rstrip("/")
        self._token = token

    async def _call(self, *args: str) -> object:
        import httpx
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self._url, json=list(args), headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result")

    async def get(self, key: str) -> Optional[str]:
        result = await self._call("GET", key)
        return str(result) if result is not None else None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        if ex is not None:
            await self._call("SET", key, value, "EX", str(ex))
        else:
            await self._call("SET", key, value)

    async def delete(self, key: str) -> None:
        await self._call("DEL", key)

    async def ping(self) -> bool:
        result = await self._call("PING")
        return str(result).upper() == "PONG"


# ── Standard redis.asyncio adapter ───────────────────────────────────────────

def _make_aioredis():
    import redis.asyncio as aioredis  # type: ignore
    return aioredis.from_url(_REDIS_URL, encoding="utf-8", decode_responses=True)


# ── Public singleton ──────────────────────────────────────────────────────────

if _UPSTASH_URL:
    logger.info("[Redis] Using Upstash REST backend")
    redis_client = _UpstashRedis(_UPSTASH_URL, _UPSTASH_TOKEN)
else:
    logger.info(f"[Redis] Using standard Redis at {_REDIS_URL}")
    redis_client = _make_aioredis()


async def ping() -> bool:
    """Returns True if the configured Redis backend is reachable."""
    try:
        return await redis_client.ping()
    except Exception as e:
        logger.warning(f"[Redis] Ping failed: {e}")
        return False
