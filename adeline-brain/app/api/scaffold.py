"""
Scaffold API — /lesson/scaffold
ZPD-aware response endpoint. Call this when the student replies to a lesson block.

POST /lesson/scaffold
  body: { student_id, topic, track, grade_level, student_response }
  returns: { zpd_zone, adeline_response, witness_anchor_used, mastery_band, mastery_score }
"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.schemas.api_models import Track, UserRole
from app.api.middleware import require_role, get_current_user_id, verify_student_access
from app.models.student import load_student_state
from app.agents.pedagogy import scaffold, explain_snippet, ZPDZone
from app.models.student import MasteryBand
from app.services.memory import memory_service
from app.algorithms.bkt_tracker import update_bkt, zpd_zone_to_correctness

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["scaffold"])


class ScaffoldRequest(BaseModel):
    student_id:       str
    topic:            str
    track:            Track
    grade_level:      str
    student_response: str
    concept_id:       str | None = None  # Optional: provided by UI from ZPD suggestion card


class ScaffoldResponseBody(BaseModel):
    zpd_zone:            ZPDZone
    adeline_response:    str
    witness_anchor_used: str | None
    mastery_band:        MasteryBand
    mastery_score:       float


@router.post(
    "/scaffold",
    response_model=ScaffoldResponseBody,
)
async def scaffold_response(body: ScaffoldRequest, student_id: str = Depends(get_current_user_id)):
    """
    Evaluate a student's in-lesson response and return a ZPD-appropriate reply.

    ZPD Zones:
      FRUSTRATED → Bridge Response using Witness Anchors from mastered lessons
      BORED      → Elevation Response with higher-order challenge
      IN_ZPD     → Socratic Response to keep the student moving
    """
    logger.info(
        f"[/lesson/scaffold] student={student_id} "
        f"topic='{body.topic}' track={body.track.value}"
    )

    try:
        student_state = await load_student_state(student_id)
        result = await scaffold(
            student_response=body.student_response,
            topic=body.topic,
            track=body.track.value,
            student_state=student_state,
        )
        
        # Save the interaction to conversation memory
        try:
            await memory_service.save_interaction(
                student_id=student_id,
                user_message=body.student_response,
                assistant_response=result.adeline_response,
                zpd_zone=result.zpd_zone.value,
                mastery_band=result.mastery_band.value,
                track=body.track.value,
            )
        except Exception as mem_err:
            logger.warning(f"[/lesson/scaffold] Memory save failed (non-fatal): {mem_err}")

        # Fire BKT update — feed ZPD zone back into per-concept mastery model (non-blocking)
        # concept_id is optional: provided when UI passes it from a ZPD suggestion card.
        # When absent, we look up the top ZPD candidate for the track as a best-effort proxy.
        import asyncio as _asyncio

        async def _fire_bkt():
            try:
                concept_id = body.concept_id
                if not concept_id:
                    from app.tools.graph_query import tool_get_zpd_candidates
                    candidates = await tool_get_zpd_candidates(student_id, body.track.value, limit=1)
                    if candidates:
                        concept_id = candidates[0].concept_id

                if concept_id:
                    correct = zpd_zone_to_correctness(result.zpd_zone.value)
                    if correct is not None:
                        await update_bkt(student_id, concept_id, body.track.value, correct)
            except Exception as bkt_err:
                logger.debug(f"[/lesson/scaffold] BKT update failed (non-fatal): {bkt_err}")

        _asyncio.create_task(_fire_bkt())
            
    except Exception as e:
        logger.exception("[/lesson/scaffold] Unexpected error")
        raise HTTPException(status_code=500, detail=str(e))

    return ScaffoldResponseBody(
        zpd_zone=result.zpd_zone,
        adeline_response=result.adeline_response,
        witness_anchor_used=result.witness_anchor_used,
        mastery_band=result.mastery_band,
        mastery_score=result.mastery_score,
    )


@router.get(
    "/student-state/{student_id}",
)
async def get_student_state(student_id: str, _user_id: str = Depends(verify_student_access)):
    """
    Return the student's full mastery profile across all 8 tracks.
    Used by the parent dashboard and the ZPD Engine.
    """
    try:
        state = await load_student_state(student_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "student_id": state.student_id,
        "tracks": {
            track: {
                "mastery_score": tm.mastery_score,
                "mastery_band": tm.mastery_band.value,
                "lesson_count": tm.lesson_count,
                "mastered_standards_count": len(tm.mastered_standards),
            }
            for track, tm in state.tracks.items()
        },
    }


# ── Ask Context (Highlight & Ask) ────────────────────────────────────────────


class AskContextRequest(BaseModel):
    """Request body for the Highlight & Ask feature."""
    student_id:       str
    snippet:          str           # The highlighted text
    lesson_topic:     str           # Topic of the current lesson
    track:            Track         # Learning track
    student_question: str | None = None  # Optional specific question


class AskContextResponse(BaseModel):
    """Response for the Highlight & Ask feature."""
    explanation:        str
    follow_up_question: str
    zpd_zone:           ZPDZone
    mastery_band:       MasteryBand


@router.post(
    "/ask-context",
    response_model=AskContextResponse,
)
async def ask_context(body: AskContextRequest, _user_id: str = Depends(get_current_user_id)):
    """
    Explain a highlighted text snippet from a lesson.
    
    This is the backend for the "Highlight & Ask" feature. When a student
    highlights text in a lesson and clicks "Ask Adeline", this endpoint
    generates a quick, ZPD-adapted micro-explanation.
    
    The explanation is tailored to:
    - The student's current mastery level in the track
    - The context of the lesson topic
    - Any specific question the student asked
    
    Returns a brief explanation (2-3 sentences) plus a follow-up question
    to check understanding or invite deeper thinking.
    """
    logger.info(
        f"[/lesson/ask-context] student={body.student_id} "
        f"topic='{body.lesson_topic}' snippet_len={len(body.snippet)}"
    )

    # Validate snippet length
    if len(body.snippet.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Highlighted text is too short. Please select at least 10 characters."
        )
    
    if len(body.snippet) > 1000:
        # Truncate very long selections
        body.snippet = body.snippet[:1000] + "…"

    try:
        student_state = await load_student_state(body.student_id)
        result = await explain_snippet(
            snippet=body.snippet,
            lesson_topic=body.lesson_topic,
            track=body.track.value,
            student_state=student_state,
            student_question=body.student_question,
        )
    except Exception as e:
        logger.exception("[/lesson/ask-context] Unexpected error")
        raise HTTPException(status_code=500, detail=str(e))

    return AskContextResponse(
        explanation=result.explanation,
        follow_up_question=result.follow_up_question,
        zpd_zone=result.zpd_zone,
        mastery_band=result.mastery_band,
    )
