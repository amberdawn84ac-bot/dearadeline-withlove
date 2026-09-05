"""Parent-pinned overrides for a household's weekly family investigation.

Sits in front of PersonalizedCurriculumPlannerAgent.family_investigation_cycle():
absent, that hash-and-calendar-week rotation is completely unchanged; present,
the pinned (household, iso_year, iso_week) -> topic/track wins.
"""
from __future__ import annotations

from app.config import get_db_conn


class FamilyInvestigationOverrideStore:
    async def get(self, household_id: str, iso_year: int, iso_week: int) -> dict | None:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT "canonicalTopic", track FROM "FamilyInvestigationOverride" '
                'WHERE "householdId"=$1 AND "isoYear"=$2 AND "isoWeek"=$3',
                household_id, iso_year, iso_week,
            )
            if not row:
                return None
            return {"canonical_topic": row["canonicalTopic"], "track": row["track"]}
        finally:
            await conn.close()

    async def set(self, household_id: str, iso_year: int, iso_week: int, canonical_topic: str, track: str) -> None:
        conn = await get_db_conn()
        try:
            await conn.execute(
                '''INSERT INTO "FamilyInvestigationOverride"
                     (id, "householdId", "isoYear", "isoWeek", "canonicalTopic", track, "updatedAt")
                   VALUES (gen_random_uuid()::text, $1, $2, $3, $4, $5, NOW())
                   ON CONFLICT ("householdId", "isoYear", "isoWeek") DO UPDATE SET
                     "canonicalTopic" = EXCLUDED."canonicalTopic",
                     track = EXCLUDED.track,
                     "updatedAt" = NOW()''',
                household_id, iso_year, iso_week, canonical_topic, track,
            )
        finally:
            await conn.close()


family_investigation_override_store = FamilyInvestigationOverrideStore()
