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
from app.api.middleware import require_role
from app.models.student import load_student_state
from app.agents.pedagogy import scaffold, ZPDZone
from app.models.student import MasteryBand

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["scaffold"])


class ScaffoldRequest(BaseModel):
    student_id:       str
    topic:            str
    track:            Track
    grade_level:      str
    student_response: str


class ScaffoldResponseBody(BaseModel):
    zpd_zone:            ZPDZone
    adeline_response:    str
    witness_anchor_used: str | None
    mastery_band:        MasteryBand
    mastery_score:       float


@router.post(
    "/scaffold",
    response_model=ScaffoldResponseBody,
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.ADMIN))],
)
async def scaffold_response(body: ScaffoldRequest):
    """
    Evaluate a student's in-lesson response and return a ZPD-appropriate reply.

    ZPD Zones:
      FRUSTRATED → Bridge Response using Witness Anchors from mastered lessons
      BORED      → Elevation Response with higher-order challenge
      IN_ZPD     → Socratic Response to keep the student moving
    """
    logger.info(
        f"[/lesson/scaffold] student={body.student_id} "
        f"topic='{body.topic}' track={body.track.value}"
    )

    try:
        student_state = await load_student_state(body.student_id)
        result = await scaffold(
            student_response=body.student_response,
            topic=body.topic,
            track=body.track.value,
            student_state=student_state,
        )
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
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))],
)
async def get_student_state(student_id: str):
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
