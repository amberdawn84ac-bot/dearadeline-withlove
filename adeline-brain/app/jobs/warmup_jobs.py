"""
Nightly canonical cache warmup job.

Queries all approved CanonicalLesson rows from Postgres and writes each to Redis.
Runs at 02:00 UTC via ARQ cron. Ensures Redis is never cold after restart.

This is the difference between a student's first lesson of the day taking
500ms (Redis hit) vs 3000ms (DB query + serialize).
"""
import json
import logging

from app.connections.canonical_store import REDIS_PREFIX
from app.connections.redis_client import redis_client

logger = logging.getLogger(__name__)


async def warmup_canonical_cache(ctx: dict) -> dict:
    """
    Load all approved canonical lessons from Postgres into Redis.
    Returns a summary dict for logging.
    """
    from app.config import get_db_conn

    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            'SELECT "topicSlug", topic, track, title, "blocksJson", "oasStandards", '
            '"researcherActivated", "agentName" '
            'FROM "CanonicalLesson" '
            'WHERE ("pendingApproval" IS FALSE OR "pendingApproval" IS NULL) '
            'ORDER BY "updatedAt" DESC',
        )
    finally:
        await conn.close()

    loaded = 0
    failed = 0

    for row in rows:
        slug = row["topicSlug"]
        record = {
            "id": None,
            "topic_slug": slug,
            "topic": row["topic"],
            "track": row["track"],
            "title": row["title"],
            "blocks": row["blocksJson"],
            "oas_standards": row["oasStandards"],
            "researcher_activated": row["researcherActivated"],
            "agent_name": row["agentName"],
            "pending_approval": False,
            "needs_review_reason": None,
        }
        try:
            await redis_client.set(
                f"{REDIS_PREFIX}{slug}",
                json.dumps(record),
                ex=None,  # no TTL — nightly job refreshes
            )
            loaded += 1
        except Exception as e:
            logger.warning(f"[Warmup] Failed to cache slug={slug}: {e}")
            failed += 1

    logger.info(f"[Warmup] Canonical cache warmed: {loaded} loaded, {failed} failed")
    return {"loaded": loaded, "failed": failed, "total": len(rows)}
