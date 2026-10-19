"""Persisted parent-defined course scopes and evidence-backed transcript approval."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.middleware import verify_student_access
from app.config import get_db_conn
from app.schemas.api_models import Track
from app.services.learning_loop import (
    course_progress,
    known_skills,
    refresh_learning_projection,
)

router = APIRouter(prefix="", tags=["credits"])
BUCKETS = {
    "ENGLISH_CORE",
    "MATH_CORE",
    "SCIENCE_CORE",
    "SOCIAL_STUDIES",
    "WORLD_LANGUAGE",
    "PERSONAL_FINANCE",
    "FINE_ARTS",
    "ELECTIVES",
}


class ProfileResponse(BaseModel):
    profile_key: str
    name: str
    description: str
    oasOptional: bool
    creditHourWeighting: dict


def load_oklahoma_profiles() -> dict:
    return json.loads(
        (
            Path(__file__).resolve().parent.parent / "data/oklahoma_profiles.json"
        ).read_text()
    )


async def require_reviewer(conn, user: str):
    role = str(
        await conn.fetchval('SELECT role FROM "User" WHERE id=$1', user) or ""
    ).upper()
    if role not in ("PARENT", "ADMIN"):
        raise HTTPException(
            403, "A parent or authorized reviewer must approve academic records."
        )


@router.get("/credits/available-profiles")
async def list_available_profiles():
    return [{"key": k, **v} for k, v in load_oklahoma_profiles().items()]


@router.get("/credits/{student_id}/profile")
async def get_student_profile(student_id: str, _user=Depends(verify_student_access)):
    conn = await get_db_conn()
    try:
        key = (
            await conn.fetchval(
                'SELECT "profileKey" FROM "StudentCreditProfile" WHERE "studentId"=$1',
                student_id,
            )
            or "oklahoma_flexible_homeschool"
        )
        return {
            "studentId": student_id,
            "profileKey": key,
            "profile": load_oklahoma_profiles()[key],
        }
    finally:
        await conn.close()


@router.put("/credits/{student_id}/profile")
async def set_student_profile(
    student_id: str, profile_key: str, _user=Depends(verify_student_access)
):
    if profile_key not in load_oklahoma_profiles():
        raise HTTPException(404, "Profile not found")
    conn = await get_db_conn()
    try:
        await require_reviewer(conn, _user)
        await conn.execute(
            """INSERT INTO "StudentCreditProfile"("studentId","profileKey") VALUES ($1,$2)
            ON CONFLICT ("studentId") DO UPDATE SET "profileKey"=$2,"updatedAt"=NOW()""",
            student_id,
            profile_key,
        )
    finally:
        await conn.close()
    await refresh_learning_projection(student_id)
    return {
        "studentId": student_id,
        "profileKey": profile_key,
        "message": "Profile saved.",
    }


class ScopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    title: str = Field(min_length=3, max_length=200)
    track: Track
    bucket: str
    credit_units: float = Field(gt=0, le=2)
    skill_ids: list[str] = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=30, max_length=4000)

    @field_validator('title', 'rationale')
    @classmethod
    def meaningful_text(cls, value, info):
        value = value.strip()
        if len(value) < (30 if info.field_name == 'rationale' else 3):
            raise ValueError('Provide a meaningful course title and scope rationale.')
        return value



@router.post("/credits/{student_id}/courses")
async def define_course(
    student_id: str, body: ScopeRequest, _user=Depends(verify_student_access)
):
    if body.bucket not in BUCKETS or len(set(body.skill_ids)) != len(body.skill_ids):
        raise HTTPException(
            422, "Choose a valid bucket and distinct curriculum targets."
        )
    conn = await get_db_conn()
    try:
        await require_reviewer(conn, _user)
        skills = await known_skills(conn, body.skill_ids)
        if {s["id"] for s in skills} != set(body.skill_ids):
            raise HTTPException(
                422, "Every course target must exist in the curriculum map."
            )
        row = await conn.fetchrow(
            """INSERT INTO "CourseScope"("studentId",title,track,bucket,"creditUnits","skillIds",rationale,"createdBy")
            VALUES ($1,$2,$3::"Track",$4,$5,$6,$7,$8) RETURNING id""",
            student_id,
            body.title.strip(),
            body.track.value,
            body.bucket,
            body.credit_units,
            body.skill_ids,
            body.rationale.strip(),
            _user,
        )
        return {"id": row["id"]}
    finally:
        await conn.close()


@router.get("/credits/{student_id}")
async def get_credit_dashboard(student_id: str, _user=Depends(verify_student_access)):
    conn = await get_db_conn()
    try:
        profile = (
            await conn.fetchval(
                'SELECT "profileKey" FROM "StudentCreditProfile" WHERE "studentId"=$1',
                student_id,
            )
            or "oklahoma_flexible_homeschool"
        )
        scopes = await conn.fetch(
            'SELECT * FROM "CourseScope" WHERE "studentId"=$1 ORDER BY "createdAt",id',
            student_id,
        )
        awards = {
            r["scopeId"]: dict(r)
            for r in await conn.fetch(
                'SELECT * FROM "CourseAward" WHERE "studentId"=$1', student_id
            )
        }
        courses = []
        bucket_totals = {}
        for scope in scopes:
            progress = await course_progress(conn, scope)
            award = awards.get(scope["id"])
            totals = bucket_totals.setdefault(
                scope["bucket"],
                {
                    "skills": set(),
                    "demonstrated": set(),
                    "attempts": set(),
                    "credits": 0.0,
                },
            )
            totals["skills"].update(scope["skillIds"])
            totals["demonstrated"].update(progress["demonstrated"])
            totals["attempts"].update(e["attemptId"] for e in progress["evidence"])
            if award:
                totals["credits"] += scope["creditUnits"]
            target_details = await known_skills(conn, scope["skillIds"])
            courses.append(
                {
                    "proposalId": scope["id"],
                    "bucket": scope["bucket"],
                    "externalCourseName": scope["title"],
                    "hoursEarned": 0,
                    "creditUnits": scope["creditUnits"],
                    "masteryPercentage": progress["coverage"],
                    "masteryGrade": "Reviewed" if award else "Pending",
                    "isApproved": bool(award),
                    "proposedAt": scope["createdAt"],
                    "approvedAt": award["approvedAt"] if award else None,
                    "ready": progress["ready"],
                    "missingSkills": progress["missing"],
                    "conflictingSkills": progress["conflicts"],
                    "skillIds": scope["skillIds"],
                    "targets": target_details,
                    "evidenceCount": len(progress["evidence"]),
                    "independentLessons": progress["lesson_count"],
                    "rationale": scope["rationale"],
                }
            )
        return {
            "studentId": student_id,
            "currentProfile": profile,
            "buckets": [
                {
                    "bucket": name,
                    "hoursEarned": 0,
                    "evidenceCount": len(data["attempts"]),
                    "masteryAverage": len(data["demonstrated"]) / len(data["skills"]),
                    "masteryGrade": "Reviewed evidence",
                    "creditEarned": data["credits"],
                }
                for name, data in bucket_totals.items()
            ],
            "pendingProposals": [c for c in courses if not c["isApproved"]],
            "approvedCourses": [c for c in courses if c["isApproved"]],
        }
    finally:
        await conn.close()


@router.post("/credits/{student_id}/approve/{proposal_id}")
async def approve_course_proposal(
    student_id: str, proposal_id: str, _user=Depends(verify_student_access)
):
    conn = await get_db_conn()
    try:
        async with conn.transaction():
            await require_reviewer(conn, _user)
            # Serialize all approvals for a learner, including competing course scopes.
            await conn.fetchval(
                'SELECT id FROM "User" WHERE id=$1 FOR UPDATE', student_id
            )
            scope = await conn.fetchrow(
                'SELECT * FROM "CourseScope" WHERE id=$1 AND "studentId"=$2 FOR UPDATE',
                proposal_id,
                student_id,
            )
            if not scope:
                raise HTTPException(404, "Course not found.")
            if await conn.fetchval(
                'SELECT "scopeId" FROM "CourseAward" WHERE "scopeId"=$1', proposal_id
            ):
                return {
                    "proposalId": proposal_id,
                    "isApproved": True,
                    "message": "Already approved; no duplicate credit.",
                }
            progress = await course_progress(conn, scope)
            if not progress["ready"]:
                raise HTTPException(
                    409,
                    "Review all course targets with independent evidence from at least two lessons; resolve already-credited targets first.",
                )
            standard_rows = await conn.fetch(
                'SELECT code FROM "OASStandard" WHERE code=ANY($1::text[])',
                scope["skillIds"],
            )
            transcript_id = str(uuid4())
            snapshot = {"scope": dict(scope), "progress": progress}
            await conn.execute(
                """INSERT INTO "TranscriptEntry"(id,"studentId","lessonId","courseTitle",track,"oasStandards",
                "activityDescription","creditHours","creditType","completedAt","sealedAt")
                VALUES ($1,$2,$3,$4,$5::"Track",$6,$7,$8,$9::"CreditType",NOW(),NOW())""",
                transcript_id,
                student_id,
                "course:" + proposal_id,
                scope["title"],
                scope["track"],
                [r["code"] for r in standard_rows],
                "Parent-approved course scope and preserved evidence: "
                + scope["rationale"],
                scope["creditUnits"],
                "FINE_ARTS"
                if scope["bucket"] == "FINE_ARTS"
                else "ELECTIVE"
                if scope["bucket"] == "ELECTIVES"
                else "CORE",
            )
            await conn.execute(
                """INSERT INTO "CourseAward"("scopeId","studentId","approvedBy",snapshot,"transcriptId")
                VALUES ($1,$2,$3,$4::jsonb,$5)""",
                proposal_id,
                student_id,
                _user,
                json.dumps(snapshot, default=str),
                transcript_id,
            )
            for skill in scope["skillIds"]:
                await conn.execute(
                    'INSERT INTO "CourseSkillAllocation"("studentId","skillId","scopeId") VALUES ($1,$2,$3)',
                    student_id,
                    skill,
                    proposal_id,
                )
    finally:
        await conn.close()
    await refresh_learning_projection(student_id)
    return {
        "proposalId": proposal_id,
        "isApproved": True,
        "message": "Approved and recorded on the transcript.",
    }


@router.get("/credits/{student_id}/targets")
async def available_course_targets(
    student_id: str, q: str = "", _user=Depends(verify_student_access)
):
    if len(q) > 100:
        raise HTTPException(422, "Search is too long.")
    conn = await get_db_conn()
    try:
        if q.strip():
            return [
                dict(r)
                for r in await conn.fetch(
                    """SELECT id,title,'not_reviewed' AS status FROM (
                SELECT code AS id,description AS title FROM "OASStandard"
                UNION ALL SELECT id,title FROM "CurriculumConcept") targets
                WHERE id ILIKE $1 OR title ILIKE $1 ORDER BY id LIMIT 50""",
                    "%" + q.strip() + "%",
                )
            ]
        return [
            dict(r)
            for r in await conn.fetch(
                '''SELECT s."skillId" AS id,s.status,
            COALESCE(o.description,c.title,s."skillId") AS title
            FROM "StudentSkillState" s LEFT JOIN "OASStandard" o ON o.code=s."skillId"
            LEFT JOIN "CurriculumConcept" c ON c.id=s."skillId"
            WHERE s."studentId"=$1 AND (o.code IS NOT NULL OR c.id IS NOT NULL)
            ORDER BY s."skillId"''',
                student_id,
            )
        ]
    finally:
        await conn.close()
