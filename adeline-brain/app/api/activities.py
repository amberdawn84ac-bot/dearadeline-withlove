"""Life activity evidence API.

A learner tells Adeline what they actually did. We record the activity immediately,
map it to relevant Oklahoma Academic Standards, and treat it as evidence toward
those standards. Duration is optional metadata, never the basis for learning value.
"""
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import get_current_user_id, verify_student_access
from app.config import ANTHROPIC_API_KEY, GOOGLE_API_KEY, create_llm
from app.connections.journal_store import journal_store
from app.connections.postgres import get_db_session
from app.schemas.api_models import Track
from app.services.standards_mapper import MasteryEvidence, StandardsMapper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activities", tags=["activities"])


@asynccontextmanager
async def _get_conn():
    from app.config import get_db_conn
    conn = await get_db_conn()
    try:
        yield conn
    finally:
        await conn.close()


TRACK_SUBJECTS: dict[str, list[str]] = {
    "CREATION_SCIENCE": ["science", "chemistry", "biology", "physics", "earth science"],
    "HEALTH_NATUROPATHY": ["health", "nutrition", "human biology"],
    "HOMESTEADING": ["agriculture", "ecology", "applied science"],
    "GOVERNMENT_ECONOMICS": ["civics", "government", "economics"],
    "JUSTICE_CHANGEMAKING": ["civics", "social studies", "argument"],
    "DISCIPLESHIP": ["ethics", "culture", "social studies"],
    "TRUTH_HISTORY": ["history", "research", "primary sources"],
    "ENGLISH_LITERATURE": ["reading", "writing", "language arts"],
    "APPLIED_MATHEMATICS": ["math", "measurement", "ratios", "data"],
    "CREATIVE_ECONOMY": ["design", "entrepreneurship", "communication"],
}

_SYSTEM_PROMPT = """You are Adeline's standards registrar. Read a learner's real-world activity and identify what concepts it genuinely demonstrates or begins to demonstrate.

Do not award learning based on time. Do not inflate mastery. A single activity is evidence, not proof that an entire standard is mastered.

Return JSON only:
{
  "course_title": "short human-readable title",
  "activity_description": "1-2 sentences describing what the learner did and the learning evidence present",
  "tracks": ["TRACK_NAME"],
  "concepts_demonstrated": ["specific concept"],
  "concepts_to_explore": ["natural next concept or gap"],
  "standard_codes": ["only codes from the supplied candidate standards that are genuinely supported"]
}

Choose no more than 3 tracks and no more than 6 standards. Prefer a small, defensible mapping over a broad one."""


def _grade_number(grade_level: str) -> int:
    match = re.search(r"\d+", grade_level or "")
    if not match:
        return 9
    return max(1, min(12, int(match.group())))


async def _candidate_standards(grade: int) -> list[dict]:
    mapper = StandardsMapper()
    candidates: list[dict] = []
    for track in TRACK_SUBJECTS:
        try:
            standards = await mapper.get_standards_for_track(track, (grade, grade))
        except Exception:
            standards = []
        for standard in standards[:30]:
            candidates.append({
                "code": standard.code,
                "track": track,
                "description": standard.description,
            })
    return candidates


async def _map_activity(description: str, grade_level: str) -> dict:
    if not ANTHROPIC_API_KEY and not GOOGLE_API_KEY and not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("No LLM API key set — cannot map activity")

    grade = _grade_number(grade_level)
    candidates = await _candidate_standards(grade)
    candidate_text = "\n".join(
        f"- {item['code']} [{item['track']}]: {item['description']}" for item in candidates[:180]
    )
    if not candidate_text:
        candidate_text = "No candidate standards were available. Return an empty standard_codes list."

    llm = create_llm(max_tokens=900)
    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Grade: {grade_level}\n\n"
            f"Learner said: {description}\n\n"
            f"Candidate Oklahoma standards:\n{candidate_text}"
        )),
    ])
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("[activities] invalid mapper JSON: %s", exc)
        raise HTTPException(status_code=500, detail="Activity mapping failed") from exc

    valid_codes = {item["code"] for item in candidates}
    result["standard_codes"] = [
        code for code in result.get("standard_codes", []) if code in valid_codes
    ][:6]
    valid_tracks = {track.value for track in Track}
    result["tracks"] = [track for track in result.get("tracks", []) if track in valid_tracks][:3]
    return result


class ActivityReportRequest(BaseModel):
    student_id: str
    grade_level: str
    description: str = Field(min_length=3, max_length=3000)
    time_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    activity_date: Optional[str] = None


class CreditedTrack(BaseModel):
    track: str
    subjects: list[str]
    credit_type: str


class ActivityReportResponse(BaseModel):
    activity_id: str
    course_title: str
    activity_description: str
    credit_hours: float
    credited_tracks: list[CreditedTrack]
    standard_codes: list[str] = []
    concepts_demonstrated: list[str] = []
    concepts_to_explore: list[str] = []
    sealed: bool
    adeline_note: str


class ActivityEntry(BaseModel):
    activity_id: str
    course_title: str
    activity_description: str
    credit_hours: float
    primary_track: str
    credit_type: str
    activity_date: str
    sealed_at: str


class ActivityListResponse(BaseModel):
    student_id: str
    activities: list[ActivityEntry]
    total: int
    total_credits: float


