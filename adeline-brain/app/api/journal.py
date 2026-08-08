"""Journal API — sealed learning plus saveable daily notes."""
import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.middleware import get_current_user_id, verify_student_access
from app.connections.journal_store import journal_store
from app.connections.neo4j_client import neo4j_client
from app.schemas.api_models import Track

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/journal", tags=["journal"])


class SealRequest(BaseModel):
    lesson_id: str
    track: Track
    completed_blocks: int = Field(default=0, ge=0)
    oas_standards: list[dict[str, Any]] = Field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)
    concept_id: str | None = None
    concept_name: str | None = None
    quiz_results: list[dict[str, Any]] = Field(default_factory=list)


class SealResponse(BaseModel):
    sealed: bool
    lesson_id: str
    track: Track
    track_progress: dict[str, int]


class ProgressResponse(BaseModel):
    student_id: str
    track_progress: dict[str, int]


class RecentEntry(BaseModel):
    lesson_id: str
    track: str
    completed_blocks: int
    sealed_at: str | None


class RecentResponse(BaseModel):
    student_id: str
    entries: list[RecentEntry]


class DailyNoteRequest(BaseModel):
    student_id: Optional[str] = None
    topic: str = Field(min_length=1, max_length=240)
    track: str = "ENGLISH_LITERATURE"
    learned: str = Field(min_length=1, max_length=12000)
    action: str | None = Field(default=None, max_length=1000)
    note: dict[str, Any] | None = None
    source: str = "adeline_conversation"


class DailyNoteResponse(BaseModel):
    id: str
    student_id: str
    topic: str
    track: str
    created_at: str


class DailyNoteItem(BaseModel):
    id: str
    topic: str
    track: str
    learned: str
    action: str | None
    note: dict[str, Any] | None
    source: str
    created_at: str | None


class DailyNotesResponse(BaseModel):
    student_id: str
    notes: list[DailyNoteItem]


@router.post("/seal", response_model=SealResponse)
async def seal_journal(body: SealRequest, student_id: str = Depends(get_current_user_id)):
    try:
        track_progress = await journal_store.seal(
            student_id=student_id,
            lesson_id=body.lesson_id,
            track=body.track.value,
            completed_blocks=body.completed_blocks,
            sources=body.evidence_sources or None,
        )
    except Exception as exc:
        logger.exception("[/journal/seal] DB error")
        raise HTTPException(status_code=500, detail=str(exc))

    from app.models.student import invalidate_student_state_cache

    await invalidate_student_state_cache(student_id)
    if body.oas_standards:
        asyncio.create_task(_record_mastery_safe(student_id, body.track.value, body.oas_standards))
    asyncio.create_task(_update_card_safe(student_id, body))
    return SealResponse(
        sealed=True,
        lesson_id=body.lesson_id,
        track=body.track,
        track_progress=track_progress,
    )


@router.post("/entries", response_model=DailyNoteResponse)
async def create_daily_note(body: DailyNoteRequest, student_id: str = Depends(get_current_user_id)):
    try:
        saved = await journal_store.add_daily_note(
            student_id=student_id,
            topic=body.topic,
            track=body.track,
            learned=body.learned,
            action=body.action,
            note=body.note,
            source=body.source,
        )
        return DailyNoteResponse(**saved)
    except Exception as exc:
        logger.exception("[/journal/entries] save failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/entries/{student_id}", response_model=DailyNotesResponse)
async def list_daily_notes(
    student_id: str,
    limit: int = Query(50, ge=1, le=200),
    _user_id: str = Depends(verify_student_access),
):
    try:
        notes = await journal_store.get_daily_notes(student_id, limit=limit)
        return DailyNotesResponse(
            student_id=student_id,
            notes=[DailyNoteItem(**note) for note in notes],
        )
    except Exception as exc:
        logger.exception("[/journal/entries] list failed")
        raise HTTPException(status_code=500, detail=str(exc))


async def _record_mastery_safe(student_id: str, track: str, oas_standards: list[dict]) -> None:
    try:
        await neo4j_client.record_mastery(student_id, track, oas_standards)
    except Exception as exc:
        logger.warning(f"[Neo4j] Mastery write failed (non-fatal): {exc}")


def _quiz_quality(quiz_results: list[dict]) -> int:
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


async def _update_card_safe(student_id: str, body: SealRequest) -> None:
    try:
        from app.algorithms.bkt_tracker import update_card_after_lesson
        from app.tools.graph_query import tool_get_zpd_candidates

        quality = _quiz_quality(body.quiz_results)
        concept_id = body.concept_id
        concept_name = body.concept_name or ""
        if not concept_id:
            zpd = await tool_get_zpd_candidates(student_id, body.track.value, limit=1)
            if zpd:
                concept_id = zpd[0].concept_id
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
async def get_progress(student_id: str, _user_id: str = Depends(verify_student_access)):
    try:
        track_progress = await journal_store.get_track_progress(student_id)
    except Exception as exc:
        logger.exception("[/journal/progress] DB error")
        raise HTTPException(status_code=500, detail=str(exc))
    return ProgressResponse(student_id=student_id, track_progress=track_progress)


@router.get("/recent/{student_id}", response_model=RecentResponse)
async def get_recent(
    student_id: str,
    limit: int = 10,
    _user_id: str = Depends(verify_student_access),
):
    try:
        entries = await journal_store.get_recent(student_id, limit=min(limit, 50))
    except Exception as exc:
        logger.exception("[/journal/recent] DB error")
        raise HTTPException(status_code=500, detail=str(exc))
    return RecentResponse(
        student_id=student_id,
        entries=[RecentEntry(**entry) for entry in entries],
    )
