"""
Journal API — /journal/*

POST /journal/seal      — Seal a completed lesson into the student's journal
GET  /journal/progress/{student_id} — Fetch track progress counts
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any

from app.schemas.api_models import Track, UserRole
from app.api.middleware import require_role
from app.connections.journal_store import journal_store
from app.connections.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/journal", tags=["journal"])


# ── Request / Response models ─────────────────────────────────────────────────

class SealRequest(BaseModel):
    student_id:       str
    lesson_id:        str
    track:            Track
    completed_blocks: int = Field(default=0, ge=0)
    oas_standards:    list[dict[str, Any]] = Field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)


class SealResponse(BaseModel):
    sealed:         bool
    lesson_id:      str
    track:          Track
    track_progress: dict[str, int]


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


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/seal", response_model=SealResponse)
async def seal_journal(
    body: SealRequest,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Seal a lesson into the student's journal.

    - Upserts (student_id, lesson_id) into student_journal
    - Returns updated track_progress so the UI can refresh the dashboard
    """
    logger.info(
        f"[/journal/seal] student={body.student_id} "
        f"lesson={body.lesson_id} track={body.track.value} "
        f"blocks={body.completed_blocks}"
    )
    try:
        track_progress = await journal_store.seal(
            student_id=body.student_id,
            lesson_id=body.lesson_id,
            track=body.track.value,
            completed_blocks=body.completed_blocks,
            sources=body.evidence_sources or None,
        )
    except Exception as e:
        logger.exception("[/journal/seal] DB error")
        raise HTTPException(status_code=500, detail=str(e))

    # Fire-and-forget Neo4j Mastery relationships — never block the seal response
    if body.oas_standards:
        asyncio.create_task(
            _record_mastery_safe(body.student_id, body.track.value, body.oas_standards)
        )

    return SealResponse(
        sealed=True,
        lesson_id=body.lesson_id,
        track=body.track,
        track_progress=track_progress,
    )


async def _record_mastery_safe(student_id: str, track: str, oas_standards: list[dict]) -> None:
    try:
        await neo4j_client.record_mastery(student_id, track, oas_standards)
        logger.info(f"[Neo4j] Mastery recorded for {student_id} — {len(oas_standards)} standards")
    except Exception as exc:
        logger.warning(f"[Neo4j] Mastery write failed (non-fatal): {exc}")


@router.get("/progress/{student_id}", response_model=ProgressResponse)
async def get_progress(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
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
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
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
