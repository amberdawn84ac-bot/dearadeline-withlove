"""
Journal API — /journal/*

POST /journal/seal      — Seal a completed lesson into the student's journal
GET  /journal/progress/{student_id} — Fetch track progress counts
"""
import asyncio
import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any

from app.schemas.api_models import Track
from app.api.middleware import get_current_user_id, verify_student_access
from app.connections.journal_store import journal_store
from app.connections.curriculum_graph import curriculum_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/journal", tags=["journal"])


# ── Request / Response models ─────────────────────────────────────────────

class SealRequest(BaseModel):
    lesson_id:        str
    track:            Track
    completed_blocks: int = Field(default=0, ge=0)
    oas_standards:    list[dict[str, Any]] = Field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)
    # Optional adaptive learning signals — sent by UI after lesson/quiz completion
    concept_id:   str | None = None   # ZPD concept_id if known
    concept_name: str | None = None   # Human-readable concept title
    quiz_results: list[dict[str, Any]] = Field(default_factory=list)  # [{correct: bool}, ...]
    learner_reflection: str | None = Field(default=None, max_length=4000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=20)
    parent_attested: bool = False
    credit_draft: dict[str, Any] | None = None


class SealResponse(BaseModel):
    sealed:         bool
    lesson_id:      str
    track:          Track
    track_progress: dict[str, int]
    learning_status: str
    credit_sealed: bool = False


class ProgressResponse(BaseModel):
    student_id:     str
    track_progress: dict[str, int]

class RecentEntry(BaseModel):
    lesson_id:        str
    track:            str
    completed_blocks: int
    sealed_at:        str | None

class RecentResponse(BaseModel):
    student_id: str
    entries:    list[RecentEntry]


# ── Routes ───────────────────────────────────────────────

