"""Shared durable progress inputs; AI prose never invents curriculum identities."""

import json
import logging

logger = logging.getLogger(__name__)


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


async def known_skills(conn, identities: list[str]) -> list[dict]:
    if not identities:
        return []
    rows = await conn.fetch(
        """SELECT code AS id,description AS title,track FROM "OASStandard" WHERE code=ANY($1::text[])
        UNION ALL SELECT id,title,track::text FROM "CurriculumConcept" WHERE id=ANY($1::text[])""",
        identities,
    )
    return list({r["id"]: dict(r) for r in rows}.values())


async def refresh_learning_projection(student_id: str) -> None:
    """Keep the shared dated investigation; recompute individual targets on next read."""
    from app.api.learning_plan import _plan_cache_key
    from app.connections.redis_client import redis_client
    from app.models.student import invalidate_student_state_cache

    try:
        await redis_client.delete(_plan_cache_key(student_id))
        await invalidate_student_state_cache(student_id)
    except Exception:
        logger.warning(
            "Progress is durable; cache refresh will retry on the next read",
            exc_info=True,
        )


async def course_progress(conn, scope) -> dict:
    scope = dict(scope)
    skills = scope["skillIds"]
    states = await conn.fetch(
        """SELECT "skillId",status FROM "StudentSkillState"
        WHERE "studentId"=$1 AND "skillId"=ANY($2::text[])""",
        scope["studentId"],
        skills,
    )
    status = {r["skillId"]: r["status"] for r in states}
    # Use actual preserved evaluations. Multiple guesses in one scene aren't independent work.
    evidence = await conn.fetch(
        '''SELECT e.id,e."attemptId",e."skillId",e.result,e.reasoning,e."evaluatorId",
            a."lessonId",a."createdAt",a.content
        FROM "EvidenceEvaluation" e JOIN "EvidenceAttempt" a ON a.id=e."attemptId"
        WHERE a."studentId"=$1 AND e."skillId"=ANY($2::text[])
        ORDER BY a."createdAt",e."createdAt"''',
        scope["studentId"],
        skills,
    )
    independent = [
        dict(r)
        for r in evidence
        if r["result"] in ("demonstrated", "secure")
        and not decoded(r["content"]).get("support")
        and not decoded(r["content"]).get("previous_feedback_available")
    ]
    demonstrated = [
        s
        for s in skills
        if status.get(s) in ("demonstrated", "secure")
        and any(e["skillId"] == s for e in independent)
    ]
    allocated = await conn.fetch(
        """SELECT "skillId","scopeId" FROM "CourseSkillAllocation"
        WHERE "studentId"=$1 AND "skillId"=ANY($2::text[])""",
        scope["studentId"],
        skills,
    )
    conflicts = [r["skillId"] for r in allocated if r["scopeId"] != scope["id"]]
    lessons = {e["lessonId"] for e in independent}
    return {
        "demonstrated": demonstrated,
        "missing": [s for s in skills if s not in demonstrated],
        "conflicts": conflicts,
        "evidence": independent,
        "ready": len(demonstrated) == len(skills)
        and len(lessons) >= 2
        and not conflicts,
        "lesson_count": len(lessons),
        "coverage": round(100 * len(demonstrated) / len(skills), 1),
    }
