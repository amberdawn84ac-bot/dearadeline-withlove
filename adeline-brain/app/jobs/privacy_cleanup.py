"""Small, idempotent privacy-retention jobs.

Every web worker may start this loop.  The UPDATE is intentionally safe to run
more than once and keeps expired parental-consent secrets out of the database.
"""
import asyncio
import logging

from app.config import get_db_conn

logger = logging.getLogger(__name__)
_cleanup_task: asyncio.Task | None = None


async def purge_expired_consent_tokens() -> int:
    conn = await get_db_conn()
    owns_lock = False
    try:
        owns_lock = await conn.fetchval(
            "SELECT pg_try_advisory_lock(hashtext('dear-adeline:privacy-retention'))"
        )
        if not owns_lock:
            return 0
        result = await conn.execute(
            '''UPDATE "User"
               SET "coppaPendingToken" = NULL,
                   "coppaTokenExpiresAt" = NULL,
                   "updatedAt" = NOW()
               WHERE "coppaTokenExpiresAt" < NOW()
                 AND "coppaPendingToken" IS NOT NULL'''
        )
        return int(result.rsplit(" ", 1)[-1])
    finally:
        if owns_lock:
            try:
                await conn.execute(
                    "SELECT pg_advisory_unlock(hashtext('dear-adeline:privacy-retention'))"
                )
            except Exception:
                pass
        await conn.close()


async def _cleanup_loop() -> None:
    while True:
        try:
            removed = await purge_expired_consent_tokens()
            if removed:
                logger.info("[Privacy] Purged %s expired consent token(s)", removed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[Privacy] Expired consent-token cleanup failed")
        await asyncio.sleep(6 * 60 * 60)


async def start_privacy_cleanup() -> None:
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop(), name="privacy-retention-cleanup")


async def stop_privacy_cleanup() -> None:
    global _cleanup_task
    if _cleanup_task is not None:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        _cleanup_task = None
