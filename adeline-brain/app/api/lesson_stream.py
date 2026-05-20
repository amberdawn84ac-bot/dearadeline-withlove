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

Canonical Persistence:
  - Pre-generation cache check: Instant load from PostgreSQL/Redis if lesson exists
  - Post-generation background save: New lessons persisted via BackgroundTask
    without blocking the real-time stream

Background Tasks:
  - RegistrarAgent (xAPI + CASE credits) runs after stream closes
  - CanonicalStore saves lesson to DB/Redis for future cache hits
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

from app.schemas.api_models import LessonRequest, LessonResponse, LessonBlockResponse, Track
from app.api.middleware import get_current_user_id
from app.models.student import load_student_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lesson-stream"])
limiter = Limiter(key_func=get_remote_address)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ── AdaptationRequest builder — fetches all personalization signals in parallel ──

async def _fetch_stream_student_profile(student_id: str) -> dict:
    """Fetch interests and learningStyle from the User table."""
    from app.config import get_db_conn
    try:
        conn = await get_db_conn()
        row = await conn.fetchrow(
            'SELECT "interests", "learningStyle" FROM "User" WHERE "id" = $1',
            student_id,
        )
        await conn.close()
        if row:
            return {
                "interests": list(row["interests"]) if row["interests"] else [],
                "learning_style": row["learningStyle"] or "text",
            }
    except Exception as e:
        logger.warning(f"[LessonStream] Profile fetch failed (non-fatal): {e}")
    return {"interests": [], "learning_style": "text"}


async def _fetch_sm2_quality_scores(student_id: str, track: str, limit: int = 10) -> list[float]:
    """Fetch the most recent SM-2 lastQuality values for a student's track."""
    from app.config import get_db_conn
    try:
        conn = await get_db_conn()
        rows = await conn.fetch(
            """
            SELECT "lastQuality"
            FROM "SpacedRepetitionCard"
            WHERE "studentId" = $1 AND "track" = $2 AND "lastQuality" IS NOT NULL
            ORDER BY "lastReviewedAt" DESC
            LIMIT $3
            """,
            student_id, track, limit,
        )
        await conn.close()
        return [float(r["lastQuality"]) for r in rows]
    except Exception as e:
        logger.warning(f"[LessonStream] SM-2 scores fetch failed (non-fatal): {e}")
    return []


async def _fetch_last_lesson_date(student_id: str, track: str):
    """Fetch the most recent completedAt for decay calculation."""
    from app.config import get_db_conn
    from datetime import timezone as _tz
    try:
        conn = await get_db_conn()
        val = await conn.fetchval(
            'SELECT MAX("completedAt") FROM "TranscriptEntry" WHERE "studentId" = $1 AND "track" = $2',
            student_id, track,
        )
        await conn.close()
        if val:
            return val if val.tzinfo else val.replace(tzinfo=_tz.utc)
    except Exception as e:
        logger.warning(f"[LessonStream] Last-lesson-date fetch failed (non-fatal): {e}")
    return None


async def _fetch_concept_proficiency_map(student_id: str, track: str) -> dict[str, float]:
    """Fetch per-concept masteryLevel from SpacedRepetitionCard for the track."""
    from app.config import get_db_conn
    try:
        conn = await get_db_conn()
        rows = await conn.fetch(
            """
            SELECT "conceptId", "conceptName", "masteryLevel"
            FROM "SpacedRepetitionCard"
            WHERE "studentId" = $1 AND "track" = $2
            """,
            student_id, track,
        )
        await conn.close()
        result: dict[str, float] = {}
        for r in rows:
            key = r["conceptId"] or r["conceptName"]
            result[key] = float(r["masteryLevel"] or 0.0)
        return result
    except Exception as e:
        logger.warning(f"[LessonStream] Proficiency map fetch failed (non-fatal): {e}")
    return {}


