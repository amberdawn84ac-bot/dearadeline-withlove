"""
Activities API — /activities/*

Students tell Adeline what they did at home and receive academic credit.
This is the life_to_credit engine: baking becomes Chemistry, gardening becomes
Biology, building becomes Engineering, etc.

No Witness Protocol — these are student-reported real-world activities, not
lesson content. Adeline trusts the student and records what they did.

POST /activities/report           — submit a home activity, receive credit
GET  /activities/{student_id}     — list a student's credited activities
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.api_models import Track, UserRole
from app.api.middleware import require_role
from app.connections.journal_store import journal_store
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activities", tags=["activities"])


@asynccontextmanager
async def _get_conn():
    """Get an asyncpg connection via config helper (SSL + Supabase pooler compatible)."""
    from app.config import get_db_conn
    conn = await get_db_conn()
    try:
        yield conn
    finally:
        await conn.close()


# ── Life-to-Credit mapping (mirrors adeline.config.toml [life_to_credit]) ─────
#
# Keys are activity categories. Values list the academic subjects + tracks
# that activity earns credit in.

LIFE_TO_CREDIT: dict[str, dict] = {
    "baking": {
        "subjects":    ["Chemistry: Thermodynamics & Fermentation", "Math: Ratios & Measurement"],
        "tracks":      [Track.CREATION_SCIENCE, Track.APPLIED_MATHEMATICS],
        "credit_type": "CORE",
    },
    "cooking": {
        "subjects":    ["Chemistry: Applied Chemistry", "Math: Measurement & Fractions", "Health: Nutrition"],
        "tracks":      [Track.CREATION_SCIENCE, Track.APPLIED_MATHEMATICS, Track.HEALTH_NATUROPATHY],
        "credit_type": "CORE",
    },
    "gardening": {
        "subjects":    ["Biology: Botany & Ecology", "Chemistry: Soil Science"],
        "tracks":      [Track.HOMESTEADING, Track.CREATION_SCIENCE],
        "credit_type": "HOMESTEAD",
    },
    "building": {
        "subjects":    ["Engineering: Structural Design", "Math: Geometry & Budgeting"],
        "tracks":      [Track.HOMESTEADING, Track.APPLIED_MATHEMATICS],
        "credit_type": "HOMESTEAD",
    },
    "woodworking": {
        "subjects":    ["Engineering: Materials Science", "Math: Measurement & Geometry", "Art: Design"],
        "tracks":      [Track.HOMESTEADING, Track.APPLIED_MATHEMATICS, Track.CREATIVE_ECONOMY],
        "credit_type": "HOMESTEAD",
    },
    "sewing": {
        "subjects":    ["Math: Measurement & Geometry", "Art: Textile Design", "History: Cultural Studies"],
        "tracks":      [Track.APPLIED_MATHEMATICS, Track.CREATIVE_ECONOMY, Track.TRUTH_HISTORY],
        "credit_type": "CORE",
    },
    "coding": {
        "subjects":    ["Computer Science: Programming", "Math: Logic & Algorithms"],
        "tracks":      [Track.CREATIVE_ECONOMY, Track.APPLIED_MATHEMATICS],
        "credit_type": "CORE",
    },
    "reading": {
        "subjects":    ["Language Arts: Narrative Structure & Comprehension"],
        "tracks":      [Track.ENGLISH_LITERATURE],
        "credit_type": "CORE",
    },
    "writing": {
        "subjects":    ["Language Arts: Composition & Rhetoric"],
        "tracks":      [Track.ENGLISH_LITERATURE],
        "credit_type": "CORE",
    },
    "volunteering": {
        "subjects":    ["Civics: Community Service", "Social Studies: Community Organization"],
        "tracks":      [Track.GOVERNMENT_ECONOMICS, Track.JUSTICE_CHANGEMAKING],
        "credit_type": "CORE",
    },
    "animals": {
        "subjects":    ["Biology: Zoology & Animal Husbandry", "Ethics: Stewardship"],
        "tracks":      [Track.HOMESTEADING, Track.DISCIPLESHIP],
        "credit_type": "HOMESTEAD",
    },
    "soap_making": {
        "subjects":    ["Chemistry: Saponification", "Entrepreneurship: Product Development"],
        "tracks":      [Track.CREATION_SCIENCE, Track.CREATIVE_ECONOMY],
        "credit_type": "ELECTIVE",
    },
    "debate": {
        "subjects":    ["Language Arts: Rhetoric & Argumentation", "Civics: Democratic Participation"],
        "tracks":      [Track.ENGLISH_LITERATURE, Track.GOVERNMENT_ECONOMICS],
        "credit_type": "CORE",
    },
    "farming": {
        "subjects":    ["Biology: Soil & Crop Science", "Chemistry: Soil Amendments", "Math: Yield Estimation"],
        "tracks":      [Track.HOMESTEADING, Track.CREATION_SCIENCE, Track.APPLIED_MATHEMATICS],
        "credit_type": "HOMESTEAD",
    },
    "canning": {
        "subjects":    ["Chemistry: Preservation Science", "Health: Food Safety", "Math: Ratios"],
        "tracks":      [Track.HOMESTEADING, Track.HEALTH_NATUROPATHY, Track.APPLIED_MATHEMATICS],
        "credit_type": "HOMESTEAD",
    },
    "animal_care": {
        "subjects":    ["Biology: Veterinary Science", "Ethics: Animal Stewardship"],
        "tracks":      [Track.HOMESTEADING, Track.DISCIPLESHIP],
        "credit_type": "HOMESTEAD",
    },
    "drawing": {
        "subjects":    ["Art: Visual Design", "Math: Proportion & Geometry"],
        "tracks":      [Track.CREATIVE_ECONOMY, Track.APPLIED_MATHEMATICS],
        "credit_type": "ELECTIVE",
    },
    "music": {
        "subjects":    ["Music: Theory & Performance", "Math: Rhythm & Fractions"],
        "tracks":      [Track.CREATIVE_ECONOMY, Track.APPLIED_MATHEMATICS],
        "credit_type": "ELECTIVE",
    },
    "nature_study": {
        "subjects":    ["Biology: Field Naturalism", "Science: Observation & Classification"],
        "tracks":      [Track.CREATION_SCIENCE, Track.HOMESTEADING],
        "credit_type": "CORE",
    },
    "research": {
        "subjects":    ["Language Arts: Research Methods", "Civics: Information Literacy"],
        "tracks":      [Track.ENGLISH_LITERATURE, Track.TRUTH_HISTORY],
        "credit_type": "CORE",
    },
    "entrepreneurship": {
        "subjects":    ["Economics: Business Planning", "Math: Profit & Loss"],
        "tracks":      [Track.CREATIVE_ECONOMY, Track.GOVERNMENT_ECONOMICS],
        "credit_type": "CORE",
    },
    "health_wellness": {
        "subjects":    ["Health: Natural Medicine & Wellness", "Biology: Human Body Systems"],
        "tracks":      [Track.HEALTH_NATUROPATHY, Track.CREATION_SCIENCE],
        "credit_type": "ELECTIVE",
    },
    "field_trip": {
        "subjects":    ["Social Studies: Experiential Learning"],
        "tracks":      [Track.TRUTH_HISTORY, Track.GOVERNMENT_ECONOMICS],
        "credit_type": "CORE",
    },
}


# ── Credit hour calculation ────────────────────────────────────────────────────
#
# Carnegie unit: 120 hours = 1 credit.
# We use a homeschool-generous ratio: 20 hours of real activity = 1 credit hour.
# So 1 hour = 0.05 credit hours. Capped at 1.0 per single activity report.

HOURS_PER_CREDIT = 20.0


def _calc_credit_hours(time_minutes: int) -> float:
    hours = time_minutes / 60.0
    raw   = hours / HOURS_PER_CREDIT
    return round(min(raw, 1.0), 3)


# ── Claude mapping prompt ──────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Adeline's Registrar — a warm, precise academic credentialing engine for a
Christian homeschool family. Your job is to look at what a student did and map it to academic credit
categories from the life_to_credit table.

Available activity categories:
baking, cooking, gardening, building, woodworking, sewing, coding, reading, writing,
volunteering, animals, soap_making, debate, farming, canning, animal_care, drawing,
music, nature_study, research, entrepreneurship, health_wellness, field_trip

Available tracks:
CREATION_SCIENCE, HEALTH_NATUROPATHY, HOMESTEADING, GOVERNMENT_ECONOMICS,
JUSTICE_CHANGEMAKING, DISCIPLESHIP, TRUTH_HISTORY, ENGLISH_LITERATURE,
APPLIED_MATHEMATICS, CREATIVE_ECONOMY

Rules:
- Pick the 1–3 BEST activity categories that match what the student described.
- Write a course_title that sounds like a real academic course (e.g. "Applied Chemistry: Bread Fermentation"
  not just "Baking Bread").
- Write a short activity_description (1–2 sentences) that describes what was learned, not just what was done.
- If the activity doesn't fit any category well, pick the closest match and note it.
- Do NOT invent categories. Choose from the list.

Respond with JSON only:
{
  "categories": ["category1", "category2"],
  "course_title": "...",
  "activity_description": "...",
  "primary_track": "TRACK_NAME"
}"""


