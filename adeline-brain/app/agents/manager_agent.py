"""
Manager Agent — Top-Level Orchestration Coordinator

Sits above the specialist orchestrator and the ZPD pedagogy agent.
Reads the student's Cognitive Twin before routing, shapes delivery,
and emits real-time events to connected monitoring WebSockets.

Decision pipeline:
  1. Load Cognitive Twin state
  2. Determine intervention mode: CONTINUE | SCAFFOLD | ELEVATE | BREAK
  3. Override track/mode if twin signals overload or frustration
  4. Call specialist orchestrator (lesson generation) OR pedagogy agent (scaffold)
  5. Run each block through ContentFilter safety gate
  6. Emit cognitive_update + block_generated events via WebSocket
  7. Update Cognitive Twin with interaction results
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Awaitable

from app.agents.cognitive_twin import (
    CognitiveTwinState,
    get_twin,
    update_from_response,
    recommend_intervention,
)
from app.agents.pedagogy import ZPDZone, scaffold_response
from app.safety.content_filter import content_filter, SafetyFlag
from app.schemas.api_models import LessonRequest, LessonResponse, LessonBlockResponse, BlockType

logger = logging.getLogger(__name__)

# Callable type for real-time event emitters (injected by WebSocket layer)
EventEmitter = Callable[[str, dict], Awaitable[None]]


class ManagerAgent:
    """
    Coordinates lesson delivery with cognitive state awareness.

    Usage:
        manager = ManagerAgent()
        response = await manager.generate(request, student_state, emit=ws_emitter)
    """

    async def generate(
        self,
        request: LessonRequest,
        student_state,
        emit: Optional[EventEmitter] = None,
    ) -> LessonResponse:
        """
        Full lesson generation with Cognitive Twin awareness + safety filtering.

        Args:
            request:       The original LessonRequest from the UI.
            student_state: StudentState (mastery, band, ZPD history).
            emit:          Optional async callable(event_type, payload) for WebSocket updates.
        """
        student_id = request.student_id

        # ── Step 1: Load Cognitive Twin ────────────────────────────────────────
        twin = await get_twin(student_id)
        intervention = recommend_intervention(twin)
        logger.info(
            f"[ManagerAgent] student={student_id} twin={twin.zpd_zone} "
            f"load={twin.working_memory_load:.2f} intervention={intervention}"
        )

        await _emit(emit, "cognitive_update", {
            "student_id": student_id,
            "zpd_zone": twin.zpd_zone,
            "working_memory_load": twin.working_memory_load,
            "engagement_level": twin.engagement_level,
            "frustration_score": twin.frustration_score,
            "session_block_count": twin.session_block_count,
            "intervention": intervention,
        })

        # ── Step 2: Intervention override ─────────────────────────────────────
        if intervention == "BREAK":
            return _break_response(request, twin)

        # ── Step 3: Route to orchestrator ─────────────────────────────────────
        from app.agents.orchestrator import run_lesson

        await _emit(emit, "agent_thinking", {
            "student_id": student_id,
            "message": f"Routing to specialist agent for {request.track}...",
            "track": request.track,
            "intervention": intervention,
        })

        response: LessonResponse = await run_lesson(
            request=request,
            student_state=student_state,
            elevate=(intervention == "ELEVATE"),
        )

        # ── Step 4: Safety filter each block ──────────────────────────────────
        grade_level = _infer_grade_level(request)
        filtered_blocks: list[LessonBlockResponse] = []

        for block in response.blocks:
            content_text = block.content or ""
            result = content_filter.check_block(content_text, block.block_type, grade_level)

            if not result.passed:
                logger.warning(
                    f"[ManagerAgent] Block BLOCKED — type={block.block_type} "
                    f"flags={result.flags}"
                )
                await _emit(emit, "safety_flag", {
                    "student_id": student_id,
                    "block_type": block.block_type,
                    "flags": [f.value for f in result.flags],
                    "warnings": result.warnings,
                })
                # Replace blocked block with a safe RESEARCH_MISSION redirect
                filtered_blocks.append(_safety_redirect_block(block))
                continue

            # Sanitize PII if needed
            if result.sanitized_content:
                block = block.model_copy(update={"content": result.sanitized_content})

            # Emit soft warnings to parent monitor (non-blocking)
            if result.warnings:
                await _emit(emit, "safety_flag", {
                    "student_id": student_id,
                    "block_type": block.block_type,
                    "flags": [f.value for f in result.flags],
                    "warnings": result.warnings,
                    "severity": "warning",
                })

            filtered_blocks.append(block)
            await _emit(emit, "block_generated", {
                "student_id": student_id,
                "block_type": block.block_type,
                "lesson_id": response.lesson_id,
            })

        response = response.model_copy(update={"blocks": filtered_blocks})

        # ── Step 5: Update Cognitive Twin ─────────────────────────────────────
        twin = await update_from_response(
            student_id=student_id,
            response_text="",
            was_correct=None,
            zpd_zone=twin.zpd_zone,
            track=request.track,
            block_count_delta=len(filtered_blocks),
        )

        await _emit(emit, "cognitive_update", {
            "student_id": student_id,
            "zpd_zone": twin.zpd_zone,
            "working_memory_load": twin.working_memory_load,
            "engagement_level": twin.engagement_level,
            "frustration_score": twin.frustration_score,
            "session_block_count": twin.session_block_count,
            "intervention": recommend_intervention(twin),
        })

        return response

    async def handle_student_response(
        self,
        student_id: str,
        response_text: str,
        was_correct: Optional[bool],
        track: str,
        emit: Optional[EventEmitter] = None,
    ) -> dict:
        """
        Process a student's answer/message and update Cognitive Twin.
        Returns the updated twin state + recommended next action.
        """
        from app.agents.pedagogy import detect_zpd_zone

        zpd_zone = detect_zpd_zone(response_text, {}, "IN_ZPD")
        twin = await update_from_response(
            student_id=student_id,
            response_text=response_text,
            was_correct=was_correct,
            zpd_zone=zpd_zone,
            track=track,
        )

        intervention = recommend_intervention(twin)
        await _emit(emit, "cognitive_update", {
            "student_id": student_id,
            "zpd_zone": twin.zpd_zone,
            "working_memory_load": twin.working_memory_load,
            "engagement_level": twin.engagement_level,
            "frustration_score": twin.frustration_score,
            "session_block_count": twin.session_block_count,
            "intervention": intervention,
        })

        if intervention == "SCAFFOLD":
            await _emit(emit, "zpd_shift", {
                "student_id": student_id,
                "zone": ZPDZone.FRUSTRATED.value,
                "consecutive_struggles": twin.consecutive_struggles,
            })

        return {
            "twin": twin.to_dict(),
            "intervention": intervention,
            "zpd_zone": zpd_zone,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _emit(emit: Optional[EventEmitter], event_type: str, payload: dict) -> None:
    if emit is None:
        return
    try:
        await emit(event_type, payload)
    except Exception as e:
        logger.debug(f"[ManagerAgent] Emit failed for {event_type}: {e}")


def _infer_grade_level(request: LessonRequest) -> int:
    if hasattr(request, "grade_level") and request.grade_level:
        return request.grade_level
    if hasattr(request, "grade_band") and request.grade_band:
        band = request.grade_band.upper()
        if "K" in band or "1" in band or "2" in band:
            return 2
        if "3" in band or "4" in band or "5" in band:
            return 4
        if "6" in band or "7" in band or "8" in band:
            return 7
        return 10
    return 7  # Default: middle school


def _break_response(request: LessonRequest, twin: CognitiveTwinState) -> LessonResponse:
    """Gentle break suggestion block when cognitive load is maxed."""
    from app.schemas.api_models import LessonResponse, LessonBlockResponse, BlockType
    import uuid

    break_block = LessonBlockResponse(
        block_id=str(uuid.uuid4()),
        block_type=BlockType.NARRATIVE,
        content=(
            "Your brain has been working hard! "
            f"You've covered {twin.session_block_count} lessons today. "
            "Take a 10-minute break — go outside, get some water, or do something physical. "
            "Come back ready to learn more!"
        ),
        title="Time for a Break",
        metadata={"is_break_suggestion": True},
    )
    return LessonResponse(
        lesson_id=str(uuid.uuid4()),
        blocks=[break_block],
        oas_standards=[],
        xapi_statements=[],
        credits_awarded=[],
        metadata={"break_suggested": True},
    )


def _safety_redirect_block(original: LessonBlockResponse) -> LessonBlockResponse:
    """Replace a blocked block with a safe RESEARCH_MISSION."""
    from app.schemas.api_models import BlockType

    return original.model_copy(update={
        "block_type": BlockType.RESEARCH_MISSION,
        "content": (
            "This content requires additional review before it can be shown. "
            "Ask your parent or teacher to help you find a primary source "
            "on this topic from a trusted archive like archive.org or NARA."
        ),
        "title": "Research Mission: Find a Primary Source",
        "evidence": None,
    })


# Singleton
manager_agent = ManagerAgent()
