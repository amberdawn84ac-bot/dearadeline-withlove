"""Durable, idempotent learner experience storage.

CanonicalLesson stores the shared authored investigation. StudentExperience
stores the exact adapted/rendered record a learner opened from a stable plan
item. A unique (student, plan item) key makes retries and double-clicks converge
on one record across processes and reconnects.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Literal

from app.config import get_db_conn

GenerationState = Literal["not_started", "generating", "ready", "failed"]


@dataclass(frozen=True)
class GenerationClaim:
    state: GenerationState
    claimed: bool = False
    record: dict | None = None


class StudentExperienceStore:
    async def get(self, student_id: str, plan_item_id: str) -> dict | None:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                '''SELECT id, status, title, track, "blocksJson", "metadataJson",
                          "errorMessage", "canonicalSlug", "failureCount"
                   FROM "StudentExperience"
                   WHERE "studentId" = $1 AND "planItemId" = $2''',
                student_id, plan_item_id,
            )
            return self._record(row) if row else None
        finally:
            await conn.close()

    async def claim(
        self, student_id: str, plan_item_id: str, canonical_slug: str, *, max_failures: int = 3,
    ) -> GenerationClaim:
        """Atomically claim generation, or return the existing state.

        Failed rows are claimable again UNTIL failureCount reaches max_failures —
        past that the row is left terminal so the caller can escalate instead of
        spending another LLM call proving what prior attempts already showed. A
        generating row is only reclaimable after a short stale window — most real
        authoring finishes in well under a minute; 3 minutes is generous headroom
        for a slow LLM call without leaving a family staring at a dead request for
        15 minutes after a deploy or dropped connection killed it mid-stream.

        The prior errorMessage is preserved on reclaim so a repeated failure's
        original cause is still visible for diagnosis; save_ready clears it on
        success and mark_failed overwrites it on the next failure.
        """
        conn = await get_db_conn()
        try:
            experience_id = str(uuid.uuid4())
            row = await conn.fetchrow(
                '''INSERT INTO "StudentExperience"
                     (id, "studentId", "planItemId", "canonicalSlug", status,
                      "blocksJson", "metadataJson", "createdAt", "updatedAt")
                   VALUES ($1, $2, $3, $4, 'generating', '[]'::jsonb, '{}'::jsonb, NOW(), NOW())
                   ON CONFLICT ("studentId", "planItemId") DO UPDATE SET
                     status = 'generating', "updatedAt" = NOW(),
                     "canonicalSlug" = EXCLUDED."canonicalSlug"
                   WHERE COALESCE("StudentExperience"."failureCount", 0) < $5
                     AND ("StudentExperience".status = 'failed'
                          OR ("StudentExperience".status = 'generating'
                              AND "StudentExperience"."updatedAt" < NOW() - INTERVAL '3 minutes'))
                   RETURNING id, status, title, track, "blocksJson", "metadataJson",
                             "errorMessage", "canonicalSlug", "failureCount"''',
                experience_id, student_id, plan_item_id, canonical_slug, max_failures,
            )
            if row:
                record = self._record(row)
                return GenerationClaim("generating", True, record)
            existing_row = await conn.fetchrow(
                '''SELECT id, status, title, track, "blocksJson", "metadataJson",
                          "errorMessage", "canonicalSlug", "failureCount" FROM "StudentExperience"
                   WHERE "studentId" = $1 AND "planItemId" = $2''',
                student_id, plan_item_id,
            )
            existing = self._record(existing_row)
            return GenerationClaim(existing["status"], False, existing)
        finally:
            await conn.close()

    async def save_ready(self, student_id: str, plan_item_id: str, *, title: str,
                         track: str, blocks: list[dict], metadata: dict) -> dict:
        conn = await get_db_conn()
        try:
            slug = str((metadata or {}).get("canonical_slug") or "")
            row = await conn.fetchrow(
                '''UPDATE "StudentExperience" SET status = 'ready', title = $3,
                     track = $4, "blocksJson" = $5::jsonb, "metadataJson" = $6::jsonb,
                     "canonicalSlug" = COALESCE(NULLIF($7, ''), "canonicalSlug"),
                     "errorMessage" = NULL, "failureCount" = 0, "updatedAt" = NOW()
                   WHERE "studentId" = $1 AND "planItemId" = $2
                   RETURNING id, status, title, track, "blocksJson", "metadataJson",
                             "errorMessage", "canonicalSlug", "failureCount"''',
                student_id, plan_item_id, title, track, json.dumps(blocks), json.dumps(metadata), slug,
            )
            return self._record(row)
        finally:
            await conn.close()

    async def invalidate_ready(self, student_id: str, plan_item_id: str, reason: str) -> bool:
        """Mark a ready experience failed so claim() can rebuild it from a better canonical."""
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                '''UPDATE "StudentExperience" SET status = 'failed',
                     "errorMessage" = $3, "updatedAt" = NOW()
                   WHERE "studentId" = $1 AND "planItemId" = $2 AND status = 'ready'
                   RETURNING id''',
                student_id, plan_item_id, reason[:500],
            )
            return bool(row)
        finally:
            await conn.close()

    async def mark_failed(self, student_id: str, plan_item_id: str, message: str) -> int:
        """Returns the new consecutive-failure count so callers can decide
        whether to escalate instead of silently offering another retry."""
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                '''UPDATE "StudentExperience" SET status = 'failed',
                     "errorMessage" = $3, "failureCount" = "failureCount" + 1, "updatedAt" = NOW()
                   WHERE "studentId" = $1 AND "planItemId" = $2 AND status = 'generating'
                   RETURNING "failureCount"''',
                student_id, plan_item_id, message[:500],
            )
            return row["failureCount"] if row else 0
        finally:
            await conn.close()

    async def mark_escalated(self, student_id: str, plan_item_id: str, reason: str) -> bool:
        """Force a repeatedly-failing row terminal, whatever its current status.

        The escalation short-circuit in the author stream used to `return`
        without touching the row, so a row that claim() had just flipped
        failed->generating stayed 'generating' forever and the UI polled it as
        if authoring were still in progress. This makes the row 'failed' so the
        client shows a real error and stops polling. failureCount is left as-is
        (already at the escalation threshold)."""
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                '''UPDATE "StudentExperience"
                   SET status = 'failed', "errorMessage" = $3, "updatedAt" = NOW()
                   WHERE "studentId" = $1 AND "planItemId" = $2 AND status <> 'ready'
                   RETURNING id''',
                student_id, plan_item_id, reason[:500],
            )
            return bool(row)
        finally:
            await conn.close()

    @staticmethod
    def _record(row) -> dict:
        def decoded(value, fallback):
            if value is None:
                return fallback
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (TypeError, ValueError):
                    return fallback
            return value

        return {
            "id": str(row["id"]), "status": str(row["status"]),
            "title": row["title"], "track": row["track"],
            "blocks": decoded(row["blocksJson"], []),
            "metadata": decoded(row["metadataJson"], {}),
            "error_message": row["errorMessage"], "canonical_slug": row["canonicalSlug"],
            "failure_count": row["failureCount"],
        }


student_experience_store = StudentExperienceStore()
