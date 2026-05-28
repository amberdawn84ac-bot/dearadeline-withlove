"""
Manager Agent — Top-Level Orchestration Coordinator

Sits above the specialist orchestrator and the ZPD pedagogy agent.
Reads the student's Cognitive Twin before routing, shapes delivery,
and emits real-time events to connected monitoring WebSockets.

Decision pipeline:
  1. Load Cognitive Twin state
  2. Determine intervention mode: CONTINUE | SCAFFOLD | ELEVATE | BREAK
  2.5 Run ML Sequencer (5-algorithm blend) → select optimal React component
  3. Override track/mode if twin signals overload or frustration
  4. Call specialist orchestrator (lesson generation) OR pedagogy agent (scaffold)
  5. Run each block through ContentFilter safety gate
  6. Emit cognitive_update + block_generated + sequencer_decision events via WebSocket
  7. Update Cognitive Twin with interaction results
"""
from __future__ import annotations

import json
import logging
from typing import Optional, Callable, Awaitable

from app.agents.cognitive_twin import (
    CognitiveTwinState,
    get_twin,
    update_from_response,
    recommend_intervention,
)
from app.agents.pedagogy import ZPDZone
from app.safety.content_filter import content_filter
from app.schemas.api_models import LessonRequest, LessonResponse, LessonBlockResponse, BlockType
from app.algorithms.ml_sequencer import SequencerInput, SequencerDecision, sequence_next_component
from app.algorithms.rl_optimizer import serialize_q_table, deserialize_q_table

logger = logging.getLogger(__name__)