async def _build_adaptation_request(
    student_id: str,
    request: LessonRequest,
    mastery_score: float,
    interaction_count: int,
) -> "AdaptationRequest":
    """
    Build a fully-populated AdaptationRequest from all personalization signals.

    Fetches in parallel: student profile (interests + modality), SM-2 quality
    history, last lesson date (for decay), per-concept proficiency map,
    cross-track knowledge bias, and ZPD priority for the specific topic.

    Every fetch is non-fatal — defaults keep the adapter functional if any
    individual source is unavailable.
    """
    import asyncio as _asyncio
    from app.agents.adapter import AdaptationRequest
    from app.algorithms.zpd_engine import apply_decay
    from app.connections.knowledge_graph import get_cross_track_bias
    from app.tools.graph_query import tool_get_zpd_candidates

    (
        profile,
        sm2_scores,
        last_date,
        proficiency_map,
        cross_bias_result,
        zpd_candidates,
    ) = await _asyncio.gather(
        _fetch_stream_student_profile(student_id),
        _fetch_sm2_quality_scores(student_id, request.track.value),
        _fetch_last_lesson_date(student_id, request.track.value),
        _fetch_concept_proficiency_map(student_id, request.track.value),
        get_cross_track_bias(student_id, request.track.value),
        tool_get_zpd_candidates(student_id, request.track.value, limit=5),
        return_exceptions=True,
    )

    # Interests + preferred modality
    interests: list[str] = []
    ls_raw = "text"
    if isinstance(profile, dict):
        interests = profile.get("interests", [])
        ls_raw = (profile.get("learning_style") or "text").lower()
    preferred_modality = (
        "visual" if ls_raw == "visual"
        else "kinesthetic" if ls_raw == "kinesthetic"
        else "text"
    )

    # Recent SM-2 quality history
    recent_quiz_scores = sm2_scores if isinstance(sm2_scores, list) else []

    # Decay-adjusted mastery
    last_practiced = last_date if not isinstance(last_date, Exception) else None
    decay_adjusted = apply_decay(mastery_score, last_practiced) if last_practiced else mastery_score

    # Cross-track bias
    cross_track_bias = 0.0
    if isinstance(cross_bias_result, tuple) and len(cross_bias_result) == 2:
        raw_bias = cross_bias_result[0]
        cross_track_bias = float(raw_bias) if raw_bias is not None else 0.0

    # ZPD priority for this specific topic (match by title substring; fall back to top candidate)
    priority_score = 0.5
    if isinstance(zpd_candidates, list) and zpd_candidates:
        topic_lower = request.topic.lower()
        for c in zpd_candidates:
            if topic_lower in c.title.lower() or c.title.lower() in topic_lower:
                priority_score = c.priority
                break
        else:
            priority_score = zpd_candidates[0].priority

    # Per-concept proficiency map
    proficiency = proficiency_map if isinstance(proficiency_map, dict) else {}

    logger.info(
        f"[LessonStream] AdaptationRequest built — "
        f"grade={request.grade_level} track={request.track.value} "
        f"bkt_pL={mastery_score:.3f} decay={decay_adjusted:.3f} "
        f"priority={priority_score:.3f} cross_bias={cross_track_bias:.3f} "
        f"modality={preferred_modality} interests={interests[:2]} "
        f"sm2_scores={len(recent_quiz_scores)} concepts={len(proficiency)}"
    )

    return AdaptationRequest(
        grade_level=request.grade_level,
        track=request.track.value,
        interests=interests,
        interaction_count=interaction_count,
        recent_quiz_scores=recent_quiz_scores,
        preferred_modality=preferred_modality,
        bkt_pL=mastery_score,
        priority_score=priority_score,
        decay_adjusted_mastery=decay_adjusted,
        cross_track_bias=cross_track_bias,
        proficiency_map=proficiency,
    )


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
    from app.agents.adapter import adapt_canonical_for_student

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
        # Sum lesson counts across all tracks — StudentState has no total_interactions attr
        interaction_count = sum(tm.lesson_count for tm in student_state.tracks.values()) or 10
    except Exception as e:
        logger.warning(f"[LessonStream] Student state load failed (non-fatal): {e}")

    # Build a fully-populated AdaptationRequest from all personalization signals
    # (interests, SM-2 scores, decay, cross-track bias, ZPD priority, proficiency map)
    adaptation_req = await _build_adaptation_request(
        student_id, request, mastery_score, interaction_count
    )

    # ── Phase 1: Canonical check ──────────────────────────────────────────────
    yield _sse({"type": "status", "message": "Checking curated lesson library..."})
    slug = canonical_slug(request.topic, request.track.value)
    logger.info(f"[LessonStream] topic='{request.topic}' track={request.track.value} force_regenerate={request.force_regenerate} slug={slug}")

    if request.force_regenerate:
        yield _sse({"type": "status", "message": "Regenerating lesson — clearing cached version..."})
        try:
            await canonical_store.archive(slug, reason="force_regenerate")
            logger.info(f"[LessonStream] force_regenerate: archived canonical slug={slug}")
        except Exception as e:
            logger.warning(f"[LessonStream] force_regenerate: archive failed (non-fatal): {e}")

    try:
        canonical = None if request.force_regenerate else await canonical_store.get(slug)
        # Redis payload uses snake_case key; DB payload also uses snake_case via _db_get
        is_pending = canonical.get("pending_approval") or canonical.get("pendingApproval") if canonical else False
        if canonical and not is_pending:
            # canonical_store returns "blocks" (not "blocksJson")
            blocks_data = canonical.get("blocks") or []
            if isinstance(blocks_data, str):
                blocks_data = json.loads(blocks_data)
            
            yield _sse({"type": "status", "message": "Personalizing lesson for you..."})
            canonical_dummy = {"topic": request.topic, "blocks": blocks_data}
            blocks_data = await adapt_canonical_for_student(canonical_dummy, adaptation_req)
            
            for block in blocks_data:
                yield _sse({"type": "block", "block": block})
                tool_event = _from_block_tool_call(block, lesson_id, request.track.value)
                if tool_event:
                    yield tool_event
            yield _sse({
                "type": "done",
                "lesson_id": lesson_id,
                "title": canonical.get("title", request.topic),
                "from_canonical": True,
            })
            return
    except Exception as e:
        logger.warning(f"[LessonStream] Canonical check failed (non-fatal): {e}")

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
    # ── Phase 2: Personalize via Adapter ──────────────────────────────────────
    if state["blocks"]:
        yield _sse({"type": "status", "message": "Personalizing lesson for you..."})
        canonical_dummy = {"topic": request.topic, "blocks": state["blocks"]}
        state["blocks"] = await adapt_canonical_for_student(canonical_dummy, adaptation_req)

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
        # Pass state for the background canonical save task
        "_state_for_canonical": {
            "slug": slug,
            "topic": request.topic,
            "track": request.track.value,
            "title": title,
            "blocks": state.get("blocks", []),
            "oas_standards": state.get("oas_standards", []),
            "researcher_activated": state.get("researcher_activated", False),
            "agent_name": state.get("agent_name", ""),
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

        # BKT + SM-2: update SpacedRepetitionCard for the primary concept studied
        try:
            from app.algorithms.bkt_tracker import update_card_after_lesson
            from app.tools.graph_query import tool_get_zpd_candidates
            zpd_candidates = await tool_get_zpd_candidates(
                student_id=request.student_id,
                track=request.track.value,
                limit=1,
            )
            if zpd_candidates:
                top = zpd_candidates[0]
                await update_card_after_lesson(
                    student_id=request.student_id,
                    concept_id=top.concept_id,
                    concept_name=top.title,
                    track=request.track.value,
                    quality=3,
                )
            else:
                # Fallback: derive concept_id from track + topic
                slug = (
                    f"{request.track.value.lower()}-"
                    f"{request.topic.lower().replace(' ', '-')[:50]}"
                )
                await update_card_after_lesson(
                    student_id=request.student_id,
                    concept_id=slug,
                    concept_name=request.topic,
                    track=request.track.value,
                    quality=3,
                )
        except Exception as bkt_err:
            logger.warning(f"[LessonStream] BKT/SM-2 update failed (non-fatal): {bkt_err}")

        # Invalidate student state cache so next plan/lesson sees fresh mastery
        try:
            from app.models.student import invalidate_student_state_cache
            await invalidate_student_state_cache(request.student_id)
        except Exception:
            pass

        logger.info(f"[LessonStream] Registrar background task complete — lesson_id={lesson_id}")
    except Exception as e:
        logger.warning(f"[LessonStream] Registrar background task failed (non-fatal): {e}")


async def _save_canonical_background(
    state_for_canonical: dict,
) -> None:
    """Background task: save generated lesson to canonical store after stream ends."""
    try:
        from app.connections.canonical_store import canonical_store

        slug = state_for_canonical.get("slug")
        if not slug:
            logger.warning("[LessonStream] Cannot save canonical: missing slug")
            return

        record = {
            "id": str(uuid.uuid4()),
            "topic": state_for_canonical.get("topic", ""),
            "track": state_for_canonical.get("track", ""),
            "title": state_for_canonical.get("title", ""),
            "blocks": state_for_canonical.get("blocks", []),
            "oas_standards": state_for_canonical.get("oas_standards", []),
            "researcher_activated": state_for_canonical.get("researcher_activated", False),
            "agent_name": state_for_canonical.get("agent_name", ""),
        }

        await canonical_store.save(slug, record, pending=False)
        logger.info(f"[LessonStream] Canonical saved — slug={slug}, topic='{record['topic']}'")
    except Exception as e:
        logger.warning(f"[LessonStream] Canonical save failed (non-fatal): {e}")


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
    as soon as each agent step completes.

    Canonical Persistence:
      - Pre-generation: Checks canonical store for existing lesson (slug = SHA256(topic:track)).
        If found, instantly streams cached blocks without running the orchestrator.
      - Post-generation: New lessons are saved to the canonical store via BackgroundTask
        after the stream completes, ensuring future requests are instant cache hits.

    Background Tasks:
      - RegistrarAgent emits xAPI statements + CASE credits
      - CanonicalStore saves lesson for future cache hits
    """
    lesson_id = str(uuid.uuid4())

    async def event_generator():
        registrar_snapshot = {}
        canonical_snapshot = {}
        async for chunk in _stream_lesson(lesson_request, student_id, lesson_id):
            yield chunk
            # Capture state from the done event for background tasks
            if '"type": "done"' in chunk:
                try:
                    payload = json.loads(chunk.replace("data: ", "").strip())
                    registrar_snapshot.update(payload.get("_state_for_registrar", {}))
                    canonical_snapshot.update(payload.get("_state_for_canonical", {}))
                except Exception as e:
                    logger.warning(f"[stream_lesson] Failed to parse done event for background tasks: {e}")

        # Run registrar synchronously after stream is fully consumed
        await _run_registrar_background(
            registrar_snapshot,
            lesson_request,
            lesson_id,
        )

        # Run canonical save synchronously after stream is fully consumed (only if not from cache)
        if canonical_snapshot and not canonical_snapshot.get("from_canonical"):
            await _save_canonical_background(
                canonical_snapshot,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
