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
                          "errorMessage", "canonicalSlug"
                   FROM "StudentExperience"
                   WHERE "studentId" = $1 AND "planItemId" = $2''',
                student_id, plan_item_id,
            )
            return self._record(row) if row else None
        finally:
            await conn.close()

    async def claim(self, student_id: str, plan_item_id: str, canonical_slug: str) -> GenerationClaim:
        """Atomically claim generation, or return the existing state.

        Failed rows are claimable again. Generating and ready rows cannot be
        claimed by a duplicate click or another application instance.
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
                     status = 'generating', "errorMessage" = NULL, "updatedAt" = NOW()
                   WHERE "StudentExperience".status = 'failed'
                      OR ("StudentExperience".status = 'generating'
                          AND "StudentExperience"."updatedAt" < NOW() - INTERVAL '2 minutes')
                   RETURNING id, status, title, track, "blocksJson", "metadataJson",
                             "errorMessage", "canonicalSlug"''',
                experience_id, student_id, plan_item_id, canonical_slug,
            )
            if row:
                record = self._record(row)
                return GenerationClaim("generating", True, record)
            existing_row = await conn.fetchrow(
                '''SELECT id, status, title, track, "blocksJson", "metadataJson",
                          "errorMessage", "canonicalSlug" FROM "StudentExperience"
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
            row = await conn.fetchrow(
                '''UPDATE "StudentExperience" SET status = 'ready', title = $3,
                     track = $4, "blocksJson" = $5::jsonb, "metadataJson" = $6::jsonb,
                     "errorMessage" = NULL, "updatedAt" = NOW()
                   WHERE "studentId" = $1 AND "planItemId" = $2
                   RETURNING id, status, title, track, "blocksJson", "metadataJson",
                             "errorMessage", "canonicalSlug"''',
                student_id, plan_item_id, title, track, json.dumps(blocks), json.dumps(metadata),
            )
            return self._record(row)
        finally:
            await conn.close()

    async def mark_failed(self, student_id: str, plan_item_id: str, message: str) -> None:
        conn = await get_db_conn()
        try:
            await conn.execute(
                '''UPDATE "StudentExperience" SET status = 'failed',
                     "errorMessage" = $3, "updatedAt" = NOW()
                   WHERE "studentId" = $1 AND "planItemId" = $2 AND status = 'generating' ''',
                student_id, plan_item_id, message[:500],
            )
        finally:
            await conn.close()

    @staticmethod
    def _record(row) -> dict:
        return {
            "id": str(row["id"]), "status": str(row["status"]),
            "title": row["title"], "track": row["track"],
            "blocks": row["blocksJson"] or [], "metadata": row["metadataJson"] or {},
            "error_message": row["errorMessage"], "canonical_slug": row["canonicalSlug"],
        }


student_experience_store = StudentExperienceStore()
