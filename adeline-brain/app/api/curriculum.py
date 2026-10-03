"""Curriculum records: explicit progression, append-only evidence and character."""

import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from app.api.middleware import verify_household_access, verify_student_access
from app.config import get_db_conn
from app.connections.family_unit_store import family_unit_store
from app.schemas.api_models import Track

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


def _record(row) -> dict:
    result = dict(row)
    for key in (
        "content",
        "rolePreferences",
        "persistentTraits",
        "visualData",
        "sources",
        "perspectives",
        "omittedPerspectives",
        "conflictingEvidence",
    ):
        if isinstance(result.get(key), str):
            result[key] = json.loads(result[key])
    return result


class UnitExperience(BaseModel):
    canonical_topic: str = Field(min_length=1, max_length=500)
    track: Track


class UnitRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    experiences: list[UnitExperience] = Field(min_length=1, max_length=50)


@router.get("/households/{household_id}/unit")
async def current_unit(household_id: str, _: str = Depends(verify_household_access)):
    return {
        "current": await family_unit_store.current(household_id),
        "upcoming": await family_unit_store.upcoming(household_id),
    }


@router.post("/households/{household_id}/units")
async def enqueue_unit(
    household_id: str, body: UnitRequest, _: str = Depends(verify_household_access)
):
    return await family_unit_store.enqueue(
        household_id,
        body.title,
        [
            {"canonical_topic": e.canonical_topic.strip(), "track": e.track.value}
            for e in body.experiences
        ],
    )


@router.post(
    "/households/{household_id}/units/{queue_id}/experiences/{experience_id}/complete"
)
async def complete_experience(
    household_id: str,
    queue_id: str,
    experience_id: str,
    _: str = Depends(verify_household_access),
):
    try:
        await family_unit_store.complete_experience(
            household_id, queue_id, experience_id
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"completed": True, "mastery_awarded": False}


@router.post("/households/{household_id}/units/{queue_id}/advance")
async def advance_unit(
    household_id: str, queue_id: str, _: str = Depends(verify_household_access)
):
    try:
        await family_unit_store.advance(household_id, queue_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"advanced": True}


class CharacterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    identity: str = Field(default="", max_length=2000)
    role_preferences: list[str] = Field(default_factory=list, max_length=20)
    persistent_traits: list[str] = Field(default_factory=list, max_length=20)
    visual_data: dict = Field(default_factory=dict)


@router.get("/students/{student_id}/character")
async def get_character(student_id: str, _: str = Depends(verify_student_access)):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            'SELECT * FROM "StudentCharacter" WHERE "studentId"=$1', student_id
        )
        return _record(row) if row else None
    finally:
        await conn.close()


@router.put("/students/{student_id}/character")
async def save_character(
    student_id: str, body: CharacterRequest, _: str = Depends(verify_student_access)
):
    conn = await get_db_conn()
    try:
        await conn.execute(
            """INSERT INTO "StudentCharacter"("studentId",name,identity,"rolePreferences","persistentTraits","visualData")
            VALUES ($1,$2,$3,$4::jsonb,$5::jsonb,$6::jsonb) ON CONFLICT ("studentId") DO UPDATE SET
            name=EXCLUDED.name,identity=EXCLUDED.identity,"rolePreferences"=EXCLUDED."rolePreferences",
            "persistentTraits"=EXCLUDED."persistentTraits","visualData"=EXCLUDED."visualData","updatedAt"=NOW()""",
            student_id,
            body.name,
            body.identity,
            json.dumps(body.role_preferences),
            json.dumps(body.persistent_traits),
            json.dumps(body.visual_data),
        )
        return body.model_dump()
    finally:
        await conn.close()


class AttemptRequest(BaseModel):
    canonical_slug: str = Field(min_length=1, max_length=200)
    canonical_revision: str = Field(default="", max_length=200)
    lesson_id: str = Field(min_length=1, max_length=200)
    skill_id: str | None = None
    parent_attempt_id: str | None = None
    kind: Literal[
        "note",
        "artifact",
        "measurement",
        "source",
        "timeline",
        "real_world_action",
        "observation",
        "photo",
        "written_claim",
        "calculation",
        "failed_attempt",
        "revision",
    ]
    content: dict
    submission_key: str = Field(min_length=1, max_length=200)


