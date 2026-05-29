"""
Focus API — Block-level timing and focus gap detection.

Tracks how long students spend on each block, counts rapid exits,
and surfaces COGNITIVE_OVERLOAD vs EXTERNAL_DISTRACTION signals
stored in the student's CognitiveTwin Redis session.

Focus gap events are persisted as xAPI LearningRecords with verb
`focus_gap_detected` for parent/teacher monitoring.

Endpoints:
  POST /focus/block-enter       — student entered a block (start timing)
  POST /focus/block-exit        — student exited a block (record duration)
  GET  /focus/gap/{student_id}  — current focus gap status
  POST /focus/reset-complete    — FocusReset finished, return SM-2 re-entry card
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.cognitive_twin import (
    CognitiveTwinState,
    get_twin,
    save_twin,
)
from app.api.middleware import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/focus", tags=["focus"])

_RAPID_EXIT_THRESHOLD_MS = 10_000  # < 10 s counts as a rapid exit


# ── Request / Response models ─────────────────────────────────────────────────

class BlockEnterRequest(BaseModel):
    student_id: str
    block_id: str
    block_type: str
    timestamp_ms: Optional[int] = None


class BlockExitRequest(BaseModel):
    student_id: str
    block_id: str
    duration_ms: int
    interaction_count: int = 0


class FocusGapResponse(BaseModel):
    focus_gap: Optional[str] = None   # "COGNITIVE_OVERLOAD" | "EXTERNAL_DISTRACTION" | None
    rapid_exit_count: int = 0
    engagement_level: float = 1.0


class FocusResetCompleteRequest(BaseModel):
    student_id: str
    reset_mode: str = "breathe"       # "breathe" | "ground" | "move"
    track: Optional[str] = None


class FocusResetCompleteResponse(BaseModel):
    cleared: bool
    reentry_block: Optional[dict] = None  # Flashcard block for soft re-entry, if SM-2 card due


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/block-enter", status_code=202)
async def block_enter(
    request: BlockEnterRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Record that a student entered a block. Fire-and-forget."""
    try:
        twin = await get_twin(request.student_id)
        twin.last_block_entered_iso = datetime.now(timezone.utc).isoformat()
        twin.interaction_count_per_block = 0
        await save_twin(twin)
    except Exception as exc:
        logger.warning("[Focus] block-enter save failed (non-fatal): %s", exc)
    return {"status": "accepted"}


