"""Per-household, per-slot ordered queue for the shared family investigation.

Two named slots exist per household today: "science" and "history". The
current item in a slot is the lowest-position row with completedAt still
null — no calendar binding, no pointer column; advancing is just stamping
completedAt on the current row.

This store only knows about the queue itself. Deciding *when* a queue item
counts as finished (checking the Space tied to it) lives in learning_plan.py,
where the shared_investigation_id formula is already defined — keeps this
store from needing to know anything about Spaces or students.
"""
from __future__ import annotations

from app.config import get_db_conn


class FamilyInvestigationQueueStore:
    async def get_current(self, household_id: str, slot: str) -> dict | None:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT id::text, position, "canonicalTopic", track FROM "FamilyInvestigationQueue" '
                'WHERE "householdId"=$1 AND slot=$2 AND "completedAt" IS NULL '
                'ORDER BY position ASC LIMIT 1',
                household_id, slot,
            )
            if not row:
                return None
            return {"id": row["id"], "position": row["position"],
                    "canonical_topic": row["canonicalTopic"], "track": row["track"]}
        finally:
            await conn.close()

    async def mark_completed(self, queue_id: str) -> None:
        conn = await get_db_conn()
        try:
            await conn.execute(
                'UPDATE "FamilyInvestigationQueue" SET "completedAt"=NOW() '
                'WHERE id=$1 AND "completedAt" IS NULL',
                queue_id,
            )
        finally:
            await conn.close()

    async def enqueue(self, household_id: str, slot: str, canonical_topic: str, track: str) -> dict:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                '''INSERT INTO "FamilyInvestigationQueue"
                     (id, "householdId", slot, position, "canonicalTopic", track)
                   SELECT gen_random_uuid()::text, $1, $2,
                          COALESCE((SELECT MAX(position) + 1 FROM "FamilyInvestigationQueue"
                                    WHERE "householdId"=$1 AND slot=$2), 0),
                          $3, $4
                   RETURNING id::text, position, "canonicalTopic", track''',
                household_id, slot, canonical_topic, track,
            )
            return {"id": row["id"], "position": row["position"],
                    "canonical_topic": row["canonicalTopic"], "track": row["track"]}
        finally:
            await conn.close()


family_investigation_queue_store = FamilyInvestigationQueueStore()