@router.post("/students/{student_id}/evidence")
async def submit_evidence(
    student_id: str, body: AttemptRequest, _: str = Depends(verify_student_access)
):
    conn = await get_db_conn()
    try:
        async with conn.transaction():
            if body.parent_attempt_id:
                parent = await conn.fetchrow(
                    'SELECT "studentId","canonicalSlug","lessonId" FROM "EvidenceAttempt" WHERE id=$1',
                    body.parent_attempt_id,
                )
                if (
                    not parent
                    or parent["studentId"] != student_id
                    or parent["canonicalSlug"] != body.canonical_slug
                    or parent["lessonId"] != body.lesson_id
                ):
                    raise HTTPException(
                        400,
                        "A revision must reference this learner and this experience.",
                    )
            row = await conn.fetchrow(
                """INSERT INTO "EvidenceAttempt"("studentId","canonicalSlug","canonicalRevision","lessonId","skillId","parentAttemptId",kind,content,"submissionKey")
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9) ON CONFLICT ("studentId","submissionKey") DO NOTHING RETURNING *""",
                student_id,
                body.canonical_slug,
                body.canonical_revision,
                body.lesson_id,
                body.skill_id,
                body.parent_attempt_id,
                body.kind,
                json.dumps(body.content),
                body.submission_key,
            )
            if not row:
                row = await conn.fetchrow(
                    'SELECT * FROM "EvidenceAttempt" WHERE "studentId"=$1 AND "submissionKey"=$2',
                    student_id,
                    body.submission_key,
                )
                # Same key with new content is not a new attempt and must not silently lose work.
                stored = row["content"]
                if isinstance(stored, str):
                    stored = json.loads(stored)
                if (
                    stored != body.content
                    or row["lessonId"] != body.lesson_id
                    or row["canonicalSlug"] != body.canonical_slug
                    or row["canonicalRevision"] != body.canonical_revision
                    or row["kind"] != body.kind
                    or row["skillId"] != body.skill_id
                    or row["parentAttemptId"] != body.parent_attempt_id
                ):
                    raise HTTPException(
                        409, "Submission key already belongs to different evidence."
                    )
            if body.kind == "timeline":
                card = body.content
                if (
                    not card.get("date_start")
                    or not card.get("claim")
                    or not card.get("sources")
                ):
                    raise HTTPException(
                        422, "Timeline evidence requires a date, claim and sources."
                    )
                await conn.execute(
                    """INSERT INTO "TimelineCard"("attemptId","studentId","dateStart","dateEnd",claim,sources,perspectives,"omittedPerspectives","conflictingEvidence",uncertainty)
                  VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8::jsonb,$9::jsonb,$10) ON CONFLICT ("attemptId") DO NOTHING""",
                    row["id"],
                    student_id,
                    card["date_start"],
                    card.get("date_end"),
                    card["claim"],
                    json.dumps(card["sources"]),
                    json.dumps(card.get("perspectives", [])),
                    json.dumps(card.get("omitted_perspectives", [])),
                    json.dumps(card.get("conflicting_evidence", [])),
                    card.get("uncertainty", ""),
                )
            return _record(row)
    finally:
        await conn.close()


@router.get("/students/{student_id}/portfolio")
async def portfolio(student_id: str, _: str = Depends(verify_student_access)):
    conn = await get_db_conn()
    try:
        attempts = await conn.fetch(
            'SELECT * FROM "EvidenceAttempt" WHERE "studentId"=$1 ORDER BY "createdAt",id',
            student_id,
        )
        evaluations = await conn.fetch(
            '''SELECT e.* FROM "EvidenceEvaluation" e JOIN "EvidenceAttempt" a ON a.id=e."attemptId" WHERE a."studentId"=$1 ORDER BY e."createdAt"''',
            student_id,
        )
        return {
            "attempts": [_record(r) for r in attempts],
            "evaluations": [_record(r) for r in evaluations],
        }
    finally:
        await conn.close()


@router.get("/students/{student_id}/timeline")
async def timeline(student_id: str, _: str = Depends(verify_student_access)):
    conn = await get_db_conn()
    try:
        return [
            _record(r)
            for r in await conn.fetch(
                'SELECT * FROM "TimelineCard" WHERE "studentId"=$1 ORDER BY "createdAt",id',
                student_id,
            )
        ]
    finally:
        await conn.close()


@router.get("/students/{student_id}/skill-state")
async def skill_state(student_id: str, _: str = Depends(verify_student_access)):
    from app.services.curriculum_state import get_curriculum_state

    return await get_curriculum_state(student_id)


class EvaluationRequest(BaseModel):
    skill_id: str = Field(min_length=1)
    result: Literal["developing", "demonstrated", "secure"]
    reasoning: str = Field(min_length=1, max_length=10000)


@router.post("/students/{student_id}/evidence/{attempt_id}/evaluate")
async def review_evidence(
    student_id: str,
    attempt_id: str,
    body: EvaluationRequest,
    evaluator: str = Depends(verify_student_access),
):
    # Access to one's own work is not authority to self-award mastery.
    conn = await get_db_conn()
    try:
        role = str(
            await conn.fetchval('SELECT role FROM "User" WHERE id=$1', evaluator) or ""
        ).upper()
    finally:
        await conn.close()
    if role not in ("PARENT", "ADMIN"):
        raise HTTPException(
            403, "A parent or authorized reviewer must evaluate evidence."
        )
    from app.services.curriculum_state import evaluate_evidence

    try:
        return await evaluate_evidence(
            attempt_id=attempt_id,
            student_id=student_id,
            skill_id=body.skill_id,
            evaluator_id=evaluator,
            result=body.result,
            reasoning=body.reasoning,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/households/{household_id}/timeline")
async def family_timeline(household_id: str, _: str = Depends(verify_household_access)):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            '''SELECT t.*,u.name AS "studentName" FROM "TimelineCard" t
          JOIN "User" u ON u.id=t."studentId" WHERE u."parentId"=$1
          ORDER BY CASE WHEN t."dateStart" ~ '^-?[0-9]+' THEN substring(t."dateStart" FROM '^-?[0-9]+')::numeric END NULLS LAST,t."createdAt"''',
            household_id,
        )
        return [_record(row) for row in rows]
    finally:
        await conn.close()