@router.post("/seal", response_model=SealResponse)
async def seal_journal(
    body: SealRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Seal a lesson into the student's journal.

    - Upserts (student_id, lesson_id) into student_journal
    - Returns updated track_progress so the UI can refresh the dashboard
    """
    logger.info(
        f"[/journal/seal] student={student_id} "
        f"lesson={body.lesson_id} track={body.track.value} "
        f"blocks={body.completed_blocks}"
    )
    reflection = (body.learner_reflection or "").strip()
    if not reflection and not body.quiz_results and not body.artifact_refs and not body.parent_attested:
        raise HTTPException(
            status_code=422,
            detail="Save a reflection, scored demonstration, artifact, or parent observation before recording this experience.",
        )

    proficiency = _evidence_proficiency(body)
    demonstrated = proficiency in {"UNDERSTANDING", "EXTENDING"}

    try:
        track_progress = await journal_store.seal(
            student_id=student_id,
            lesson_id=body.lesson_id,
            track=body.track.value,
            completed_blocks=body.completed_blocks,
            sources=(body.evidence_sources + [
                {"type": "learner_reflection", "content": reflection},
                *({"type": "artifact", "url": ref} for ref in body.artifact_refs),
            ]) or None,
        )
    except Exception as e:
        logger.exception("[/journal/seal] DB error")
        raise HTTPException(status_code=500, detail=str(e))

    # Invalidate student state cache so next lesson sees fresh mastery scores
    from app.models.student import invalidate_student_state_cache
    await invalidate_student_state_cache(student_id)

    # Record standards mastery in the same Postgres transaction system.
    if body.oas_standards:
        # Await this write so the parent Learning Map is correct immediately
        # after the learner saves the experience.
        await _record_mastery_safe(
            student_id, body.track.value, body.oas_standards, proficiency,
        )

    # Fire-and-forget BKT + SM-2 card update with quiz-derived quality signal
    asyncio.create_task(
        _update_card_safe(student_id, body)
    )

    # A generated lesson carries only proposed credit. Sealing is the learner's
    # completion signal, so this is the one place that turns it into transcript
    # credit. Never trust the student id embedded in the client payload.
    credit_sealed = False
    if body.credit_draft and demonstrated:
        try:
            from app.api.learning_records import _seal_transcript_db, TranscriptEntryIn
            credit = body.credit_draft
            await _seal_transcript_db(TranscriptEntryIn(
                id=credit.get("id") or str(uuid.uuid4()),
                student_id=student_id,
                lesson_id=body.lesson_id,
                course_title=credit.get("course_title") or body.lesson_id,
                track=body.track.value,
                oas_standards=credit.get("oas_standards", []),
                activity_description=credit.get("activity_description", "Completed and sealed lesson"),
                credit_hours=max(0.0, min(float(credit.get("credit_hours", 0)), 1.0)),
                credit_type=credit.get("credit_type", "ELECTIVE"),
                is_homestead_credit=bool(credit.get("is_homestead_credit", False)),
                agent_name=credit.get("agent_name"),
                researcher_activated=bool(credit.get("researcher_activated", False)),
            ))
            credit_sealed = True
        except Exception as exc:
            logger.exception("[/journal/seal] Transcript credit seal failed")
            raise HTTPException(status_code=500, detail=f"Journal saved but transcript credit failed: {exc}")

    # Completion changes both mastery coverage and the next-best experience.
    # Invalidate the whole adaptive plan even when the lesson earns no credit.
    try:
        from app.api.learning_plan import pop_completed_lesson
        await pop_completed_lesson(student_id, body.lesson_id)
    except Exception as exc:
        logger.warning("Learning plan invalidation failed after journal seal: %s", exc)

    return SealResponse(
        sealed=True,
        lesson_id=body.lesson_id,
        track=body.track,
        track_progress=track_progress,
        learning_status=proficiency,
        credit_sealed=credit_sealed,
    )


async def _record_mastery_safe(
    student_id: str, track: str, oas_standards: list[dict], proficiency: str,
) -> None:
    try:
        await curriculum_graph.record_standard_mastery(
            student_id, track, oas_standards, proficiency=proficiency,
        )
        logger.info(
            "[CurriculumGraph] %s recorded for %s — %s standards",
            proficiency, student_id, len(oas_standards),
        )
    except Exception as exc:
        logger.warning(f"[CurriculumGraph] Mastery write failed (non-fatal): {exc}")


def _quiz_quality(quiz_results: list[dict]) -> int:
    """Map quiz results to SM-2 quality (0–5). Defaults to 3 (lesson-only experience)."""
    if not quiz_results:
        return 3
    correct = sum(1 for q in quiz_results if q.get("correct"))
    ratio = correct / len(quiz_results)
    if ratio >= 0.9:
        return 5
    if ratio >= 0.75:
        return 4
    if ratio >= 0.5:
        return 3
    if ratio >= 0.25:
        return 2
    return 1


def _evidence_proficiency(body: SealRequest) -> str:
    """Translate reviewable evidence into a conservative learning status."""
    if body.quiz_results:
        correct = sum(1 for result in body.quiz_results if result.get("correct"))
        ratio = correct / len(body.quiz_results)
        if ratio >= 0.9 and (body.artifact_refs or body.parent_attested):
            return "EXTENDING"
        if ratio >= 0.75:
            return "UNDERSTANDING"
        if ratio >= 0.5:
            return "APPROACHING"
        return "DEVELOPING"
    if body.parent_attested and body.artifact_refs:
        return "UNDERSTANDING"
    if body.artifact_refs:
        return "APPROACHING"
    return "DEVELOPING"


async def _update_card_safe(student_id: str, body: SealRequest) -> None:
    """Fire-and-forget: update BKT pL + SM-2 schedule after lesson seal."""
    try:
        from app.algorithms.bkt_tracker import update_card_after_lesson
        from app.tools.graph_query import tool_get_zpd_candidates

        quality = _quiz_quality(body.quiz_results)

        concept_id   = body.concept_id
        concept_name = body.concept_name or ""

        # If no concept_id was sent, resolve from ZPD candidates
        if not concept_id:
            zpd = await tool_get_zpd_candidates(student_id, body.track.value, limit=1)
            if zpd:
                concept_id   = zpd[0].concept_id
                concept_name = concept_name or zpd[0].title
            else:
                concept_id = f"{body.track.value.lower()}-seal"

        await update_card_after_lesson(
            student_id=student_id,
            concept_id=concept_id,
            concept_name=concept_name,
            track=body.track.value,
            quality=quality,
        )
    except Exception as exc:
        logger.warning(f"[Journal] BKT/SM-2 update failed (non-fatal): {exc}")


@router.get("/progress/{student_id}", response_model=ProgressResponse)
async def get_progress(
    student_id: str,
    _user_id: str = Depends(verify_student_access),
):
    """Return all track progress counts for a student."""
    try:
        track_progress = await journal_store.get_track_progress(student_id)
    except Exception as e:
        logger.exception("[/journal/progress] DB error")
        raise HTTPException(status_code=500, detail=str(e))

    return ProgressResponse(student_id=student_id, track_progress=track_progress)


@router.get("/recent/{student_id}", response_model=RecentResponse)
async def get_recent(
    student_id: str,
    limit: int = 10,
    _user_id: str = Depends(verify_student_access),
):
    """Return the most recently sealed lessons for a student."""
    try:
        entries = await journal_store.get_recent(student_id, limit=min(limit, 50))
    except Exception as e:
        logger.exception("[/journal/recent] DB error")
        raise HTTPException(status_code=500, detail=str(e))

    return RecentResponse(
        student_id=student_id,
        entries=[RecentEntry(**e) for e in entries],
    )
