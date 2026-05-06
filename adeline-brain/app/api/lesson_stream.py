"""
Lesson Streaming API — POST /lesson/stream

Streams lesson blocks as Server-Sent Events so the Next.js translation layer
can feed the Vercel AI SDK Data Stream Protocol to the frontend useChat hook.

SSE event shapes:
  data: {"type": "status",    "message": "..."}
  data: {"type": "block",     "block": LessonBlockResponse}
  data: {"type": "tool_call", "name": "render_quiz_widget",  "props": {...}}
  data: {"type": "tool_call", "name": "render_lab_widget",   "props": {...}}
  data: {"type": "done",      "lesson_id": "...", "title": "..."}
  data: {"type": "error",     "message": "..."}

The RegistrarAgent (xAPI + CASE credits) runs as a FastAPI BackgroundTask
after the stream closes — it never blocks the student.
"""
import json
import logging
import os
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.api_models import LessonRequest, LessonResponse, LessonBlockResponse
from app.api.middleware import get_current_user_id
from app.models.student import load_student_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lesson-stream"])
limiter = Limiter(key_func=get_remote_address)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_lesson(
    request: LessonRequest,
    student_id: str,
    lesson_id: str,
) -> AsyncGenerator[str, None]:
    """
    Core streaming generator.

    Phase 1 (sync ~1s): embed → canonical check → load student state.
    Phase 2 (streaming): run each specialist agent, yield blocks as they complete.
    Registrar is skipped here — caller runs it via BackgroundTask.
    """
    import openai
    from app.connections.pgvector_client import hippocampus
    from app.connections.canonical_store import canonical_store, canonical_slug
    from app.agents.orchestrator import (
        historian_agent, justice_agent, science_agent, literature_agent,
        practical_agent, discipleship_agent, _fetch_graph_context, _route,
        AdelineState,
    )

    yield _sse({"type": "status", "message": "Searching knowledge archive..."})

    # ── Phase 1: Embed ────────────────────────────────────────────────────────
    try:
        oai = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await oai.embeddings.create(
            model="text-embedding-3-small",
            input=request.topic,
        )
        query_embedding = resp.data[0].embedding
    except Exception as e:
        logger.error(f"[LessonStream] Embed failed: {e}")
        yield _sse({"type": "error", "message": "Failed to process topic embedding."})
        return

    # ── Phase 1: Canonical check ──────────────────────────────────────────────
    yield _sse({"type": "status", "message": "Checking curated lesson library..."})
    try:
        slug = canonical_slug(request.topic, request.track.value)
        canonical = await canonical_store.get(slug)
        if canonical and not canonical.get("pendingApproval"):
            blocks_data = canonical.get("blocksJson") or canonical.get("blocks_json") or []
            if isinstance(blocks_data, str):
                blocks_data = json.loads(blocks_data)
            for block in blocks_data:
                yield _sse({"type": "block", "block": block})
                yield _from_block_tool_call(block, lesson_id, request.track.value)
            yield _sse({
                "type": "done",
                "lesson_id": lesson_id,
                "title": canonical.get("title", request.topic),
                "from_canonical": True,
            })
            return
    except Exception as e:
        logger.warning(f"[LessonStream] Canonical check failed (non-fatal): {e}")

    # ── Phase 1: Student state ────────────────────────────────────────────────
    interaction_count = 10
    mastery_score = 0.0
    mastery_band = "NOVICE"
    cross_track_ack = None

    try:
        student_state = await load_student_state(student_id)
        track_mastery = student_state.tracks.get(request.track.value)
        if track_mastery:
            mastery_score = track_mastery.mastery_score
            mastery_band = track_mastery.mastery_band
        interaction_count = student_state.total_interactions or 10
    except Exception as e:
        logger.warning(f"[LessonStream] Student state load failed (non-fatal): {e}")

    # ── Phase 2: Build initial state ──────────────────────────────────────────
    state: AdelineState = {
        "request":               request,
        "lesson_id":             lesson_id,
        "query_embedding":       query_embedding,
        "blocks":                [],
        "oas_standards":         [],
        "has_research_missions": False,
        "researcher_activated":  False,
        "agent_name":            "",
        "xapi_statements":       [],
        "credits_awarded":       [],
        "interaction_count":     interaction_count,
        "cross_track_acknowledgment": cross_track_ack,
        "mastery_score":         mastery_score,
        "mastery_band":          mastery_band,
        "student_message":       None,
    }

    route = _route(state)
    agent_label = {
        "historian":    "Historian",
        "justice":      "Justice",
        "science":      "Science",
        "literature":   "Literature",
        "practical":    "Practical",
        "discipleship": "Discipleship",
    }.get(route, "Specialist")

    yield _sse({"type": "status", "message": f"Activating {agent_label} Agent..."})

    # ── Phase 2: Specialist agent (blocks emitted after agent returns) ────────
    try:
        if route == "historian":
            state = await historian_agent(state)
        elif route == "justice":
            state = await justice_agent(state)
        elif route == "science":
            state = await science_agent(state)
        elif route == "literature":
            state = await literature_agent(state)
        elif route == "practical":
            state = await practical_agent(state)
        else:
            state = await discipleship_agent(state)
    except Exception as e:
        logger.error(f"[LessonStream] Agent {route} failed: {e}")
        yield _sse({"type": "error", "message": f"Lesson generation failed: {e}"})
        return

    # ── Phase 2: Cross-track acknowledgment ───────────────────────────────────
    if state.get("cross_track_acknowledgment") and state["blocks"]:
        state["blocks"][0]["content"] = (
            state["cross_track_acknowledgment"] + "\n\n" + state["blocks"][0]["content"]
        )

    # ── Phase 2: Emit blocks ──────────────────────────────────────────────────
    yield _sse({"type": "status", "message": "Streaming lesson blocks..."})
    for block in state["blocks"]:
        yield _sse({"type": "block", "block": block})
        tool_event = _from_block_tool_call(block, lesson_id, request.track.value)
        if tool_event:
            yield tool_event

    # ── Phase 2: Neo4j graph context ──────────────────────────────────────────
    try:
        yield _sse({"type": "status", "message": "Linking OAS standards..."})
        state["oas_standards"] = await _fetch_graph_context(request.track.value)
    except Exception as e:
        logger.warning(f"[LessonStream] Graph context failed (non-fatal): {e}")

    title = f"{request.topic.title()} — {request.track.value.replace('_', ' ').title()}"
    yield _sse({
        "type": "done",
        "lesson_id": lesson_id,
        "title": title,
        "agent_name": state.get("agent_name", ""),
        "oas_standards": state.get("oas_standards", []),
        "researcher_activated": state.get("researcher_activated", False),
        # Pass state for the background registrar task
        "_state_for_registrar": {
            "xapi_statements": state.get("xapi_statements", []),
            "credits_awarded":  state.get("credits_awarded", []),
        },
    })