_Q_TABLE_TTL = 60 * 60 * 24 * 30  # 30 days

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

        # ── Step 2.5: ML Sequencer ────────────────────────────────────────────
        sequencer_decision = await _run_ml_sequencer(
            request=request,
            student_state=student_state,
            twin=twin,
            emit=emit,
        )

        # ── Step 3: Route to orchestrator ─────────────────────────────────────
        from app.agents.orchestrator import run_lesson

        await _emit(emit, "agent_thinking", {
            "student_id": student_id,
            "message": f"Routing to specialist agent for {request.track}...",
            "track": request.track,
            "intervention": intervention,
            "preferred_component": sequencer_decision.component_id if sequencer_decision else None,
        })

        # Inject sequencer decision into request metadata so adapter.py
        # can use the preferred component and pacing factor during transformation.
        enriched_request = _inject_sequencer_metadata(request, sequencer_decision)

        response: LessonResponse = await run_lesson(
            request=enriched_request,
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
    from app.schemas.api_models import LessonResponse, LessonBlockResponse
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


# ── ML Sequencer integration ──────────────────────────────────────────────────

async def _run_ml_sequencer(
    request: LessonRequest,
    student_state,
    twin: CognitiveTwinState,
    emit: Optional[EventEmitter],
) -> Optional[SequencerDecision]:
    """
    Build SequencerInput from available context, run the 5-algorithm ML blend,
    persist the Q-table to Redis, and emit a sequencer_decision WebSocket event.

    Returns None on any error — callers must treat this as optional enrichment.
    """
    student_id = request.student_id
    try:
        q_table = await _load_q_table(student_id)

        mastery_score = getattr(student_state, "mastery_score", None)
        if mastery_score is None:
            mastery_map: dict = getattr(student_state, "mastery_map", {})
            if mastery_map:
                mastery_score = sum(mastery_map.values()) / len(mastery_map)
            else:
                mastery_score = 0.5

        seq_input = SequencerInput(
            student_id=student_id,
            track=request.track,
            grade_band=_grade_band_from_request(request),
            zpd_zone=twin.zpd_zone,
            mastery_score=float(mastery_score),
            cognitive_load_level=_twin_load_to_level(twin.working_memory_load),
            consecutive_struggles=twin.consecutive_struggles,
            interaction_history=[],        # Caller can enrich via a DB fetch; graceful fallback
            recently_used_components=getattr(student_state, "recent_components", []),
            mastery_map=getattr(student_state, "mastery_map", {}),
            peer_profiles=[],              # Populated from DB fetch when available
            q_table=q_table,
            sm2_cards=[],                  # Populated from DB fetch when available
            mastery_checkpoints=[],        # Populated from DB fetch when available
            needs_assessment=_should_assess(student_state, twin),
            topic_tags=_track_to_tags(request.track),
            time_available_minutes=getattr(request, "time_available_minutes", 20),
        )

        decision = sequence_next_component(seq_input)

        # Persist updated Q-table (pre-lesson snapshot; post-lesson update happens
        # via apply_lesson_feedback() in the learning_records API route)
        await _save_q_table(student_id, decision.updated_q_table)

        await _emit(emit, "sequencer_decision", {
            "student_id": student_id,
            "component_id": decision.component_id,
            "confidence": decision.confidence,
            "reasons": decision.reasons,
            "profile_type": decision.profile.profile_type.value,
            "pacing_status": decision.pacing.status.value,
            "velocity": decision.pacing.velocity,
            "velocity_ratio": decision.pacing.velocity_ratio,
            "alternatives": decision.alternatives,
        })

        return decision

    except Exception as exc:
        logger.warning("[ManagerAgent] ML sequencer failed (non-fatal): %s", exc, exc_info=True)
        return None


def _inject_sequencer_metadata(
    request: LessonRequest,
    decision: Optional[SequencerDecision],
) -> LessonRequest:
    """Attach sequencer output to request.metadata without mutating the original."""
    if decision is None:
        return request
    extra = {
        "preferred_component": decision.component_id,
        "pacing_factor": decision.pacing.pacing_factor,
        "learner_profile": decision.profile.profile_type.value,
        "rl_state": list(decision.rl_state),
    }
    existing_meta: dict = dict(request.metadata) if getattr(request, "metadata", None) else {}
    existing_meta.update(extra)
    try:
        return request.model_copy(update={"metadata": existing_meta})
    except Exception:
        return request


async def _load_q_table(student_id: str) -> dict:
    """Load the student's Q-table from Redis, or return an empty table."""
    try:
        from app.connections.redis_client import redis_client
        raw = await redis_client.get(f"q_table:{student_id}")
        if raw:
            return deserialize_q_table(json.loads(raw))
    except Exception as exc:
        logger.debug("[ManagerAgent] Q-table load failed: %s", exc)
    return {}


async def _save_q_table(student_id: str, q_table: dict) -> None:
    """Persist the student's Q-table to Redis with a 30-day TTL."""
    try:
        from app.connections.redis_client import redis_client
        payload = json.dumps(serialize_q_table(q_table))
        await redis_client.set(f"q_table:{student_id}", payload, ex=_Q_TABLE_TTL)
    except Exception as exc:
        logger.debug("[ManagerAgent] Q-table save failed: %s", exc)


def _twin_load_to_level(working_memory_load: float) -> str:
    if working_memory_load > 0.80:
        return "CRITICAL"
    if working_memory_load > 0.60:
        return "HIGH"
    if working_memory_load > 0.30:
        return "MEDIUM"
    return "LOW"


def _grade_band_from_request(request: LessonRequest) -> str:
    grade = getattr(request, "grade_level", None) or getattr(request, "grade_band", None)
    if grade is None:
        return "68"
    grade_str = str(grade).lower().replace(" ", "").replace("-", "")
    if any(x in grade_str for x in ("k", "1", "2")):
        return "k2"
    if any(x in grade_str for x in ("3", "4", "5")):
        return "35"
    if any(x in grade_str for x in ("6", "7", "8")):
        return "68"
    return "912"


def _should_assess(student_state, twin: CognitiveTwinState) -> bool:
    """Recommend an assessment block when the student has had several successes."""
    consecutive_successes = getattr(twin, "consecutive_successes", 0)
    return consecutive_successes >= 3


def _track_to_tags(track: str) -> list[str]:
    """Map a curriculum track to relevant content tags for the content-based filter."""
    mapping: dict[str, list[str]] = {
        "CREATION_SCIENCE":      ["science", "exploration", "hands-on"],
        "HEALTH_NATUROPATHY":    ["health", "application", "scenario"],
        "HOMESTEADING":          ["hands-on", "application", "spatial"],
        "GOVERNMENT_ECONOMICS":  ["text", "reference", "key-terms"],
        "JUSTICE_CHANGEMAKING":  ["text", "reference", "problem-solving"],
        "DISCIPLESHIP":          ["reading", "key-terms", "reference"],
        "TRUTH_HISTORY":         ["text", "reference", "key-terms"],
        "ENGLISH_LITERATURE":    ["reading", "text", "lecture"],
        "APPLIED_MATHEMATICS":   ["math", "concrete", "spatial"],
        "CREATIVE_ECONOMY":      ["hands-on", "exploration", "application"],
    }
    return mapping.get(track, ["reading", "text"])


# Singleton
manager_agent = ManagerAgent()
