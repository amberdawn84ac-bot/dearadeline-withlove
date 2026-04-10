"""
Learning Records API — xAPI statement persistence + CASE transcript entries.

Endpoints:
  POST /learning/record          — persist one or more xAPI statements from RegistrarAgent
  POST /learning/transcript      — seal a CASE credit TranscriptEntry for a lesson
  GET  /learning/transcript/{student_id}  — full transcript for a student
  GET  /learning/reviews/{student_id}     — due SpacedRepetitionCards for SM-2 widget
  POST /learning/reviews         — submit SM-2 quality rating, update card interval
  GET  /learning/xapi/{student_id}        — raw xAPI statements (paginated)

All writes are idempotent via INSERT … ON CONFLICT DO NOTHING or DO UPDATE.
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from app.api.middleware import get_current_user_id, verify_student_access, require_internal_key
from pydantic import BaseModel, Field

from app.algorithms.spaced_repetition import sm2, is_due, overdue_days
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning", tags=["learning"])


# ── Request / Response models ─────────────────────────────────────────────────

class XAPIStatementIn(BaseModel):
    id:            str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id:    str
    lesson_id:     str
    block_id:      Optional[str] = None
    verb:          str
    object_id:     str
    object_name:   str
    track:         str
    oas_standard:  str = ""
    grade_level:   str = ""
    is_homestead:  bool = False
    agent_name:    Optional[str] = None
    block_type:    str = ""
    duration_ms:   Optional[int] = None
    completion:    bool = False
    response:      Optional[str] = None
    score_raw:     Optional[float] = None
    timestamp:     Optional[str] = None
    statement_json: dict = Field(default_factory=dict)

class RecordLearningRequest(BaseModel):
    statements: list[XAPIStatementIn]

class RecordLearningResponse(BaseModel):
    recorded:  int
    lesson_id: str


class TranscriptEntryIn(BaseModel):
    id:                   str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id:           str
    lesson_id:            str
    course_title:         str
    track:                str
    oas_standards:        list[str] = []
    activity_description: str = ""
    credit_hours:         float = 0.0
    credit_type:          str = "ELECTIVE"
    grade_letter:         Optional[str] = None
    percent_score:        Optional[float] = None
    is_homestead_credit:  bool = False
    agent_name:           Optional[str] = None
    researcher_activated: bool = False
    completed_at:         Optional[str] = None
    xapi_statement_id:    Optional[str] = None

class SealTranscriptResponse(BaseModel):
    sealed:        bool
    entry_id:      str
    credit_hours:  float
    credit_type:   str


class SM2ReviewSubmit(BaseModel):
    concept_id: str
    quality:    int          # 0-5 per SM-2 spec
    track:      str = "TRUTH_HISTORY"

class SM2ReviewResponse(BaseModel):
    concept_id:   str
    new_interval: int
    ease_factor:  float
    repetitions:  int
    due_at:       str


class DueReview(BaseModel):
    review_id:     str
    concept_id:    str
    concept_name:  str
    track:         str
    repetitions:   int
    overdue_days:  float

class DueReviewsResponse(BaseModel):
    reviews: list[DueReview]
    total:   int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@asynccontextmanager
async def _get_conn():
    """Get an asyncpg connection via config helper (SSL + Supabase pooler compatible)."""
    from app.config import get_db_conn
    conn = await get_db_conn()
    try:
        yield conn
    finally:
        await conn.close()


# ── POST /learning/record ─────────────────────────────────────────────────────

@router.post("/record", response_model=RecordLearningResponse)
async def record_learning(
    payload: RecordLearningRequest,
    _key: str = Depends(require_internal_key),
):
    """
    Persist xAPI LearningActivity statements from the RegistrarAgent.
    Called automatically by /lesson/generate after lesson assembly.
    Idempotent — duplicate statement IDs are silently ignored.
    """
    recorded = 0

    async with _get_conn() as conn:
        for stmt in payload.statements:
            ts = stmt.timestamp or _now_iso()
            try:
                await conn.execute(
                    """
                    INSERT INTO "LearningRecord" (
                        id, "studentId", "lessonId", "blockId",
                        verb, "objectId", "objectName", track,
                        "oasStandard", "gradeLevel", "isHomestead",
                        "agentName", "blockType",
                        "durationMs", completion, response,
                        "scoreRaw", "statementJson", timestamp
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7, $8,
                        $9, $10, $11,
                        $12, $13,
                        $14, $15, $16,
                        $17, $18::jsonb, $19::timestamp
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    stmt.id, stmt.student_id, stmt.lesson_id, stmt.block_id,
                    stmt.verb.lower(), stmt.object_id, stmt.object_name, stmt.track,
                    stmt.oas_standard, stmt.grade_level, stmt.is_homestead,
                    stmt.agent_name, stmt.block_type,
                    stmt.duration_ms, stmt.completion, stmt.response,
                    stmt.score_raw, json.dumps(stmt.statement_json), ts,
                )
                recorded += 1
            except Exception as e:
                logger.warning(f"[LearningRecord] Failed to insert statement {stmt.id}: {e}")

    lesson_id = payload.statements[0].lesson_id if payload.statements else ""
    logger.info(f"[LearningRecord] Recorded {recorded}/{len(payload.statements)} statements for lesson={lesson_id}")
    return RecordLearningResponse(recorded=recorded, lesson_id=lesson_id)