async def _map_activity_with_claude(description: str, grade_level: str) -> dict:
    """
    Use Claude to map a free-text activity description to academic credit categories.
    Falls back to a generic mapping if Claude is unavailable.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ADELINE_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot map activity")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    try:
        response = await client.messages.create(
            model=os.getenv("ADELINE_MODEL", "claude-sonnet-4-6"),
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Grade level: {grade_level}\n\n"
                        f"Student says: \"{description}\"\n\n"
                        "Map this to credit categories."
                    ),
                }
            ],
        )
        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"[activities] Claude returned non-JSON: {e}")
        raise HTTPException(status_code=500, detail="Credit mapping failed — invalid response from AI")
    except anthropic.APIError as e:
        logger.warning(f"[activities] Claude API error: {e}")
        raise HTTPException(status_code=503, detail=f"AI unavailable: {e}")


# ── Request / Response models ─────────────────────────────────────────────────

class ActivityReportRequest(BaseModel):
    student_id:   str
    grade_level:  str
    description:  str = Field(
        min_length=10,
        max_length=2000,
        description="What did you do? Be specific — include what you made, learned, or accomplished.",
    )
    time_minutes: int = Field(
        ge=5,
        le=1440,
        description="How many minutes did you spend on this activity?",
    )
    activity_date: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD). Defaults to today.",
    )


class CreditedTrack(BaseModel):
    track:       str
    subjects:    list[str]
    credit_type: str


class ActivityReportResponse(BaseModel):
    activity_id:         str
    course_title:        str
    activity_description: str
    credit_hours:        float
    credited_tracks:     list[CreditedTrack]
    sealed:              bool
    adeline_note:        str


class ActivityEntry(BaseModel):
    activity_id:         str
    course_title:        str
    activity_description: str
    credit_hours:        float
    primary_track:       str
    credit_type:         str
    activity_date:       str
    sealed_at:           str


class ActivityListResponse(BaseModel):
    student_id:    str
    activities:    list[ActivityEntry]
    total:         int
    total_credits: float


# ── POST /activities/report ───────────────────────────────────────────────────

@router.post("/report", response_model=ActivityReportResponse)
async def report_activity(
    body: ActivityReportRequest,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Student tells Adeline what they did. Adeline maps it to academic credit
    and seals a TranscriptEntry.

    No Witness Protocol — this is student-reported real-world activity.
    Adeline trusts it and records it.
    """
    logger.info(
        f"[/activities/report] student={body.student_id} "
        f"grade={body.grade_level} time={body.time_minutes}min"
    )

    # ── 1. Map activity to academic credit via Claude ──────────────────────────
    mapped = await _map_activity_with_claude(body.description, body.grade_level)

    categories    = mapped.get("categories", [])
    course_title  = mapped.get("course_title", "Independent Study")
    activity_desc = mapped.get("activity_description", body.description[:200])
    primary_track = mapped.get("primary_track", "DISCIPLESHIP")

    # Validate primary_track against enum
    try:
        Track(primary_track)
    except ValueError:
        primary_track = "DISCIPLESHIP"

    # ── 2. Build credited tracks list from category mapping ────────────────────
    seen_tracks: set[str] = set()
    credited_tracks: list[CreditedTrack] = []
    dominant_credit_type = "ELECTIVE"

    for cat in categories:
        cat_lower = cat.lower().replace(" ", "_")
        mapping   = LIFE_TO_CREDIT.get(cat_lower)
        if not mapping:
            continue
        for track in mapping["tracks"]:
            if track.value not in seen_tracks:
                seen_tracks.add(track.value)
                credited_tracks.append(CreditedTrack(
                    track=track.value,
                    subjects=mapping["subjects"],
                    credit_type=mapping["credit_type"],
                ))
                if mapping["credit_type"] == "CORE":
                    dominant_credit_type = "CORE"
                elif mapping["credit_type"] == "HOMESTEAD" and dominant_credit_type != "CORE":
                    dominant_credit_type = "HOMESTEAD"

    # If Claude returned no recognized categories, fall back to primary_track
    if not credited_tracks:
        credited_tracks.append(CreditedTrack(
            track=primary_track,
            subjects=["Independent Study"],
            credit_type="ELECTIVE",
        ))
        dominant_credit_type = "ELECTIVE"

    # ── 3. Calculate credit hours ──────────────────────────────────────────────
    credit_hours = _calc_credit_hours(body.time_minutes)

    # ── 4. Generate activity ID and date ──────────────────────────────────────
    activity_id   = f"activity-{uuid.uuid4()}"
    activity_date = body.activity_date or datetime.now(timezone.utc).date().isoformat()
    now_iso       = datetime.now(timezone.utc).isoformat()

    # ── 5. Seal to student_journal (makes it show on dashboard) ───────────────
    try:
        await journal_store.seal(
            student_id=body.student_id,
            lesson_id=activity_id,
            track=primary_track,
            completed_blocks=max(1, body.time_minutes // 30),
            sources=[],
        )
    except Exception as e:
        logger.warning(f"[activities] Journal seal failed (non-fatal): {e}")

    # ── 6. Seal TranscriptEntry for each credited track ────────────────────────
    transcript_entry_id = str(uuid.uuid4())

    try:
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
                    $1, $2, $3, $4, $5::"Track",
                    $6, $7,
                    $8, $9::"CreditType",
                    NULL, NULL,
                    $10, 'RegistrarAgent'::"AgentName", false,
                    $11::timestamp, $12::timestamp, NULL
                )
                ON CONFLICT ("studentId", "lessonId") DO UPDATE SET
                    "courseTitle"         = EXCLUDED."courseTitle",
                    "creditHours"         = EXCLUDED."creditHours",
                    "creditType"          = EXCLUDED."creditType",
                    "activityDescription" = EXCLUDED."activityDescription",
                    "sealedAt"            = EXCLUDED."sealedAt"
                """,
                transcript_entry_id,
                body.student_id,
                activity_id,
                course_title,
                primary_track,
                [],                      # oasStandards — none for life activities
                activity_desc,
                credit_hours,
                dominant_credit_type,
                dominant_credit_type == "HOMESTEAD",
                activity_date,
                now_iso,
            )
    except Exception as e:
        logger.exception("[activities] TranscriptEntry write failed")
        raise HTTPException(status_code=500, detail=f"Failed to seal activity: {e}")

    logger.info(
        f"[/activities/report] Sealed '{course_title}' — "
        f"{credit_hours} {dominant_credit_type} credits for student={body.student_id}"
    )

    # ── 7. Build Adeline's response note ──────────────────────────────────────
    time_display   = f"{body.time_minutes} minutes" if body.time_minutes < 60 else f"{body.time_minutes // 60} hour{'s' if body.time_minutes >= 120 else ''}"
    tracks_display = ", ".join(t.track.replace("_", " ").title() for t in credited_tracks[:2])
    adeline_note   = (
        f"{time_display} of real work. That goes on your transcript as {course_title}. "
        f"Credit filed under {tracks_display}."
    )

    return ActivityReportResponse(
        activity_id=activity_id,
        course_title=course_title,
        activity_description=activity_desc,
        credit_hours=credit_hours,
        credited_tracks=credited_tracks,
        sealed=True,
        adeline_note=adeline_note,
    )


# ── GET /activities/{student_id} ──────────────────────────────────────────────

@router.get("/{student_id}", response_model=ActivityListResponse)
async def list_activities(
    student_id: str,
    limit: int = Query(50, le=200),
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    List all activity-based transcript entries for a student.
    These are entries where lessonId starts with 'activity-'.
    """
    async with _get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT id, "lessonId", "courseTitle", track,
                   "creditHours", "creditType",
                   "activityDescription",
                   "completedAt", "sealedAt"
            FROM "TranscriptEntry"
            WHERE "studentId" = $1
              AND "lessonId" LIKE 'activity-%'
            ORDER BY "completedAt" DESC
            LIMIT $2
            """,
            student_id, limit,
        )

    entries = []
    for r in rows:
        entries.append(ActivityEntry(
            activity_id=str(r["lessonId"]),
            course_title=str(r["courseTitle"]),
            activity_description=str(r["activityDescription"] or ""),
            credit_hours=float(r["creditHours"] or 0),
            primary_track=str(r["track"]),
            credit_type=str(r["creditType"]),
            activity_date=r["completedAt"].isoformat() if r["completedAt"] else "",
            sealed_at=r["sealedAt"].isoformat() if r["sealedAt"] else "",
        ))

    total_credits = sum(e.credit_hours for e in entries)

    return ActivityListResponse(
        student_id=student_id,
        activities=entries,
        total=len(entries),
        total_credits=round(total_credits, 3),
    )
