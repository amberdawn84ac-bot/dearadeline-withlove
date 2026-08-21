"""Live learner-response monitor.

This module intentionally cannot generate lessons. Canonical investigations are
the sole lesson source; this monitor only updates cognitive state from responses.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Optional

from app.agents.cognitive_twin import recommend_intervention, update_from_response
from app.agents.pedagogy import ZPDZone

logger = logging.getLogger(__name__)
EventEmitter = Callable[[str, dict], Awaitable[None]]


async def _emit(emit: Optional[EventEmitter], event_type: str, payload: dict) -> None:
    if emit is None:
        return
    try:
        await emit(event_type, payload)
    except Exception as exc:
        logger.debug("Response monitor emit failed for %s: %s", event_type, exc)


class LearnerResponseMonitor:
    async def handle_student_response(
        self,
        student_id: str,
        response_text: str,
        was_correct: Optional[bool],
        track: str,
        emit: Optional[EventEmitter] = None,
    ) -> dict:
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
        return {"twin": twin.to_dict(), "intervention": intervention, "zpd_zone": zpd_zone}


# Compatibility name for the realtime response channel. It is not a lesson manager.
manager_agent = LearnerResponseMonitor()
