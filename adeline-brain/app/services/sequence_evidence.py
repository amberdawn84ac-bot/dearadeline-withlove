"""Bring this learner's saved evidence forward within the same family unit."""
import json
import re
import logging
from app.config import get_db_conn

logger = logging.getLogger(__name__)
_UNIT_ITEM = re.compile(r"^family-unit-([0-9a-f-]{36})-([0-9a-f-]{36})$")


def evidence_from_prior_sessions(rows: list) -> list[dict]:
    result = []
    for row in rows:
        messages = row["messagesJson"]
        if isinstance(messages, str):
            messages = json.loads(messages)
        notebooks = []
        for message in messages or []:
            metadata = ((message.get("resource_block") or {}).get("metadata") or {})
            if metadata.get("notebook"):
                notebooks.append({"question": (metadata.get("lab") or {}).get("question"), "notebook": metadata["notebook"]})
        result.append({
            "title": row["title"], "status": row["status"], "lab_notebooks": notebooks[-2:],
            "learner_evidence": [m["content"][:600] for m in messages or [] if m.get("role") == "user" and not m.get("lab_notebook")][-2:],
        })
    return result


async def attach_sequence_evidence(state: dict) -> dict:
    match = _UNIT_ITEM.fullmatch(str(state.get("plan_item_id") or ""))
    if not match:
        return state
    try:
        conn = await get_db_conn()
        try:
            rows = await conn.fetch('''SELECT e.title,s.status,s."messagesJson"
                FROM "FamilyUnitQueue" q
                JOIN "FamilyUnitExperience" present ON present.id=$2::text AND present."unitId"=q."unitId"
                JOIN "FamilyUnitExperience" prior ON prior."unitId"=q."unitId" AND prior.position<present.position
                JOIN "SpaceSession" s ON s."planItemId"='family-unit-'||q.id::text||'-'||prior.id::text AND s."studentId"=$3
                JOIN "StudentExperience" e ON e.id=s."experienceId"
                WHERE q.id=$1::text ORDER BY prior.position DESC LIMIT 3''', match.group(1), match.group(2), state["student_id"])
        finally:
            await conn.close()
        return {**state, "previous_session_evidence": evidence_from_prior_sessions(list(reversed(rows)))}
    except Exception:
        logger.warning("Prior session evidence unavailable; never invent earlier results", exc_info=True)
        return state
