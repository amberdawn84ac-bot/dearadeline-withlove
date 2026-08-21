"""Shared Redis-backed limits for expensive or abuse-sensitive operations."""
from __future__ import annotations

import logging
import time

from fastapi import HTTPException

from app.connections.redis_client import redis_client

logger = logging.getLogger(__name__)


async def enforce_rate_limit(
    bucket: str,
    identifier: str,
    *,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """Fixed-window limit shared by every Railway replica; fail open if Redis is down."""
    window = int(time.time()) // window_seconds
    key = f"rate:{bucket}:{identifier}:{window}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds + 5)
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(window_seconds)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Shared rate limiter unavailable for %s: %s", bucket, exc)
