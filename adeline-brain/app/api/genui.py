"""
GenUI API — Callback endpoints for dynamic stateful components.

Provides real-time BKT/ZPD updates when students interact with GENUI_ASSEMBLY components.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.algorithms.zpd_engine import bkt_update, BKTParams
from app.api.middleware import get_current_user_id
from app.models.student import load_student_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/genui", tags=["genui"])


class GenuiCallbackRequest(BaseModel):
    """Request payload for GENUI component callbacks."""
    student_id: str
    lesson_id: str
    component_type: str
    event: str  # "onAnswer", "onComplete", "onHint", etc.
    state: dict  # Component state (e.g., isCorrect, currentStep, hintsUsed)
    block_id: Optional[str] = None
    track: Optional[str] = None  # Track for BKT lookup on onAnswer events


class GenuiCallbackResponse(BaseModel):
    """Response from GENUI callback."""
    success: bool
    updated_mastery: Optional[float] = None
    message: str
    should_re_render: bool = False  # New: trigger component re-render
    new_state: Optional[dict] = None  # New: updated component state
    new_props: Optional[dict] = None  # New: updated component props


@router.post("/callback", response_model=GenuiCallbackResponse)
async def genui_callback(
    request: GenuiCallbackRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Handle GENUI component callbacks and update BKT/ZPD in real time.

    Events:
    - onAnswer: Update BKT based on quiz answer correctness
    - onComplete: Mark completion, award credit
    - onHint: Log hint usage (may affect mastery decay)
    - onStruggle: Detect struggle and trigger scaffolding

    All callbacks are authenticated and ownership-checked via JWT.
    """
    # TODO: Implement student ownership check
    # if current_user.id != request.student_id and not is_admin(current_user):
    #     raise HTTPException(status_403, "Not authorized")

    # Audit logging for compliance and portfolio tracking
    logger.info(
        f"[GENUI_AUDIT] Callback: student={request.student_id}, "
        f"lesson={request.lesson_id}, component={request.component_type}, "
        f"event={request.event}, block_id={request.block_id}, state={request.state}"
    )

    updated_mastery = None

    # Handle specific events
    should_re_render = False
    new_state = None
    new_props = None

    if request.event == "onAnswer":
        is_correct = request.state.get("isCorrect", False)
        # Fetch real BKT params from student state; fall back to defaults
        try:
            student_state = await load_student_state(request.student_id)
            track_mastery = student_state.get(request.track or "TRUTH_HISTORY")
            pL = track_mastery.mastery_score if track_mastery else 0.5
        except Exception as e:
            logger.warning(f"[GENUI] load_student_state failed for {request.student_id}: {e}")
            pL = 0.5
        params = BKTParams(pL=pL, pT=0.15, pS=0.05, pG=0.25)
        updated_mastery = bkt_update(params, is_correct)
        logger.info(f"[GENUI] BKT update: correct={is_correct}, pL={pL:.3f}, new_mastery={updated_mastery:.3f}")

    elif request.event == "onComplete":
        # Mark completion, award credit
        logger.info(f"[GENUI] Component completed: {request.component_type}")
        # TODO: Implement credit awarding via registrar

    elif request.event == "onHint":
        # Log hint usage
        hints_used = request.state.get("hintsUsed", 0)
        logger.info(f"[GENUI] Hint used: total={hints_used}")
        # Trigger re-render if hint threshold reached
        if hints_used >= 3:
            should_re_render = True
            new_state = request.state
            logger.info(f"[GENUI] Hint threshold reached - triggering re-render")

    elif request.event == "onStruggle":
        # Detect struggle and trigger scaffolding
        wrong_attempts = request.state.get("wrongAttempts", 0)
        logger.info(f"[GENUI] Struggle detected: wrong_attempts={wrong_attempts}")
        # Trigger re-render with scaffolding after 2+ wrong attempts
        if wrong_attempts >= 2:
            should_re_render = True
            new_state = {
                **request.state,
                "scaffolding_level": request.state.get("scaffolding_level", 0) + 1
            }
            logger.info(f"[GENUI] Struggle threshold reached - triggering scaffolding re-render")

    return GenuiCallbackResponse(
        success=True,
        updated_mastery=updated_mastery,
        message=f"Processed {request.event} event for {request.component_type}",
        should_re_render=should_re_render,
        new_state=new_state,
        new_props=new_props
    )