# ── POST /learning/transcript ─────────────────────────────────────────────────

@router.post("/transcript", response_model=SealTranscriptResponse)
async def seal_transcript(
    entry: TranscriptEntryIn,
    _key: str = Depends(require_internal_key),
):
    """
    Persist a CASE-compatible TranscriptEntry for a completed lesson.
    Upserts on (studentId, lessonId) — resealing a lesson updates the record.
    """
    completed_at = entry.completed_at or _now_iso()
    sealed_at    = _now_iso()

    async with _get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO "TranscriptEntry" (
                id, "studentId", "lessonId", "courseTitle", track,
                "oasStandards", "activityDescription",
                "creditHours", "creditType",
                "gradeLetter", "percentScore",
                "isHomesteadCredit", "agentName", "researcherActivated",
                "completedAt", "sealedAt", "xapiStatementId"
            ) VALUES (
                $1, $2, $3, $4, $5::\"Track\",
                $6, $7,
                $8, $9::\"CreditType\",
                $10::\"GradeLetter\", $11,
                $12, $13::\"AgentName\", $14,
                $15::timestamp, $16::timestamp, $17
            )
            ON CONFLICT ("studentId", "lessonId") DO UPDATE SET
                "courseTitle"         = EXCLUDED."courseTitle",
                "creditHours"         = EXCLUDED."creditHours",
                "creditType"          = EXCLUDED."creditType",
                "activityDescription" = EXCLUDED."activityDescription",
                "researcherActivated" = EXCLUDED."researcherActivated",
                "sealedAt"            = EXCLUDED."sealedAt"
            """,
            entry.id, entry.student_id, entry.lesson_id, entry.course_title, entry.track,
            entry.oas_standards, entry.activity_description,
            entry.credit_hours, entry.credit_type,
            entry.grade_letter, entry.percent_score,
            entry.is_homestead_credit, entry.agent_name, entry.researcher_activated,
            completed_at, sealed_at, entry.xapi_statement_id,
        )

    logger.info(
        f"[Transcript] Sealed entry for student={entry.student_id}, "
        f"lesson={entry.lesson_id}, credits={entry.credit_hours} {entry.credit_type}"
    )
    return SealTranscriptResponse(
        sealed=True,
        entry_id=entry.id,
        credit_hours=entry.credit_hours,
        credit_type=entry.credit_type,
    )


# ── GET /learning/transcript/{student_id} ─────────────────────────────────────

@router.get("/transcript/{student_id}")
async def get_transcript(
    student_id: str,
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_student_access),
):
    """Return paginated transcript entries for a student, newest first."""
    async with _get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT id, "lessonId", "courseTitle", track,
                   "creditHours", "creditType", "gradeLetter", "percentScore",
                   "oasStandards", "activityDescription",
                   "isHomesteadCredit", "agentName", "researcherActivated",
                   "completedAt", "sealedAt"
            FROM "TranscriptEntry"
            WHERE "studentId" = $1
            ORDER BY "completedAt" DESC
            LIMIT $2
            """,
            student_id, limit,
        )
    entries = [dict(r) for r in rows]
    total_credits = sum(float(e.get("creditHours", 0) or 0) for e in entries)
    return {
        "student_id":    student_id,
        "entries":       entries,
        "total_entries": len(entries),
        "total_credits": round(total_credits, 2),
    }


