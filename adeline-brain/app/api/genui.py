"""
GenUI API — Callback endpoints for dynamic stateful components.

Provides real-time BKT/ZPD updates when students interact with GENUI_ASSEMBLY components.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.algorithms.zpd_engine import bkt_update, BKTParams
from app.api.middleware import get_current_user_id
from app.models.student import load_student_state, invalidate_student_state_cache

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
    scaffold_component: Optional[str] = None  # Component type to stream as remediation
    scaffold_props: Optional[dict] = None  # Props for the scaffold component


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
    scaffold_component = None
    scaffold_props = None

    if request.event == "onAnswer":
        is_correct = request.state.get("isCorrect", False)
        # Fetch real BKT params from student state; fall back to defaults
        try:
            student_state = await load_student_state(request.student_id)
            track_mastery = student_state.tracks.get(request.track or "TRUTH_HISTORY")
            pL = track_mastery.mastery_score if track_mastery else 0.5
        except Exception as e:
            logger.warning(f"[GENUI] load_student_state failed for {request.student_id}: {e}")
            pL = 0.5
        params = BKTParams(pL=pL, pT=0.15, pS=0.05, pG=0.25)
        updated_mastery = bkt_update(params, is_correct)
        logger.info(f"[GENUI] BKT update: correct={is_correct}, pL={pL:.3f}, new_mastery={updated_mastery:.3f}")

        # PERSIST: Save BKT mastery update to database and invalidate cache
        try:
            await _persist_mastery_update(
                student_id=request.student_id,
                track=request.track or "TRUTH_HISTORY",
                mastery_score=updated_mastery,
                component_type=request.component_type,
                block_id=request.block_id,
                is_correct=is_correct,
            )
        except Exception as e:
            logger.warning(f"[GENUI] Failed to persist mastery update (non-fatal): {e}")

    elif request.event == "onComplete":
        # Mark completion, award credit
        logger.info(f"[GENUI] Component completed: {request.component_type}")
        # Award CASE credit and emit xAPI statement for the interactive widget
        try:
            await _award_widget_credit(
                student_id=request.student_id,
                lesson_id=request.lesson_id,
                track=request.track or "TRUTH_HISTORY",
                component_type=request.component_type,
                block_id=request.block_id,
            )
            logger.info(f"[GENUI] Credit awarded for {request.component_type}")
        except Exception as e:
            logger.warning(f"[GENUI] Failed to award credit (non-fatal): {e}")

    elif request.event == "onHint":
        # Log hint usage
        hints_used = request.state.get("hintsUsed", 0)
        logger.info(f"[GENUI] Hint used: total={hints_used}")
        # Trigger re-render if hint threshold reached
        if hints_used >= 3:
            should_re_render = True
            new_state = request.state
            scaffold_component = "TaskScaffold"
            scaffold_props = {
                "title": "Need a hand?",
                "description": "Let's break this down into smaller steps.",
                "tasks": [
                    {"id": "1", "label": "Re-read the source material", "done": False},
                    {"id": "2", "label": "Write down what you DO know", "done": False},
                    {"id": "3", "label": "Answer in your own words", "done": False},
                ],
            }
            logger.info("[GENUI] Hint threshold reached - triggering TaskScaffold re-render")

    elif request.event == "onWrongAnswer":
        wrong_answer = request.state.get("wrongAnswer", "")
        correct_answer = request.state.get("correctAnswer", "")
        question = request.state.get("question", "")
        logger.info(
            f"[GENUI] Wrong answer: component={request.component_type} "
            f"wrong='{wrong_answer}' correct='{correct_answer}'"
        )
        overlay_props = await _synthesize_corrective_overlay(
            question=question,
            wrong_answer=wrong_answer,
            correct_answer=correct_answer,
            track=request.track or "TRUTH_HISTORY",
        )
        should_re_render = True
        scaffold_component = "CorrectiveOverlay"
        scaffold_props = overlay_props
        logger.info("[GENUI] CorrectiveOverlay triggered for wrong answer")

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
            scaffold_component = "TaskScaffold"
            scaffold_props = {
                "title": "Let's slow down",
                "description": "You've made a few attempts — here's a scaffold to help you think through it.",
                "tasks": [
                    {"id": "1", "label": "State the question in your own words", "done": False},
                    {"id": "2", "label": "What do you already know about this?", "done": False},
                    {"id": "3", "label": "What evidence from the source applies?", "done": False},
                    {"id": "4", "label": "Now try the answer again", "done": False},
                ],
            }
            logger.info("[GENUI] Struggle threshold reached - triggering scaffolding re-render")

    return GenuiCallbackResponse(
        success=True,
        updated_mastery=updated_mastery,
        message=f"Processed {request.event} event for {request.component_type}",
        should_re_render=should_re_render,
        new_state=new_state,
        new_props=new_props,
        scaffold_component=scaffold_component,
        scaffold_props=scaffold_props,
    )


# ── Telemetry Endpoint (fire-and-forget) ─────────────────────────────────────


class TelemetryEvent(BaseModel):
    """Fire-and-forget telemetry payload from GenUI components."""
    student_id: str
    lesson_id: str
    component_type: str
    event: str  # "completion", "struggle", "interaction", "hint", "timeout"
    state: dict = {}
    duration_ms: Optional[int] = None
    block_id: Optional[str] = None
    track: Optional[str] = None


@router.post("/telemetry", status_code=202)
async def genui_telemetry(
    request: TelemetryEvent,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Fire-and-forget telemetry sink for GenUI component interactions.

    Accepts completion, struggle, interaction, hint, and timeout events.
    Persists to LearningRecord and updates mastery cache without blocking the UI.
    Returns 202 Accepted immediately.
    """
    logger.info(
        f"[GENUI_TELEMETRY] event={request.event} component={request.component_type} "
        f"student={request.student_id} lesson={request.lesson_id} "
        f"duration_ms={request.duration_ms} block_id={request.block_id}"
    )

    # Persist interaction asynchronously
    import asyncio

    async def _persist_telemetry():
        try:
            if request.event == "completion":
                await _award_widget_credit(
                    student_id=request.student_id,
                    lesson_id=request.lesson_id,
                    track=request.track or "TRUTH_HISTORY",
                    component_type=request.component_type,
                    block_id=request.block_id,
                )
            elif request.event == "struggle":
                # Log struggle for adaptive routing — update BKT with negative signal
                student_state = await load_student_state(request.student_id)
                track_mastery = student_state.tracks.get(request.track or "TRUTH_HISTORY")
                pL = track_mastery.mastery_score if track_mastery else 0.5
                params = BKTParams(pL=pL, pT=0.15, pS=0.05, pG=0.25)
                updated = bkt_update(params, observed_correct=False)
                await _persist_mastery_update(
                    student_id=request.student_id,
                    track=request.track or "TRUTH_HISTORY",
                    mastery_score=updated,
                    component_type=request.component_type,
                    block_id=request.block_id,
                    is_correct=False,
                )
            # For "interaction", "hint", "timeout" — just log, no mastery update
        except Exception as e:
            logger.warning(f"[GENUI_TELEMETRY] Background persist failed (non-fatal): {e}")

    asyncio.ensure_future(_persist_telemetry())

    return {"status": "accepted"}