@router.post("/block-exit", response_model=FocusGapResponse)
async def block_exit(
    request: BlockExitRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Record that a student exited a block.
    Updates response_latencies and rapid_exit_count on the CognitiveTwin.
    Persists a focus_gap_detected xAPI event if a gap is detected.
    """
    try:
        twin = await get_twin(request.student_id)

        # Update latency ring buffer (last 10)
        twin.response_latencies.append(request.duration_ms)
        if len(twin.response_latencies) > 10:
            twin.response_latencies = twin.response_latencies[-10:]

        # Track interactions in this block
        twin.interaction_count_per_block = request.interaction_count

        # Rapid exit tracking (ring buffer of last 10 exits)
        if request.duration_ms < _RAPID_EXIT_THRESHOLD_MS:
            twin.rapid_exit_count = min(twin.rapid_exit_count + 1, 10)
        else:
            twin.rapid_exit_count = max(twin.rapid_exit_count - 1, 0)

        gap = twin.detect_focus_gap()
        if gap and not twin.focus_gap_detected:
            twin.focus_gap_detected = True
            await _persist_focus_gap_event(
                student_id=request.student_id,
                block_id=request.block_id,
                gap_type=gap,
            )

        await save_twin(twin)

        return FocusGapResponse(
            focus_gap=gap,
            rapid_exit_count=twin.rapid_exit_count,
            engagement_level=twin.engagement_level,
        )

    except Exception as exc:
        logger.warning("[Focus] block-exit failed (non-fatal): %s", exc)
        return FocusGapResponse()


@router.get("/gap/{student_id}", response_model=FocusGapResponse)
async def get_focus_gap(
    student_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """Return the current focus gap status for a student."""
    try:
        twin = await get_twin(student_id)
        gap = twin.detect_focus_gap()
        return FocusGapResponse(
            focus_gap=gap,
            rapid_exit_count=twin.rapid_exit_count,
            engagement_level=twin.engagement_level,
        )
    except Exception as exc:
        logger.warning("[Focus] gap check failed (non-fatal): %s", exc)
        return FocusGapResponse()


@router.post("/reset-complete", response_model=FocusResetCompleteResponse)
async def reset_complete(
    request: FocusResetCompleteRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Called when the FocusReset component completes.
    Clears focus gap flags on the CognitiveTwin and returns the first
    due SM-2 card as a soft re-entry block.
    """
    try:
        twin = await get_twin(request.student_id)
        twin.focus_gap_detected = False
        twin.rapid_exit_count = 0
        twin.consecutive_struggles = max(0, twin.consecutive_struggles - 1)
        twin.working_memory_load = max(0.1, twin.working_memory_load - 0.25)
        await save_twin(twin)
    except Exception as exc:
        logger.warning("[Focus] reset-complete twin clear failed (non-fatal): %s", exc)

    reentry_block = await _fetch_sm2_reentry_block(
        student_id=request.student_id,
        track=request.track,
    )

    return FocusResetCompleteResponse(cleared=True, reentry_block=reentry_block)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _persist_focus_gap_event(
    student_id: str,
    block_id: str,
    gap_type: str,
) -> None:
    """Persist a focus_gap_detected xAPI event to LearningRecord."""
    try:
        from app.api.learning_records import RecordLearningRequest, XAPIStatementIn, record_learning

        now_iso = datetime.now(timezone.utc).isoformat()
        stmt = XAPIStatementIn(
            id=str(uuid.uuid4()),
            student_id=student_id,
            lesson_id=block_id or "focus-monitor",
            block_id=block_id,
            verb="focus_gap_detected",
            object_id=f"https://adeline.app/focus/{gap_type.lower()}",
            object_name=f"Focus Gap: {gap_type.replace('_', ' ').title()}",
            track="TRUTH_HISTORY",   # placeholder — focus gaps are track-agnostic
            block_type="FOCUS_GAP",
            statement_json={
                "actor": {
                    "objectType": "Agent",
                    "account": {"homePage": "https://adeline.app", "name": student_id},
                },
                "verb": {
                    "id": "https://adeline.app/verbs/focus_gap_detected",
                    "display": {"en-US": "focus gap detected"},
                },
                "object": {
                    "id": f"https://adeline.app/focus/{gap_type.lower()}",
                    "definition": {"name": {"en-US": gap_type.replace("_", " ").title()}},
                },
                "result": {"extensions": {"gap_type": gap_type}},
                "timestamp": now_iso,
            },
        )
        await record_learning(RecordLearningRequest(statements=[stmt]))
        logger.info("[Focus] Gap event persisted: student=%s gap=%s", student_id, gap_type)
    except Exception as exc:
        logger.warning("[Focus] Gap event persist failed (non-fatal): %s", exc)


async def _fetch_sm2_reentry_block(
    student_id: str,
    track: Optional[str],
) -> Optional[dict]:
    """
    Fetch the first due SM-2 card and return it as a Flashcard GENUI_ASSEMBLY block.
    Returns None if no cards are due.
    """
    try:
        from app.config import get_db_conn
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _conn():
            conn = await get_db_conn()
            try:
                yield conn
            finally:
                await conn.close()

        now = datetime.now(timezone.utc)
        query = """
            SELECT id, "conceptId", "conceptName", track
            FROM "SpacedRepetitionCard"
            WHERE "studentId" = $1 AND "dueAt" <= $2
        """
        params = [student_id, now]
        if track:
            query += ' AND track = $3 ORDER BY "dueAt" ASC LIMIT 1'
            params.append(track)
        else:
            query += ' ORDER BY "dueAt" ASC LIMIT 1'

        async with _conn() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            return None

        return {
            "block_id": str(uuid.uuid4()),
            "block_type": "GENUI_ASSEMBLY",
            "content": f"Quick review: {row['conceptName']}",
            "genui_component": "Flashcard",
            "genui_props": {
                "front": row["conceptName"],
                "back": f"Review: {row['conceptName']}",
                "category": row["track"],
                "cardId": row["id"],
                "studentId": student_id,
            },
        }
    except Exception as exc:
        logger.warning("[Focus] SM-2 re-entry fetch failed (non-fatal): %s", exc)
        return None