@router.post("/report", response_model=ActivityReportResponse)
async def report_activity(
    body: ActivityReportRequest,
    student_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    mapped = await _map_activity(body.description, body.grade_level)
    tracks = mapped.get("tracks", []) or ["ENGLISH_LITERATURE"]
    primary_track = tracks[0]
    course_title = mapped.get("course_title") or "Real-World Learning"
    activity_desc = mapped.get("activity_description") or body.description
    standards = mapped.get("standard_codes", [])
    concepts = mapped.get("concepts_demonstrated", [])[:8]
    next_concepts = mapped.get("concepts_to_explore", [])[:6]

    activity_id = f"activity-{uuid.uuid4()}"
    activity_date = body.activity_date or datetime.now(timezone.utc).date().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    credited_tracks = [
        CreditedTrack(
            track=track,
            subjects=TRACK_SUBJECTS.get(track, ["interdisciplinary learning"]),
            credit_type="CORE" if track in {
                "CREATION_SCIENCE", "APPLIED_MATHEMATICS", "ENGLISH_LITERATURE",
                "GOVERNMENT_ECONOMICS", "TRUTH_HISTORY"
            } else "ELECTIVE",
        )
        for track in tracks
    ]

    try:
        await journal_store.seal(
            student_id=student_id,
            lesson_id=activity_id,
            track=primary_track,
            completed_blocks=1,
            sources=[],
        )
    except Exception as exc:
        logger.warning("[activities] Journal seal failed: %s", exc)

    try:
        async with _get_conn() as conn:
            await conn.execute(
                """
                INSERT INTO "TranscriptEntry" (
                    id, "studentId", "lessonId", "courseTitle", track,
                    "oasStandards", "activityDescription", "creditHours", "creditType",
                    "gradeLetter", "percentScore", "isHomesteadCredit", "agentName",
                    "researcherActivated", "completedAt", "sealedAt", "xapiStatementId"
                ) VALUES (
                    $1, $2, $3, $4, $5::"Track", $6, $7, 0, $8::"CreditType",
                    NULL, NULL, false, 'RegistrarAgent'::"AgentName", false,
                    $9::date, $10::timestamptz, NULL
                )
                ON CONFLICT ("studentId", "lessonId") DO UPDATE SET
                    "courseTitle" = EXCLUDED."courseTitle",
                    "oasStandards" = EXCLUDED."oasStandards",
                    "activityDescription" = EXCLUDED."activityDescription",
                    "sealedAt" = EXCLUDED."sealedAt"
                """,
                str(uuid.uuid4()), student_id, activity_id, course_title, primary_track,
                standards, activity_desc, credited_tracks[0].credit_type, activity_date, now_iso,
            )
    except Exception as exc:
        logger.exception("[activities] TranscriptEntry write failed")
        raise HTTPException(status_code=500, detail=f"Failed to record activity: {exc}") from exc

    # Activity evidence starts as developing. It counts as evidence without pretending
    # a single real-world mention proves full mastery of a standard.
    mapper = StandardsMapper(db)
    recorded_standards: list[str] = []
    for standard_id in standards:
        try:
            await mapper.record_mastery_evidence(
                student_id=student_id,
                standard_id=standard_id,
                evidence=MasteryEvidence(
                    evidence_type="quiz",
                    score=40,
                    description=f"Real-world activity evidence: {activity_desc}",
                ),
                pg_session=db,
            )
            recorded_standards.append(standard_id)
        except Exception as exc:
            logger.warning("[activities] standard evidence failed for %s: %s", standard_id, exc)
    try:
        await db.commit()
    except Exception:
        await db.rollback()

    concept_text = ", ".join(concepts[:3])
    next_text = next_concepts[0] if next_concepts else ""
    adeline_note = "I saved that."
    if concept_text:
        adeline_note += f" It gives us evidence around {concept_text}."
    if next_text:
        adeline_note += f" A natural next thread is {next_text}."

    return ActivityReportResponse(
        activity_id=activity_id,
        course_title=course_title,
        activity_description=activity_desc,
        credit_hours=0.0,
        credited_tracks=credited_tracks,
        standard_codes=recorded_standards or standards,
        concepts_demonstrated=concepts,
        concepts_to_explore=next_concepts,
        sealed=True,
        adeline_note=adeline_note,
    )


@router.get("/{student_id}", response_model=ActivityListResponse)
async def list_activities(
    student_id: str,
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_student_access),
):
    async with _get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT "lessonId", "courseTitle", track, "creditHours", "creditType",
                   "activityDescription", "completedAt", "sealedAt"
            FROM "TranscriptEntry"
            WHERE "studentId" = $1 AND "lessonId" LIKE 'activity-%'
            ORDER BY "completedAt" DESC
            LIMIT $2
            """,
            student_id, limit,
        )

    entries = [
        ActivityEntry(
            activity_id=str(row["lessonId"]),
            course_title=str(row["courseTitle"]),
            activity_description=str(row["activityDescription"] or ""),
            credit_hours=float(row["creditHours"] or 0),
            primary_track=str(row["track"]),
            credit_type=str(row["creditType"]),
            activity_date=row["completedAt"].isoformat() if row["completedAt"] else "",
            sealed_at=row["sealedAt"].isoformat() if row["sealedAt"] else "",
        )
        for row in rows
    ]
    return ActivityListResponse(
        student_id=student_id,
        activities=entries,
        total=len(entries),
        total_credits=round(sum(item.credit_hours for item in entries), 3),
    )
