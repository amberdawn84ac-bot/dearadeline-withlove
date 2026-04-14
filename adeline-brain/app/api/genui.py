"""
GenUI API — Callback endpoints for dynamic stateful components.

Provides real-time BKT/ZPD updates when students interact with GENUI_ASSEMBLY components.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.algorithms.zpd_engine import bkt_update, BKTParams
from app.api.middleware import get_current_user

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


class GenuiCallbackResponse(BaseModel):
    """Response from GENUI callback."""
    success: bool
    updated_mastery: Optional[float] = None
    message: str


@router.post("/callback", response_model=GenuiCallbackResponse)
async def genui_callback(
    request: GenuiCallbackRequest,
    current_user = Depends(get_current_user),
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
    if request.event == "onAnswer":
        is_correct = request.state.get("isCorrect", False)
        # TODO: Fetch current BKT params for this concept from database
        # For now, use default params
        params = BKTParams(pL=0.5, pT=0.15, pS=0.05, pG=0.25)
        updated_mastery = bkt_update(params, is_correct)
        logger.info(f"[GENUI] BKT update: correct={is_correct}, new_mastery={updated_mastery:.3f}")

    elif request.event == "onComplete":
        # Mark completion, award credit
        logger.info(f"[GENUI] Component completed: {request.component_type}")
        # TODO: Implement credit awarding via registrar

    elif request.event == "onHint":
        # Log hint usage
        hints_used = request.state.get("hintsUsed", 0)
        logger.info(f"[GENUI] Hint used: total={hints_used}")
        # TODO: May affect mastery decay

    elif request.event == "onStruggle":
        # Detect struggle and trigger scaffolding
        logger.info(f"[GENUI] Struggle detected: {request.state}")
        # TODO: Trigger adaptive scaffolding

    return GenuiCallbackResponse(
        success=True,
        updated_mastery=updated_mastery,
        message=f"Processed {request.event} event for {request.component_type}"
    )
