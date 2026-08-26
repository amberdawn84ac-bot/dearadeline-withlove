"""
Journal API — /journal/*

POST /journal/seal      — Seal a completed lesson into the student's journal
GET  /journal/progress/{student_id} — Fetch track progress counts
"""
import asyncio
import json
import logging
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
    plan_item_id:     str | None = None
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

class PortfolioItem(BaseModel):
    lesson_id: str
    title: str
    track: str
    sealed_at: str | None
    reflection: str | None = None
    artifact_description: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)

class PortfolioResponse(BaseModel):
    student_id: str
    items: list[PortfolioItem]


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
        try:
            await curriculum_graph.record_standard_mastery(
                student_id, body.track.value, body.oas_standards, proficiency=proficiency,
            )
        except Exception as exc:
            logger.exception("[/journal/seal] Mastery persistence failed")
            raise HTTPException(
                status_code=500,
                detail=f"Journal saved but mastery did not finish; retrying is safe: {exc}",
            ) from exc

    # Fire-and-forget BKT + SM-2 card update with quiz-derived quality signal
    asyncio.create_task(
        _update_card_safe(student_id, body)
    )

    # Learner-controlled payloads never set a transcript amount. Conventional
    # course equivalency is derived from reviewed standards/mastery reports.
    credit_sealed = False

    # Completion changes both mastery coverage and the next-best experience.
    # Invalidate the whole adaptive plan even when the lesson earns no credit.
    try:
        from app.api.learning_plan import pop_completed_lesson
        await pop_completed_lesson(student_id, body.plan_item_id or body.lesson_id)
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


def _quiz_quality(quiz_results: list[dict]) -> int:
    """Map an actual scored demonstration to SM-2 quality (0–5)."""
    if not quiz_results:
        return 0
    correct = sum(1 for q in quiz_results if q.get("correct"))
    ratio = correct / len(quiz_results)
    if ratio >= 0.9:
        return 5
    if ratio >= 0.75:
        return 4
    if ratio >= 0.5:
        return 2
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
    if not body.quiz_results:
        # Saving a reflection/artifact is not a correct BKT response.
        return
    try:
        from app.algorithms.bkt_tracker import update_card_after_lesson

        quality = _quiz_quality(body.quiz_results)

        concept_id   = body.concept_id
        concept_name = body.concept_name or ""

        # Never guess a mastery target. A quiz may count as lesson evidence,
        # but it cannot unlock a curriculum dependency without the exact
        # concept selected by the persisted plan.
        if not concept_id:
            logger.info("[Journal] Skipping concept mastery update: no exact concept_id")
            return

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


@router.get("/portfolio/{student_id}", response_model=PortfolioResponse)
async def get_portfolio_items(
    student_id: str,
    limit: int = 100,
    _user_id: str = Depends(verify_student_access),
):
    """Return durable investigation evidence for the learner portfolio."""
    from app.config import get_db_conn
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            '''SELECT j.lesson_id, j.track, j.sources_json, j.sealed_at,
                      COALESCE(e.title, j.lesson_id) AS title
               FROM student_journal j
               LEFT JOIN "StudentExperience" e
                 ON e.id = j.lesson_id AND e."studentId" = j.student_id
               WHERE j.student_id = $1
               ORDER BY j.sealed_at DESC LIMIT $2''',
            student_id, min(max(limit, 1), 200),
        )
    finally:
        await conn.close()

    items: list[PortfolioItem] = []
    for row in rows:
        try:
            sources = json.loads(row["sources_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            sources = []
        reflection = next((str(item.get("content")) for item in sources if item.get("type") == "learner_reflection" and item.get("content")), None)
        artifact = next((item for item in sources if item.get("type") == "artifact" or str(item.get("url") or "").startswith("portfolio://")), None)
        title = str((artifact or {}).get("title") or row["title"])
        artifact_description = str(artifact.get("author") or artifact.get("description") or artifact.get("title") or "Portfolio artifact") if artifact else None
        refs = list(dict.fromkeys(
            str(item.get("url")) for item in sources if item.get("url")
        ))
        items.append(PortfolioItem(
            lesson_id=str(row["lesson_id"]), title=title, track=str(row["track"]),
            sealed_at=row["sealed_at"].isoformat() if row["sealed_at"] else None,
            reflection=reflection, artifact_description=artifact_description, artifact_refs=refs,
        ))
    return PortfolioResponse(student_id=student_id, items=items)