# ── GET /learning/reviews/{student_id} ────────────────────────────────────────

@router.get("/reviews/{student_id}", response_model=DueReviewsResponse)
async def get_due_reviews(
    student_id: str,
    limit: int = Query(20, le=50),
    _user_id: str = Depends(verify_student_access),
):
    """
    Return SpacedRepetitionCards that are due for review today.
    Ordered by most overdue first.
    """
    try:
        from datetime import datetime as _dt
        now = _dt.utcnow()  # naive UTC — matches DB TIMESTAMP without timezone

        async with _get_conn() as conn:
            rows = await conn.fetch(
                """
                SELECT id, "conceptId", "conceptName", track, repetitions, "dueAt"
                FROM "SpacedRepetitionCard"
                WHERE "studentId" = $1
                  AND "dueAt" <= $2
                ORDER BY "dueAt" ASC
                LIMIT $3
                """,
                student_id, now, limit,
            )

        reviews = [
            DueReview(
                review_id=str(r["id"]),
                concept_id=str(r["conceptId"]),
                concept_name=str(r["conceptName"]),
                track=str(r["track"]),
                repetitions=int(r["repetitions"]),
                overdue_days=overdue_days(r["dueAt"]),
            )
            for r in rows
        ]
        return DueReviewsResponse(reviews=reviews, total=len(reviews))
    except Exception as e:
        logger.error(f"[Reviews] Failed to fetch due reviews for {student_id}: {e}")
        # Return empty list instead of 500 error
        return DueReviewsResponse(reviews=[], total=0)


# ── POST /learning/reviews ────────────────────────────────────────────────────

@router.post("/reviews", response_model=SM2ReviewResponse)
async def submit_review(
    payload: SM2ReviewSubmit,
    student_id: str = Depends(get_current_user_id),
):
    """
    Submit an SM-2 quality rating (0–5) for a concept card.
    Updates the card's interval, ease factor, repetitions, and due date.
    Creates the card if it doesn't exist yet (first review auto-seeds it).
    """
    if not 0 <= payload.quality <= 5:
        raise HTTPException(status_code=422, detail="quality must be 0–5")

    now  = datetime.now(timezone.utc)

    async with _get_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT interval, "easeFactor", repetitions
            FROM "SpacedRepetitionCard"
            WHERE "studentId" = $1 AND "conceptId" = $2
            """,
            student_id, payload.concept_id,
        )

        current_interval    = int(row["interval"]) if row else 1
        current_ease        = float(row["easeFactor"]) if row else 2.5
        current_repetitions = int(row["repetitions"]) if row else 0

        result = sm2(
            quality=payload.quality,
            interval=current_interval,
            ease_factor=current_ease,
            repetitions=current_repetitions,
        )

        await conn.execute(
            """
            INSERT INTO "SpacedRepetitionCard" (
                id, "studentId", "conceptId", "conceptName", track,
                interval, "easeFactor", repetitions,
                "lastQuality", "dueAt", "lastReviewedAt"
            ) VALUES (
                $1, $2, $3, $4, $11::\"Track\",
                $5, $6, $7,
                $8, $9::timestamp, $10::timestamp
            )
            ON CONFLICT ("studentId", "conceptId") DO UPDATE SET
                interval          = EXCLUDED.interval,
                "easeFactor"      = EXCLUDED."easeFactor",
                repetitions       = EXCLUDED.repetitions,
                "lastQuality"     = EXCLUDED."lastQuality",
                "dueAt"           = EXCLUDED."dueAt",
                "lastReviewedAt"  = EXCLUDED."lastReviewedAt",
                "updatedAt"       = now()
            """,
            str(uuid.uuid4()), student_id, payload.concept_id,
            payload.concept_id,   # conceptName defaults to id until explicitly set
            result.interval, result.ease_factor, result.repetitions,
            payload.quality, result.next_due_at.isoformat(), now.isoformat(),
            payload.track,
        )

    logger.info(
        f"[SM2] Review submitted: student={student_id}, "
        f"concept={payload.concept_id}, quality={payload.quality}, "
        f"new_interval={result.interval}d"
    )
    return SM2ReviewResponse(
        concept_id=payload.concept_id,
        new_interval=result.interval,
        ease_factor=result.ease_factor,
        repetitions=result.repetitions,
        due_at=result.next_due_at.isoformat(),
    )
