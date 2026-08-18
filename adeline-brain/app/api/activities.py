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
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.config import create_llm, GOOGLE_API_KEY, GEMINI_MODEL
from app.schemas.api_models import Track
from app.api.middleware import get_current_user_id, verify_student_access
from app.connections.journal_store import journal_store
from app.services.storage import upload_mastery_evidence
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


# ── Gemini mapping prompt ──────────────────────────────────────────────────────

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


_LOCAL_ACTIVITY_HINTS: dict[str, tuple[str, ...]] = {
    "baking": ("bake", "baked", "bread", "dough", "yeast", "sourdough"),
    "cooking": ("cook", "cooked", "meal", "recipe", "kitchen"),
    "gardening": ("garden", "planted", "seed", "soil", "harvest"),
    "building": ("build", "built", "construct", "repair", "fixed"),
    "woodworking": ("woodwork", "lumber", "saw", "carpentry"),
    "sewing": ("sew", "sewed", "stitched", "fabric"),
    "coding": ("code", "coded", "program", "software", "app"),
    "reading": ("read", "book", "chapter"),
    "writing": ("write", "wrote", "essay", "story", "poem"),
    "volunteering": ("volunteer", "helped", "community service"),
    "animal_care": ("fed the", "cared for", "animal", "livestock", "chicken"),
    "drawing": ("draw", "drew", "paint", "sketch"),
    "music": ("music", "guitar", "piano", "sang", "practiced"),
    "research": ("research", "investigated", "looked up", "compared sources"),
    "entrepreneurship": ("sold", "business", "customer", "profit", "budget"),
}


def _map_activity_locally(description: str, *, allow_generic: bool = False) -> Optional[dict]:
    """Map common life activities without making learning recognition depend on an LLM."""
    normalized = description.lower()
    categories = [
        category
        for category, hints in _LOCAL_ACTIVITY_HINTS.items()
        if any(hint in normalized for hint in hints)
    ][:3]
    if not categories and not allow_generic:
        return None

    if "baking" in categories:
        return {
            "categories": categories,
            "course_title": "Applied Chemistry: Bread Fermentation",
            "activity_description": (
                "Measured ingredients, observed fermentation and dough development, "
                "and used heat to transform dough into bread."
            ),
            "primary_track": "CREATION_SCIENCE",
        }

    primary = categories[0] if categories else None
    mapping = LIFE_TO_CREDIT.get(primary or "", {})
    tracks = mapping.get("tracks") or [Track.DISCIPLESHIP]
    subject = (mapping.get("subjects") or ["Independent Study"])[0]
    return {
        "categories": categories,
        "course_title": subject,
        "activity_description": (
            "Documented a real-world activity and reflected on the observations, "
            "decisions, skills, and possible next questions it produced."
        ),
        "primary_track": tracks[0].value,
    }


async def _map_activity_with_gemini(description: str, grade_level: str) -> dict:
    """
    Use the active LLM to map a free-text activity description to academic credit categories.
    Falls back to a generic mapping if no LLM key is available.
    """
    local_match = _map_activity_locally(description)
    if local_match:
        return local_match

    if not GOOGLE_API_KEY and not os.getenv("GEMINI_API_KEY"):
        return _map_activity_locally(description, allow_generic=True) or {}

    llm = create_llm(model=GEMINI_MODEL, max_tokens=512)
    lc_messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Grade level: {grade_level}\n\n"
            f"Student says: \"{description}\"\n\n"
            "Map this to credit categories."
        )),
    ]

    try:
        response = await llm.ainvoke(lc_messages)
        text = response.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"[activities] Gemini returned non-JSON; using local mapping: {e}")
    except Exception as e:
        logger.warning(f"[activities] Gemini unavailable; using local mapping: {e}")
    return _map_activity_locally(description, allow_generic=True) or {}


# ── Request / Response models ─────────────────────────────────────────────────