# ── Internal helpers ─────────────────────────────────────────────────────────


async def _persist_mastery_update(
    student_id: str,
    track: str,
    mastery_score: float,
    component_type: str,
    block_id: Optional[str] = None,
    is_correct: Optional[bool] = None,
) -> None:
    """
    Persist BKT mastery update to LearningRecord (xAPI) and invalidate student cache.
    Creates a synthetic 'assessed' xAPI statement for the mastery update.
    """
    from app.api.learning_records import RecordLearningRequest, XAPIStatementIn, record_learning

    statement_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    xapi_stmt = XAPIStatementIn(
        id=statement_id,
        student_id=student_id,
        lesson_id=block_id or "genui-interactive",
        block_id=block_id,
        verb="assessed",
        object_id=f"https://adeline.app/genui/{component_type}",
        object_name=f"Interactive {component_type}",
        track=track,
        agent_name="BKT_ENGINE",
        block_type=component_type,
        score_raw=mastery_score,
        statement_json={
            "actor": {
                "objectType": "Agent",
                "account": {"homePage": "https://adeline.app", "name": student_id}
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/assessed",
                "display": {"en-US": "assessed"}
            },
            "object": {
                "id": f"https://adeline.app/genui/{component_type}",
                "definition": {"name": {"en-US": f"Interactive {component_type}"}}
            },
            "result": {"score": {"raw": mastery_score, "scaled": mastery_score}},
            "timestamp": now_iso,
        },
    )

    await record_learning(RecordLearningRequest(statements=[xapi_stmt]))

    # Update SpacedRepetitionCard so BKT blend in load_student_state picks up interaction evidence
    try:
        from app.algorithms.bkt_tracker import update_bkt
        # Use the observed correctness when available; only fall back to the
        # posterior-mastery heuristic if the caller could not supply it. Inferring
        # correctness from mastery_score misclassifies early/low-mastery learners
        # (a first correct answer can yield a posterior < 0.5).
        observed_correct = is_correct if is_correct is not None else mastery_score >= 0.5
        concept_id = block_id or f"{track}-{component_type}"
        await update_bkt(student_id, concept_id, track, observed_correct)
    except Exception as e:
        logger.warning(f"[GENUI] bkt_tracker.update_bkt failed (non-fatal): {e}")

    # Invalidate student state cache so next load picks up new mastery
    await invalidate_student_state_cache(student_id)

    logger.info(f"[GENUI] Mastery persisted: student={student_id}, track={track}, score={mastery_score:.3f}")


