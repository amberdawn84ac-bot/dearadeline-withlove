"""
CanonicalStore — permanent lesson storage for the curriculum corpus.

Two-layer storage:
  1. Redis (fast, in-memory) — checked first, written on DB miss
  2. PostgreSQL CanonicalLesson table — source of truth, survives Redis eviction

Lookup: Redis HIT → return. Redis MISS → DB lookup → populate Redis → return.
Write:  DB first → then Redis. Canonical lessons are never deleted.
"""
import hashlib
import json
import logging
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
                '"researcherActivated", "agentName" '
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
            }
        finally:
            await conn.close()

    async def _db_write(self, slug: str, record: dict) -> None:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            await conn.execute(
                """
                INSERT INTO "CanonicalLesson" (
                    id, "topicSlug", topic, track, title,
                    "blocksJson", "oasStandards", "researcherActivated", "agentName"
                ) VALUES ($1, $2, $3, $4::"Track", $5, $6::jsonb, $7::jsonb, $8, $9)
                ON CONFLICT ("topicSlug") DO UPDATE SET
                    title               = EXCLUDED.title,
                    "blocksJson"        = EXCLUDED."blocksJson",
                    "oasStandards"      = EXCLUDED."oasStandards",
                    "researcherActivated" = EXCLUDED."researcherActivated",
                    "agentName"         = EXCLUDED."agentName",
                    "updatedAt"         = NOW()
                """,
                record["id"], slug, record["topic"], record["track"], record["title"],
                json.dumps(record["blocks"]), json.dumps(record["oas_standards"]),
                record["researcher_activated"], record["agent_name"],
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

    async def save(self, slug: str, record: dict) -> None:
        """Write to DB first (durable), then Redis (fast)."""
        await self._db_write(slug, record)
        await self._redis_set(slug, json.dumps(record))
        logger.info(f"[CanonicalStore] Saved canonical lesson — {slug} ({record['topic']})")


canonical_store = CanonicalStore()