class ActivityReportRequest(BaseModel):
    student_id:   str
    grade_level:  str
    description:  str = Field(
        min_length=10,
        max_length=2000,
        description="What did you do? Be specific — include what you made, learned, or accomplished.",
    )
    time_minutes: Optional[int] = Field(
        default=None,
        ge=5,
        le=1440,
        description="Optional time spent, used only for clock-hour accounting.",
    )
    activity_date: Optional[date] = Field(
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
    evidence_urls:       list[str] = Field(default_factory=list)


class BreadLessonCompletionRequest(BaseModel):
    grade_level: str
    answers: dict[str, str]
    observations: str = Field(min_length=15, max_length=1200)
    next_test: str = Field(min_length=10, max_length=800)


class BreadLessonCompletionResponse(ActivityReportResponse):
    score_percent: float
    concepts_demonstrated: list[str]
    oas_standards: list[str]


class ActivityEntry(BaseModel):
    activity_id:         str
    course_title:        str
    activity_description: str
    credit_hours:        float
    primary_track:       str
    credit_type:         str
    activity_date:       str
    sealed_at:           str
    evidence_urls:       list[str] = Field(default_factory=list)


class ActivityListResponse(BaseModel):
    student_id:    str
    activities:    list[ActivityEntry]
    total:         int
    total_credits: float


def _build_learning_note(
    activity_description: str,
    credited_tracks: list[CreditedTrack],
) -> str:
    """Lead with demonstrated learning instead of clock time."""
    learning_subjects = list(dict.fromkeys(
        subject
        for credited_track in credited_tracks
        for subject in credited_track.subjects
    ))
    subjects_display = "; ".join(learning_subjects[:4]) or "Independent Study"
    return (
        f"That is real learning. {activity_description.rstrip('.')}—and it connects to "
        f"{subjects_display}. What did you notice, figure out, or change while doing it, "
        "and what would you try next time?"
    )


_BREAD_REVIEW_ANSWER_KEY = {
    "yeast": "living_fungus",
    "gas": "carbon_dioxide",
    "gluten": "traps_gas",
    "temperature": "warm_speeds_yeast",
    "oven": "sets_structure_and_browns",
    "ratio": "proportional_scaling",
}


def _score_bread_review(answers: dict[str, str]) -> tuple[int, int]:
    """Return correct and total counts for the fixed, server-verified review."""
    correct = sum(
        answers.get(question_id) == expected
        for question_id, expected in _BREAD_REVIEW_ANSWER_KEY.items()
    )
    return correct, len(_BREAD_REVIEW_ANSWER_KEY)


def _bread_standards_for_grade(grade_level: str) -> list[str]:
    """Select a small, age-appropriate OAS alignment for one shared family lab."""
    digits = "".join(character for character in grade_level if character.isdigit())
    grade = int(digits) if digits else 8
    if grade <= 3:
        return ["SCIENC_G3_CCC.3.3-5.3"]
    if grade <= 5:
        return ["SCIENC_G5_5.PS1.2", "MATHEM_G4_4.GM.2.7"]
    if grade <= 8:
        return ["SCIENC_G7_7.PS1.2", "SCIENC_G6_6.PS1.4", "MATHEM_G6_6.N.3.3"]
    return ["SCIENC_G9_B.LS2.3", "SCIENC_G9_CCC.5.9-12.3"]


async def _seal_activity_transcript(
    *,
    transcript_entry_id: str,
    student_id: str,
    activity_id: str,
    course_title: str,
    primary_track: str,
    oas_standards: list[str],
    activity_description: str,
    credit_hours: float,
    credit_type: str,
    is_homestead_credit: bool,
    completed_at: date,
    sealed_at: datetime,
    percent_score: Optional[float] = None,
) -> bool:
    """Write a portfolio/transcript record with asyncpg-native date values."""
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
                    NULL, $10,
                    $11, 'RegistrarAgent'::"AgentName", false,
                    $12::date, $13::timestamptz, NULL
                )
                ON CONFLICT ("studentId", "lessonId") DO UPDATE SET
                    "courseTitle"         = EXCLUDED."courseTitle",
                    "oasStandards"        = EXCLUDED."oasStandards",
                    "creditHours"         = EXCLUDED."creditHours",
                    "creditType"          = EXCLUDED."creditType",
                    "percentScore"        = EXCLUDED."percentScore",
                    "activityDescription" = EXCLUDED."activityDescription",
                    "sealedAt"            = EXCLUDED."sealedAt"
                """,
                transcript_entry_id,
                student_id,
                activity_id,
                course_title,
                primary_track,
                oas_standards,
                activity_description,
                credit_hours,
                credit_type,
                percent_score,
                is_homestead_credit,
                completed_at,
                sealed_at,
            )
        return True
    except Exception:
        logger.exception("[activities] TranscriptEntry write failed; returning learning reflection")
        return False


# ── POST /activities/report ───────────────────────────────────────────────────

@router.post("/report", response_model=ActivityReportResponse)
async def report_activity(
    body: ActivityReportRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Student tells Adeline what they did. Adeline maps it to academic credit
    and seals a TranscriptEntry.

    No Witness Protocol — this is student-reported real-world activity.
    Adeline trusts it and records it.
    """
    logger.info(
        f"[/activities/report] student={student_id} "
        f"grade={body.grade_level} time={body.time_minutes or 'unspecified'}min"
    )

    # ── 1. Map the activity's learning value via Gemini ────────────────────────
    mapped = await _map_activity_with_gemini(body.description, body.grade_level)

    categories    = mapped.get("categories", [])
    course_title  = mapped.get("course_title", "Independent Study")
    activity_desc = mapped.get("activity_description", body.description[:200])
    primary_track = mapped.get("primary_track", "DISCIPLESHIP")

    # Validate primary_track against enum
    sealed = True
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

    # If the mapper returned no recognized categories, fall back to primary_track.
    if not credited_tracks:
        credited_tracks.append(CreditedTrack(
            track=primary_track,
            subjects=["Independent Study"],
            credit_type="ELECTIVE",
        ))
        dominant_credit_type = "ELECTIVE"

    # ── 3. Calculate optional clock-hour credit ────────────────────────────────
    # Learning evidence is still recorded when the student did not provide time.
    credit_hours = _calc_credit_hours(body.time_minutes or 0)

    # ── 4. Generate activity ID and date ──────────────────────────────────────
    activity_id   = f"activity-{uuid.uuid4()}"
    activity_date = body.activity_date or datetime.now(timezone.utc).date()
    sealed_at     = datetime.now(timezone.utc)

    # ── 5. Seal to student_journal (makes it show on dashboard) ───────────────
    try:
        await journal_store.seal(
            student_id=student_id,
            lesson_id=activity_id,
            track=primary_track,
            completed_blocks=max(1, (body.time_minutes or 0) // 30),
            sources=[],
        )
    except Exception as e:
        logger.warning(f"[activities] Journal seal failed (non-fatal): {e}")

    # ── 6. Seal TranscriptEntry for each credited track ────────────────────────
    transcript_entry_id = str(uuid.uuid4())

    sealed = await _seal_activity_transcript(
        transcript_entry_id=transcript_entry_id,
        student_id=student_id,
        activity_id=activity_id,
        course_title=course_title,
        primary_track=primary_track,
        oas_standards=[],
        activity_description=activity_desc,
        credit_hours=credit_hours,
        credit_type=dominant_credit_type,
        is_homestead_credit=dominant_credit_type == "HOMESTEAD",
        completed_at=activity_date,
        sealed_at=sealed_at,
    )

    logger.info(
        f"[/activities/report] Sealed '{course_title}' — "
        f"{credit_hours} {dominant_credit_type} credits for student={student_id}"
    )

    # ── 7. Build Adeline's response note ──────────────────────────────────────
    adeline_note = _build_learning_note(activity_desc, credited_tracks)

    return ActivityReportResponse(
        activity_id=activity_id,
        course_title=course_title,
        activity_description=activity_desc,
        credit_hours=credit_hours,
        credited_tracks=credited_tracks,
        sealed=sealed,
        adeline_note=adeline_note,
        evidence_urls=[],
    )


@router.post(
    "/kitchen-chemistry-bread/complete",
    response_model=BreadLessonCompletionResponse,
)
async def complete_kitchen_chemistry_bread(
    body: BreadLessonCompletionRequest,
    student_id: str = Depends(get_current_user_id),
):
    """Verify the bread review, then create its registrar and portfolio record."""
    correct, total = _score_bread_review(body.answers)
    score_percent = round((correct / total) * 100, 1)
    if correct < 5:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Review the bread concepts and try again before sealing the portfolio entry.",
                "correct": correct,
                "total": total,
            },
        )

    completed_at = datetime.now(timezone.utc).date()
    sealed_at = datetime.now(timezone.utc)
    activity_id = f"activity-kitchen-chemistry-bread-{completed_at.isoformat()}"
    oas_standards = _bread_standards_for_grade(body.grade_level)
    concepts = [
        "Yeast is a living fungus that carries out fermentation.",
        "Fermentation releases carbon dioxide that inflates the dough.",
        "Gluten forms a stretchy network that traps gas.",
        "Temperature changes yeast activity and proofing rate.",
        "Ingredient ratios can be scaled proportionally.",
        "Oven heat sets structure and browns the crust.",
    ]
    activity_description = (
        "Completed a family kitchen-chemistry investigation of bread fermentation, "
        "ingredient ratios, carbon-dioxide production, gluten structure, temperature, "
        f"and oven transformations. Observation: {body.observations.strip()} "
        f"Next investigation: {body.next_test.strip()}"
    )
    credited_tracks = [
        CreditedTrack(
            track="CREATION_SCIENCE",
            subjects=[
                "Chemistry: Fermentation & Gas Production",
                "Physical Science: Matter, Heat & Structural Change",
            ],
            credit_type="CORE",
        ),
        CreditedTrack(
            track="APPLIED_MATHEMATICS",
            subjects=["Math: Ratios, Measurement & Proportional Scaling"],
            credit_type="CORE",
        ),
    ]

    try:
        await journal_store.seal(
            student_id=student_id,
            lesson_id=activity_id,
            track="CREATION_SCIENCE",
            completed_blocks=1,
            sources=[],
        )
    except Exception as error:
        logger.warning(f"[bread-lesson] Journal seal failed (non-fatal): {error}")

    sealed = await _seal_activity_transcript(
        transcript_entry_id=str(uuid.uuid4()),
        student_id=student_id,
        activity_id=activity_id,
        course_title="Kitchen Chemistry: Bread",
        primary_track="CREATION_SCIENCE",
        oas_standards=oas_standards,
        activity_description=activity_description,
        credit_hours=0.05,
        credit_type="CORE",
        is_homestead_credit=False,
        completed_at=completed_at,
        sealed_at=sealed_at,
        percent_score=score_percent,
    )

    return BreadLessonCompletionResponse(
        activity_id=activity_id,
        course_title="Kitchen Chemistry: Bread",
        activity_description=activity_description,
        credit_hours=0.05,
        credited_tracks=credited_tracks,
        sealed=sealed,
        adeline_note=(
            "You explained the chemistry instead of merely finishing a recipe. "
            "Your fermentation, structure, heat, and ratio evidence is ready for the portfolio."
        ),
        evidence_urls=[],
        score_percent=score_percent,
        concepts_demonstrated=concepts,
        oas_standards=oas_standards,
    )


