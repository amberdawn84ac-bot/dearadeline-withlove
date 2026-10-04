"""One active household unit; advancing is an explicit, locked transaction."""
from app.config import get_db_conn


class FamilyUnitStore:
    async def enqueue(self, household_id: str, title: str, experiences: list[dict]) -> dict:
        if not title.strip() or not experiences:
            raise ValueError('A unit needs a title and at least one experience')
        conn = await get_db_conn()
        try:
            async with conn.transaction():
                await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', household_id)
                unit_id = await conn.fetchval('INSERT INTO "FamilyUnit"(title) VALUES ($1) RETURNING id', title.strip())
                for position, experience in enumerate(experiences):
                    await conn.execute('INSERT INTO "FamilyUnitExperience"("unitId",position,"canonicalTopic",track) VALUES ($1,$2,$3,$4)', unit_id, position, experience['canonical_topic'], experience['track'])
                row = await conn.fetchrow('''INSERT INTO "FamilyUnitQueue"("householdId","unitId",position,status,"startedAt")
                    SELECT $1,$2,COALESCE(MAX(position)+1,0),
                      CASE WHEN COUNT(*) FILTER (WHERE status='active')=0 THEN 'active' ELSE 'queued' END,
                      CASE WHEN COUNT(*) FILTER (WHERE status='active')=0 THEN NOW() END
                    FROM "FamilyUnitQueue" WHERE "householdId"=$1 RETURNING id,position,status''', household_id, unit_id)
                return dict(row)
        finally:
            await conn.close()

    async def current(self, household_id: str) -> dict | None:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow('''SELECT q.id,q.position,q."unitId",u.title,
                e.id AS "experienceId",e."canonicalTopic",e.track,e.position AS "experiencePosition",
                legacy.slot AS "legacySlot",legacy.position AS "legacyPosition"
                FROM "FamilyUnitQueue" q JOIN "FamilyUnit" u ON u.id=q."unitId"
                LEFT JOIN "FamilyInvestigationQueue" legacy ON legacy.id=q."legacyQueueId"
                LEFT JOIN LATERAL (
                  SELECT x.* FROM "FamilyUnitExperience" x WHERE x."unitId"=q."unitId"
                  AND NOT EXISTS (SELECT 1 FROM "FamilyUnitExperienceProgress" p WHERE p."queueId"=q.id AND p."experienceId"=x.id)
                  ORDER BY x.position LIMIT 1
                ) e ON TRUE WHERE q."householdId"=$1 AND q.status='active' ''', household_id)
            return dict(row) if row else None
        finally:
            await conn.close()

    async def upcoming(self, household_id: str) -> list[dict]:
        conn = await get_db_conn()
        try:
            rows = await conn.fetch('''SELECT q.id,q.position,u.title,e."canonicalTopic",e.track
              FROM "FamilyUnitQueue" q JOIN "FamilyUnit" u ON u.id=q."unitId"
              JOIN "FamilyUnitExperience" e ON e."unitId"=u.id AND e.position=0
              WHERE q."householdId"=$1 AND q.status='queued' ORDER BY q.position''', household_id)
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async def complete_experience(self, household_id: str, queue_id: str, experience_id: str) -> None:
        conn = await get_db_conn()
        try:
            async with conn.transaction():
                await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', household_id)
                valid = await conn.fetchval('''SELECT 1 FROM "FamilyUnitQueue" q JOIN "FamilyUnitExperience" e ON e."unitId"=q."unitId"
                  WHERE q.id=$1 AND q."householdId"=$2 AND q.status='active' AND e.id=$3
                  AND NOT EXISTS (SELECT 1 FROM "FamilyUnitExperience" earlier WHERE earlier."unitId"=q."unitId" AND earlier.position<e.position
                    AND NOT EXISTS (SELECT 1 FROM "FamilyUnitExperienceProgress" p WHERE p."queueId"=q.id AND p."experienceId"=earlier.id))''', queue_id, household_id, experience_id)
                if not valid:
                    raise ValueError('Only the current experience in the active household unit can complete')
                await conn.execute('INSERT INTO "FamilyUnitExperienceProgress"("queueId","experienceId") VALUES ($1,$2) ON CONFLICT DO NOTHING', queue_id, experience_id)
        finally:
            await conn.close()

    async def advance(self, household_id: str, queue_id: str) -> None:
        conn = await get_db_conn()
        try:
            async with conn.transaction():
                await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', household_id)
                row = await conn.fetchrow('SELECT * FROM "FamilyUnitQueue" WHERE id=$1 AND "householdId"=$2 FOR UPDATE', queue_id, household_id)
                if not row:
                    raise ValueError('Unit does not belong to this household')
                if row['status'] == 'completed':
                    return  # retry must not complete the next unit
                if row['status'] != 'active':
                    raise ValueError('Only the active unit can advance')
                remaining = await conn.fetchval('''SELECT COUNT(*) FROM "FamilyUnitExperience" e WHERE e."unitId"=$1
                  AND NOT EXISTS (SELECT 1 FROM "FamilyUnitExperienceProgress" p WHERE p."queueId"=$2 AND p."experienceId"=e.id)''', row['unitId'], queue_id)
                if remaining:
                    raise ValueError('Finish every experience before advancing the unit')
                await conn.execute('UPDATE "FamilyUnitQueue" SET status=\'completed\',"completedAt"=NOW() WHERE id=$1', queue_id)
                await conn.execute('''UPDATE "FamilyUnitQueue" SET status='active',"startedAt"=NOW() WHERE id=(
                    SELECT id FROM "FamilyUnitQueue" WHERE "householdId"=$1 AND status='queued' ORDER BY position LIMIT 1)''', household_id)
        finally:
            await conn.close()


family_unit_store = FamilyUnitStore()