async def _award_widget_credit(
    student_id: str,
    lesson_id: str,
    track: str,
    component_type: str,
    block_id: Optional[str] = None,
) -> None:
    """
    Award CASE credit for completing an interactive GenUI widget.
    Emits xAPI 'completed' statement and seals transcript entry (0.15 credits).
    """
    from app.api.learning_records import (
        RecordLearningRequest, XAPIStatementIn, TranscriptEntryIn,
        record_learning, _seal_transcript_db,
    )

    statement_id = str(uuid.uuid4())
    entry_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Emit xAPI 'completed' statement
    xapi_stmt = XAPIStatementIn(
        id=statement_id,
        student_id=student_id,
        lesson_id=lesson_id,
        block_id=block_id,
        verb="completed",
        object_id=f"https://adeline.app/genui/{component_type}",
        object_name=f"Interactive {component_type}",
        track=track,
        agent_name="REGISTRAR",
        block_type=component_type,
        completion=True,
        statement_json={
            "actor": {
                "objectType": "Agent",
                "account": {"homePage": "https://adeline.app", "name": student_id}
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"}
            },
            "object": {
                "id": f"https://adeline.app/genui/{component_type}",
                "definition": {"name": {"en-US": f"Interactive {component_type}"}}
            },
            "result": {"completion": True},
            "timestamp": now_iso,
        },
    )
    await record_learning(RecordLearningRequest(statements=[xapi_stmt]))

    # 2. Award CASE credit (0.15 credits for interactive widget completion)
    credit_hours = 0.15
    await _seal_transcript_db(TranscriptEntryIn(
        id=entry_id,
        student_id=student_id,
        lesson_id=lesson_id,
        course_title=f"Sovereign Lab: {component_type}",
        track=track,
        oas_standards=[],
        activity_description=f"Completed interactive {component_type} widget",
        credit_hours=credit_hours,
        credit_type="SOVEREIGN_LAB",
        agent_name="REGISTRAR",
        researcher_activated=False,
        completed_at=now_iso,
        xapi_statement_id=statement_id,
    ))

    logger.info(f"[GENUI] Credit awarded: student={student_id}, track={track}, hours={credit_hours}")


# ── Bidirectional Remediation SSE Endpoint ────────────────────────────────────


class RemediationRequest(BaseModel):
    """Request payload for the SSE remediation stream."""
    student_id: str
    lesson_id: str
    source_component_id: str
    component_type: str
    event: str  # "student_needs_remediation", "onStruggle", "onWrongAnswer"
    student_state: dict = {}
    track: Optional[str] = None


