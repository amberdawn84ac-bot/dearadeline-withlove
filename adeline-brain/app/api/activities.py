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


# Credit is competency-based. Optional time is retained only as family metadata
# and never participates in mastery or credit calculations.


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
        description="Optional family metadata. Never used to calculate mastery or credit.",
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
    learning_status:     str = "NOT_YET_DEMONSTRATED"
    concepts_demonstrated: list[str] = Field(default_factory=list)
    standards_mastered:  list[str] = Field(default_factory=list)
    mastery_question:    Optional[str] = None


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
    concepts_demonstrated: list[str],
    mastery_question: Optional[str],
) -> str:
    """Lead with demonstrated learning instead of clock time."""
    learning_subjects = list(dict.fromkeys(
        subject
        for credited_track in credited_tracks
        for subject in credited_track.subjects
    ))
    subjects_display = "; ".join(learning_subjects[:4]) or "Independent Study"
    if concepts_demonstrated:
        concepts = "; ".join(concepts_demonstrated[:4])
        return f"That demonstrates real learning in {subjects_display}: {concepts}."
    return (
        f"That activity connects to {subjects_display}, but doing it alone does not prove what you understand. "
        + (mastery_question or "What did you notice, figure out, change, or learn while doing it?")
    )


def _grade_number(grade_level: str) -> int:
    if str(grade_level).upper().startswith("K"):
        return 0
    try:
        return max(0, min(12, int(str(grade_level).split("-")[0])))
    except (TypeError, ValueError):
        return 0


async def _evaluate_concept_mastery(
    description: str,
    grade_level: str,
    candidate_standards: list[dict],
) -> dict:
    """Match only explicitly demonstrated knowledge to required concepts."""
    if not candidate_standards or (not GOOGLE_API_KEY and not os.getenv("GEMINI_API_KEY")):
        return {
            "learning_status": "NOT_YET_DEMONSTRATED",
            "concepts_demonstrated": [],
            "standard_codes": [],
            "mastery_question": "What did you figure out, and how do you know it worked?",
        }
    standards = [
        {
            "code": row.get("id") or row.get("code"),
            "description": row.get("description"),
            "subject": row.get("subject"),
            "track": row.get("track"),
        }
        for row in candidate_standards[:160]
    ]
    prompt = f"""Grade: {grade_level}
Learner's own report: {description}
Required grade-level concepts: {json.dumps(standards, ensure_ascii=False)}

Judge only knowledge or skill explicitly demonstrated in the learner's words. Merely naming,
doing, attending, completing, or spending time on an activity is not mastery. Do not infer an
explanation the learner did not give. Match at most five standards and only when the report is
clear evidence of the standard. Return JSON only:
{{"learning_status":"NOT_YET_DEMONSTRATED|APPROACHING|UNDERSTANDING|EXTENDING",
"concepts_demonstrated":["plain-language concept"],"standard_codes":["exact code"],
"mastery_question":"one natural question that would let the learner demonstrate the most relevant missing concept, or null"}}"""
    llm = create_llm(model=GEMINI_MODEL, max_tokens=700)
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are Adeline's competency evaluator. Credit mastery, never attendance or time. Be conservative and return strict JSON."),
            HumanMessage(content=prompt),
        ])
        text = str(response.content).strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(text)
        allowed = {str(item["code"]) for item in standards if item.get("code")}
        codes = [str(code) for code in result.get("standard_codes", []) if str(code) in allowed]
        status = str(result.get("learning_status") or "NOT_YET_DEMONSTRATED")
        if status not in {"NOT_YET_DEMONSTRATED", "APPROACHING", "UNDERSTANDING", "EXTENDING"}:
            status = "NOT_YET_DEMONSTRATED"
        if status in {"UNDERSTANDING", "EXTENDING"} and not codes:
            status = "APPROACHING"
        return {
            "learning_status": status,
            "concepts_demonstrated": [str(x) for x in result.get("concepts_demonstrated", [])][:5],
            "standard_codes": codes,
            "mastery_question": result.get("mastery_question"),
        }
    except Exception as exc:
        logger.warning("[activities] mastery evaluation unavailable: %s", exc)
        return {
            "learning_status": "NOT_YET_DEMONSTRATED",
            "concepts_demonstrated": [],
            "standard_codes": [],
            "mastery_question": "What did you figure out, and what evidence showed you were right?",
        }


