"""Purely observational log of concepts a Space conversation engaged with but
did not demonstrate to correctness.

This must never be read by any mastery/credit calculation — recording
"encountered" here is deliberately kept separate from StandardMastery so it
can never be mistaken for, or accidentally counted as, demonstrated mastery.
"""
from __future__ import annotations

from app.config import get_db_conn


class ConceptEncounterStore:
    async def record(self, student_id: str, concept_name: str, track: str, space_session_id: str) -> None:
        conn = await get_db_conn()
        try:
            await conn.execute(
                '''INSERT INTO "ConceptEncounter"
                     (id, "studentId", "conceptName", track, "spaceSessionId")
                   VALUES (gen_random_uuid()::text, $1, $2, $3, $4)''',
                student_id, concept_name, track, space_session_id,
            )
        finally:
            await conn.close()


concept_encounter_store = ConceptEncounterStore()
