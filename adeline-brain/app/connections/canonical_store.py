"""
CanonicalStore — permanent lesson storage for the curriculum corpus.

Two-layer storage:
  1. Redis (fast, in-memory) — checked first, written on DB miss
  2. PostgreSQL CanonicalLesson table — source of truth, survives Redis eviction

Lookup: Redis HIT → return. Redis MISS → DB lookup → populate Redis → return.
Write:  DB first → then Redis. Pending canonicals skip Redis until approved.
"""
import asyncio
import hashlib
import json
import logging
import os
import uuid
from typing import Optional

from app.connections.redis_client import redis_client

logger = logging.getLogger(__name__)
REDIS_PREFIX = "canonical:"


def canonical_slug(topic: str, track: str) -> str:
    """Deterministic 32-char hex key for (topic, track). Case- and whitespace-insensitive."""
    raw = f"{topic.strip().lower()}:{track}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class CanonicalStore:
    async def _redis_get(self, slug: str) -> Optional[str]:
        try:
            return await redis_client.get(f"{REDIS_PREFIX}{slug}")
        except Exception as e:
            logger.warning(f"[CanonicalStore] Redis GET failed: {e}")
            return None

    async def _redis_set(self, slug: str, value: str) -> None:
        try:
            await redis_client.set(f"{REDIS_PREFIX}{slug}", value, ex=None)
        except Exception as e:
            logger.warning(f"[CanonicalStore] Redis SET failed: {e}")

    async def _db_get(self, slug: str) -> Optional[dict]:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT id, topic, track, title, "blocksJson", "oasStandards", '
                '"researcherActivated", "agentName", '
                'COALESCE("pendingApproval", FALSE) AS "pendingApproval", "needsReviewReason" '
                'FROM "CanonicalLesson" '
                'WHERE "topicSlug" = $1 '
                'AND ("pendingApproval" IS FALSE OR "pendingApproval" IS NULL)',
                slug,
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "topic_slug": slug,
                "topic": row["topic"],
                "track": row["track"],
                "title": row["title"],
                "blocks": row["blocksJson"],
                "oas_standards": row["oasStandards"],
                "researcher_activated": row["researcherActivated"],
                "agent_name": row["agentName"],
                "pending_approval": row["pendingApproval"],
                "needs_review_reason": row["needsReviewReason"],
            }
        finally:
            await conn.close()

    async def _db_write(self, slug: str, record: dict, pending: bool = False) -> None:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            await conn.execute(
                """
                INSERT INTO "CanonicalLesson" (
                    id, "topicSlug", topic, track, title,
                    "blocksJson", "oasStandards", "researcherActivated", "agentName",
                    "pendingApproval", "needsReviewReason"
                ) VALUES ($1, $2, $3, $4::"Track", $5, $6::jsonb, $7::jsonb, $8, $9, $10, $11)
                ON CONFLICT ("topicSlug") DO UPDATE SET
                    title               = EXCLUDED.title,
                    "blocksJson"        = EXCLUDED."blocksJson",
                    "oasStandards"      = EXCLUDED."oasStandards",
                    "researcherActivated" = EXCLUDED."researcherActivated",
                    "agentName"         = EXCLUDED."agentName",
                    "pendingApproval"   = EXCLUDED."pendingApproval",
                    "needsReviewReason" = EXCLUDED."needsReviewReason",
                    "updatedAt"         = NOW()
                """,
                record["id"], slug, record["topic"], record["track"], record["title"],
                json.dumps(record["blocks"]), json.dumps(record["oas_standards"]),
                record["researcher_activated"], record["agent_name"],
                pending, record.get("needs_review_reason"),
            )
        finally:
            await conn.close()

    async def get(self, slug: str) -> Optional[dict]:
        """Redis-first lookup. Returns dict or None."""
        raw = await self._redis_get(slug)
        if raw:
            logger.info(f"[CanonicalStore] Redis HIT — {slug}")
            return json.loads(raw)

        record = await self._db_get(slug)
        if record:
            logger.info(f"[CanonicalStore] DB HIT — {slug}, populating Redis")
            await self._redis_set(slug, json.dumps(record))
        return record

    async def _redis_delete(self, slug: str) -> None:
        try:
            await redis_client.delete(f"{REDIS_PREFIX}{slug}")
        except Exception as e:
            logger.warning(f"[CanonicalStore] Redis DELETE failed (non-fatal): {e}")

    async def save(self, slug: str, record: dict, pending: bool = False) -> None:
        """Write to DB first (durable), then Redis only if not pending."""
        await self._db_write(slug, record, pending=pending)
        if not pending:
            await self._redis_set(slug, json.dumps(record))
        logger.info(
            f"[CanonicalStore] Saved canonical — {slug} ({record['topic']}) pending={pending}"
        )
        if pending:
            asyncio.create_task(_notify_review_needed(record))

    async def invalidate(self, slug: str) -> None:
        """Evict canonical from Redis cache (non-fatal). Next request re-fetches from DB."""
        await self._redis_delete(slug)
        logger.info(f"[CanonicalStore] Cache invalidated — {slug}")

    async def approve(self, slug: str) -> bool:
        """Mark a pending canonical as approved: clear flag in DB, then publish to Redis."""
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            result = await conn.execute(
                'UPDATE "CanonicalLesson" '
                'SET "pendingApproval" = FALSE, "needsReviewReason" = NULL, "updatedAt" = NOW() '
                'WHERE "topicSlug" = $1 AND "pendingApproval" = TRUE',
                slug,
            )
            if result == "UPDATE 0":
                return False
            record = await self._db_get_any(slug)
            if record:
                await self._redis_set(slug, json.dumps(record))
            logger.info(f"[CanonicalStore] Approved canonical — {slug}")
            return True
        finally:
            await conn.close()

    async def _db_get_any(self, slug: str) -> Optional[dict]:
        """Fetch canonical regardless of pendingApproval status (for internal use)."""
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT id, topic, track, title, "blocksJson", "oasStandards", '
                '"researcherActivated", "agentName", '
                'COALESCE("pendingApproval", FALSE) AS "pendingApproval", "needsReviewReason" '
                'FROM "CanonicalLesson" WHERE "topicSlug" = $1',
                slug,
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "topic_slug": slug,
                "topic": row["topic"],
                "track": row["track"],
                "title": row["title"],
                "blocks": row["blocksJson"],
                "oas_standards": row["oasStandards"],
                "researcher_activated": row["researcherActivated"],
                "agent_name": row["agentName"],
                "pending_approval": row["pendingApproval"],
                "needs_review_reason": row["needsReviewReason"],
            }
        finally:
            await conn.close()

    async def list_pending(self) -> list[dict]:
        """Return all canonicals awaiting admin review."""
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            rows = await conn.fetch(
                'SELECT "topicSlug", topic, track, title, "needsReviewReason", "updatedAt" '
                'FROM "CanonicalLesson" WHERE "pendingApproval" = TRUE '
                'ORDER BY "updatedAt" DESC',
            )
            return [
                {
                    "slug": r["topicSlug"],
                    "topic": r["topic"],
                    "track": r["track"],
                    "title": r["title"],
                    "needs_review_reason": r["needsReviewReason"],
                    "updated_at": r["updatedAt"].isoformat() if r["updatedAt"] else None,
                }
                for r in rows
            ]
        finally:
            await conn.close()


async def _notify_review_needed(record: dict) -> None:
    """Fire-and-forget HITL notification when a canonical needs admin review."""
    topic = record.get("topic", "unknown")
    track = record.get("track", "unknown")
    slug = record.get("topic_slug", "")
    reason = record.get("needs_review_reason", "unknown")
    msg = (
        f"[Adeline] New canonical needs review: '{topic}' ({track}) — "
        f"reason: {reason}. "
        f"Approve at POST /brain/api/admin/tasks/canonicals/{slug}/approve"
    )
    webhook_url = os.getenv("ADMIN_REVIEW_WEBHOOK_URL", "")
    if webhook_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook_url, json={"text": msg})
            logger.info(f"[CanonicalReview] Webhook notified for slug={slug}")
        except Exception as e:
            logger.warning(f"[CanonicalReview] Webhook failed (non-fatal): {e} — {msg}")
    else:
        logger.warning(f"[CanonicalReview] {msg}")


canonical_store = CanonicalStore()