def _competency_credit(mastered_codes: list[str], candidate_standards: list[dict]) -> float:
    """Give each mastered requirement its proportional share of a subject credit."""
    if not mastered_codes:
        return 0.0
    subject_by_code = {
        str(row.get("id") or row.get("code")): str(row.get("subject") or "General")
        for row in candidate_standards
    }
    counts: dict[str, int] = {}
    for subject in subject_by_code.values():
        counts[subject] = counts.get(subject, 0) + 1
    value = sum(1.0 / max(1, counts.get(subject_by_code.get(code, "General"), 1)) for code in set(mastered_codes))
    return round(min(value, 1.0), 3)


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

    # ── 3. Match explicit understanding to unmastered grade-level requirements ─
    from app.connections.curriculum_graph import curriculum_graph
    try:
        grade_standards = await curriculum_graph.get_grade_standards(
            student_id, _grade_number(body.grade_level), limit=500, per_subject_limit=None,
        )
    except Exception as exc:
        logger.warning("[activities] grade standards unavailable: %s", exc)
        grade_standards = []
    relevant_tracks = seen_tracks or {primary_track}
    relevant_standards = [
        row for row in grade_standards
        if str(row.get("track")) in relevant_tracks
    ]
    candidates = [row for row in relevant_standards if not bool(row.get("mastered"))]
    evaluation = await _evaluate_concept_mastery(body.description, body.grade_level, candidates)
    learning_status = evaluation["learning_status"]
    mastered_codes = evaluation["standard_codes"] if learning_status in {"UNDERSTANDING", "EXTENDING"} else []
    credit_hours = _competency_credit(mastered_codes, relevant_standards)

    # ── 4. Generate activity ID and date ──────────────────────────────────────
    activity_id   = f"activity-{uuid.uuid4()}"
    activity_date = body.activity_date or datetime.now(timezone.utc).date()
    sealed_at     = datetime.now(timezone.utc)

    # ── 5. Record only demonstrated concepts as mastery and transcript credit ─
    sealed = False
    if mastered_codes:
        matched_standards = [
            {
                "standard_id": str(row.get("id")),
                "text": str(row.get("description") or ""),
                "grade": int(row.get("grade") or _grade_number(body.grade_level)),
                "subject": str(row.get("subject") or "General"),
                "source_type": "everyday_activity",
            }
            for row in candidates if str(row.get("id")) in mastered_codes
        ]
        try:
            await curriculum_graph.record_standard_mastery(
                student_id, primary_track, matched_standards, proficiency=learning_status,
            )
            await journal_store.seal(
                student_id=student_id,
                lesson_id=activity_id,
                track=primary_track,
                completed_blocks=max(1, len(mastered_codes)),
                sources=[{
                    "type": "everyday_learning",
                    "content": body.description,
                    "concepts": evaluation["concepts_demonstrated"],
                    "standard_codes": mastered_codes,
                    "time_minutes": body.time_minutes,  # metadata only
                }],
            )
            sealed = await _seal_activity_transcript(
                transcript_entry_id=str(uuid.uuid4()),
                student_id=student_id,
                activity_id=activity_id,
                course_title=course_title,
                primary_track=primary_track,
                oas_standards=mastered_codes,
                activity_description=activity_desc,
                credit_hours=credit_hours,
                credit_type=dominant_credit_type,
                is_homestead_credit=dominant_credit_type == "HOMESTEAD",
                completed_at=activity_date,
                sealed_at=sealed_at,
                percent_score=95.0 if learning_status == "EXTENDING" else 85.0,
            )
            from app.models.student import invalidate_student_state_cache
            await invalidate_student_state_cache(student_id)
            try:
                from app.api.learning_plan import pop_completed_lesson
                await pop_completed_lesson(student_id, course_title)
            except Exception as plan_exc:
                logger.warning("[activities] learning-plan refresh failed: %s", plan_exc)
        except Exception as exc:
            logger.exception("[activities] competency record failed: %s", exc)

    logger.info(
        "[/activities/report] %s — status=%s standards=%s competency_credit=%s student=%s",
        course_title, learning_status, mastered_codes, credit_hours, student_id,
    )

    # ── 7. Build Adeline's response note ──────────────────────────────────────
    adeline_note = _build_learning_note(
        activity_desc, credited_tracks, evaluation["concepts_demonstrated"], evaluation.get("mastery_question"),
    )

    return ActivityReportResponse(
        activity_id=activity_id,
        course_title=course_title,
        activity_description=activity_desc,
        credit_hours=credit_hours,
        credited_tracks=credited_tracks,
        sealed=sealed,
        adeline_note=adeline_note,
        evidence_urls=[],
        learning_status=learning_status,
        concepts_demonstrated=evaluation["concepts_demonstrated"],
        standards_mastered=mastered_codes,
        mastery_question=evaluation.get("mastery_question"),
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