@router.post("/{activity_id}/evidence")
async def upload_activity_evidence(
    activity_id: str,
    description: str = Form(""),
    file: UploadFile = File(...),
    student_id: str = Depends(get_current_user_id),
):
    """Attach authenticated photo/video evidence to a credited life activity."""
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/gif", "video/mp4", "video/webm", "video/quicktime"}
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail="Use a JPG, PNG, GIF, MP4, WebM, or MOV file")

    async with _get_conn() as conn:
        owns_activity = await conn.fetchval(
            'SELECT EXISTS(SELECT 1 FROM "TranscriptEntry" WHERE "studentId"=$1 AND "lessonId"=$2)',
            student_id, activity_id,
        )
        if not owns_activity:
            raise HTTPException(status_code=404, detail="Activity not found")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (50MB maximum)")

    file_url = await upload_mastery_evidence(
        student_id=student_id,
        standard_id=activity_id,
        file_bytes=file_bytes,
        content_type=content_type,
        original_filename=file.filename,
    )

    evidence_id = str(uuid.uuid4())
    async with _get_conn() as conn:
        await conn.execute(
            'INSERT INTO "ActivityEvidence" (id, "studentId", "activityId", "fileUrl", "contentType", description) VALUES ($1,$2,$3,$4,$5,$6)',
            evidence_id, student_id, activity_id, file_url, content_type, description or file.filename or "Project evidence",
        )
    return {"evidence_id": evidence_id, "activity_id": activity_id, "file_url": file_url}


# ── GET /activities/{student_id} ──────────────────────────────────────────────

@router.get("/{student_id}", response_model=ActivityListResponse)
async def list_activities(
    student_id: str,
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_student_access),
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
                   "completedAt", "sealedAt",
                   COALESCE((SELECT array_agg(e."fileUrl" ORDER BY e."createdAt")
                     FROM "ActivityEvidence" e WHERE e."activityId" = "TranscriptEntry"."lessonId"), ARRAY[]::text[]) AS "evidenceUrls"
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
            evidence_urls=list(r["evidenceUrls"] or []),
        ))

    total_credits = sum(e.credit_hours for e in entries)

    return ActivityListResponse(
        student_id=student_id,
        activities=entries,
        total=len(entries),
        total_credits=round(total_credits, 3),
    )