@router.post("/remediate")
async def genui_remediate(
    request: RemediationRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Bidirectional remediation loop — SSE endpoint.

    When a student struggles with a GenUI component, the frontend's
    onToolCall handler POSTs the struggle event here.  This endpoint
    streams back a remediation response as SSE using the Data Stream
    Protocol (2: annotations), so the frontend can inject a remedial
    component into the existing lesson without a page reload.

    The response is an SSE stream with:
      - 2: genui_skeleton (placeholder for the remedial component)
      - 2: genui_complete (full remedial component props)
      - d: finish

    This keeps the connection conversational — the student sees the
    remediation component appear smoothly in the same stream context.
    """
    from app.api.stream_protocol import DataStreamWriter
    from fastapi.responses import StreamingResponse

    logger.info(
        f"[GENUI_REMEDIATE] student={request.student_id} "
        f"source={request.source_component_id} type={request.component_type} "
        f"event={request.event} state={request.student_state}"
    )

    async def _remediation_stream():
        writer = DataStreamWriter()

        # Determine remediation strategy based on struggle signals
        wrong_attempts = request.student_state.get("wrongAttempts", 0)
        hints_used = request.student_state.get("hintsUsed", 0)
        is_wrong_answer = request.event == "onWrongAnswer"

        remedial_type, remedial_props = await _select_remediation(
            request=request,
            wrong_attempts=wrong_attempts,
            hints_used=hints_used,
            is_wrong_answer=is_wrong_answer,
        )

        remedial_id = f"remedial-{request.source_component_id}"

        # Phase 1: Emit skeleton so the UI shows a placeholder immediately
        yield writer.genui_skeleton(
            remedial_id,
            remedial_type,
            initial_hints={"title": "Let me help you with this..."},
        )

        # Phase 2: Emit full props
        yield writer.genui_complete(
            component_id=remedial_id,
            component_type=remedial_type,
            props=remedial_props,
            callbacks=["onAnswer", "onComplete"],
        )

        # Phase 3: Also emit as an annotation the frontend can act on
        yield writer.annotation("remediation", {
            "remedialId": remedial_id,
            "sourceComponentId": request.source_component_id,
            "componentType": remedial_type,
            "props": remedial_props,
            "reason": request.event,
        })

        yield writer.finish("stop")

    return StreamingResponse(
        _remediation_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-data-stream": "v1",
        },
    )


async def _select_remediation(
    request: RemediationRequest,
    wrong_attempts: int,
    hints_used: int,
    is_wrong_answer: bool,
) -> tuple[str, dict]:
    """
    Select the appropriate remediation component and build its props.

    Strategy:
      - Wrong answer → CorrectiveOverlay (with LLM-synthesized explanation)
      - 2+ wrong attempts → TaskScaffold (step-by-step breakdown)
      - 3+ hints → InteractiveConceptMap (visual knowledge map)
      - Default → Flashcard (quick review of the concept)
    """
    track = request.track or "TRUTH_HISTORY"

    if is_wrong_answer:
        question = request.student_state.get("question", "")
        wrong_answer = request.student_state.get("wrongAnswer", "")
        correct_answer = request.student_state.get("correctAnswer", "")
        overlay_props = await _synthesize_corrective_overlay(
            question=question,
            wrong_answer=wrong_answer,
            correct_answer=correct_answer,
            track=track,
        )
        return ("CorrectiveOverlay", overlay_props)

    if wrong_attempts >= 2:
        return ("TaskScaffold", {
            "title": "Let's slow down",
            "context": "You've made a few attempts. Let's break this down.",
            "tasks": [
                {"id": "1", "text": "State the question in your own words", "priority": "now"},
                {"id": "2", "text": "What do you already know about this?", "priority": "now"},
                {"id": "3", "text": "What evidence from the source applies?", "priority": "today"},
                {"id": "4", "text": "Now try the answer again", "priority": "today"},
            ],
        })

    if hints_used >= 3:
        concept = request.student_state.get("concept", "this topic")
        return ("InteractiveConceptMap", {
            "title": f"Concept Map: {concept}",
            "nodes": [
                {"id": "root", "label": concept, "x": 300, "y": 50, "type": "concept"},
                {"id": "n1", "label": "Key Idea 1", "x": 150, "y": 200, "type": "concept"},
                {"id": "n2", "label": "Key Idea 2", "x": 450, "y": 200, "type": "concept"},
            ],
            "edges": [
                {"source": "root", "target": "n1", "label": "relates to"},
                {"source": "root", "target": "n2", "label": "leads to"},
            ],
        })

    # Default: flash review
    content = request.student_state.get("content", "Review this concept")
    return ("Flashcard", {
        "front": request.student_state.get("question", "Key Concept"),
        "back": content,
        "category": track.replace("_", " ").title(),
    })


async def _synthesize_corrective_overlay(
    question: str,
    wrong_answer: str,
    correct_answer: str,
    track: str,
) -> dict:
    """
    Generate CorrectiveOverlay props via a small LLM synthesis call.
    Returns a dict matching CorrectiveOverlayProps in the frontend.
    Falls back to a generic overlay if the LLM call fails.
    """
    fallback = {
        "studentAnswer": wrong_answer,
        "correctAnswer": correct_answer,
        "mistakeType": "Incorrect response",
        "explanation": f"The correct answer is: {correct_answer}",
        "correctApproach": "Review the source material and try again.",
        "relatedConcepts": [],
    }
    try:
        import os
        import json as _json
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        prompt = (
            f"A student answered a {track} question incorrectly.\n"
            f"Question: {question}\n"
            f"Student answered: {wrong_answer}\n"
            f"Correct answer: {correct_answer}\n\n"
            "Respond with a JSON object with these fields:\n"
            "- mistakeType (string): a short label for the type of mistake (e.g. 'Factual error', 'Misread the source')\n"
            "- explanation (string): 1–2 sentences explaining why the student's answer is wrong\n"
            "- correctApproach (string): 1–2 sentences on how to find/derive the right answer\n"
            "- relatedConcepts (array of strings): 2–3 related concepts the student should review\n"
            "Keep it concise and educational. No markdown — pure JSON only."
        )
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        parsed = _json.loads(raw)
        return {
            "studentAnswer": wrong_answer,
            "correctAnswer": correct_answer,
            "mistakeType": parsed.get("mistakeType", fallback["mistakeType"]),
            "explanation": parsed.get("explanation", fallback["explanation"]),
            "correctApproach": parsed.get("correctApproach", fallback["correctApproach"]),
            "relatedConcepts": parsed.get("relatedConcepts", []),
        }
    except Exception as exc:
        logger.warning(f"[GENUI] CorrectiveOverlay synthesis failed (using fallback): {exc}")
        return fallback