def _from_block_tool_call(block: dict, lesson_id: str, track: str) -> str | None:
    """
    For interactive block types, emit a tool_call event that the Next.js
    translation layer maps to a Vercel AI SDK tool invocation.
    """
    block_type = block.get("blockType") or block.get("block_type", "")

    if block_type == "QUIZ":
        return _sse({
            "type": "tool_call",
            "name": "render_quiz_widget",
            "props": {
                "blockId":  block.get("id", ""),
                "lessonId": lesson_id,
                "track":    track,
                "title":    block.get("title", ""),
                "content":  block.get("content", ""),
                "tags":     block.get("tags", []),
            },
        })

    if block_type == "LAB_MISSION":
        return _sse({
            "type": "tool_call",
            "name": "render_lab_widget",
            "props": {
                "blockId":   block.get("id", ""),
                "lessonId":  lesson_id,
                "track":     track,
                "title":     block.get("title", ""),
                "content":   block.get("content", ""),
                "isHomestead": block.get("homesteadEnabled", False),
            },
        })

    return None


async def _run_registrar_background(
    state_snapshot: dict,
    request: LessonRequest,
    lesson_id: str,
) -> None:
    """Background task: run RegistrarAgent + persist xAPI/credits after stream ends."""
    try:
        from app.agents.orchestrator import registrar_agent, AdelineState
        from app.api.lessons import _persist_learning_records

        dummy_state: AdelineState = {
            "request":               request,
            "lesson_id":             lesson_id,
            "query_embedding":       [],
            "blocks":                [],
            "oas_standards":         [],
            "has_research_missions": False,
            "researcher_activated":  state_snapshot.get("researcher_activated", False),
            "agent_name":            state_snapshot.get("agent_name", ""),
            "xapi_statements":       state_snapshot.get("xapi_statements", []),
            "credits_awarded":       state_snapshot.get("credits_awarded", []),
            "interaction_count":     10,
            "cross_track_acknowledgment": None,
            "mastery_score":         0.0,
            "mastery_band":          "NOVICE",
            "student_message":       None,
        }
        final_state = await registrar_agent(dummy_state)

        from app.schemas.api_models import LessonResponse, LessonBlockResponse
        lesson = LessonResponse(
            lesson_id=lesson_id,
            title="",
            track=request.track,
            blocks=[],
            has_research_missions=False,
            oas_standards=[],
            researcher_activated=final_state.get("researcher_activated", False),
            agent_name=final_state.get("agent_name", ""),
            xapi_statements=final_state.get("xapi_statements", []),
            credits_awarded=final_state.get("credits_awarded", []),
        )
        await _persist_learning_records(lesson)
        logger.info(f"[LessonStream] Registrar background task complete — lesson_id={lesson_id}")
    except Exception as e:
        logger.warning(f"[LessonStream] Registrar background task failed (non-fatal): {e}")


@router.post("/stream")
@limiter.limit("20/hour")
async def stream_lesson(
    request: Request,
    lesson_request: LessonRequest,
    background_tasks: BackgroundTasks,
    student_id: str = Depends(get_current_user_id),
):
    """
    Stream a lesson as Server-Sent Events.

    Returns immediately with a StreamingResponse. Blocks arrive as SSE events
    as soon as each agent step completes. The RegistrarAgent runs in background.
    """
    lesson_id = str(uuid.uuid4())

    async def event_generator():
        registrar_snapshot = {}
        async for chunk in _stream_lesson(lesson_request, student_id, lesson_id):
            yield chunk
            # Capture the registrar state from the done event
            if '"type": "done"' in chunk:
                try:
                    payload = json.loads(chunk.replace("data: ", "").strip())
                    registrar_snapshot.update(payload.get("_state_for_registrar", {}))
                except Exception:
                    pass

        # Schedule registrar after stream is fully consumed
        background_tasks.add_task(
            _run_registrar_background,
            registrar_snapshot,
            lesson_request,
            lesson_id,
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
