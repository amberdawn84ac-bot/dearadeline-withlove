"""
Lesson Generation API — /lessons/*
The primary delivery endpoint. Orchestrates retrieval, Witness Protocol
verification, and Neo4j graph-linking into a structured LessonResponse.
"""
import hashlib
import json
import logging
import os
import asyncio

import openai
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.api_models import LessonRequest, LessonResponse, TRUTH_THRESHOLD, UserRole
from app.api.middleware import require_role, get_current_user_id
from app.agents.orchestrator import run_orchestrator
from app.connections.pgvector_client import hippocampus
from app.connections.knowledge_graph import get_cross_track_bias
from app.connections.redis_client import redis_client
from app.algorithms.zpd_engine import apply_cross_track_bias, AdaptiveBKTParams
from app.models.student import load_student_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lessons"])

# Per-user lesson rate limit: 20 lessons/hour
limiter = Limiter(key_func=get_remote_address)
LESSON_CACHE_TTL = 86_400  # 24 hours


def _lesson_cache_key(student_id: str, request: LessonRequest) -> str:
    """Stable cache key: student + topic (normalized) + track + grade."""
    raw = f"{student_id}:{request.topic.strip().lower()}:{request.track.value}:{request.grade_level}"
    return "lesson:" + hashlib.sha256(raw.encode()).hexdigest()[:32]

EMBED_MODEL = "text-embedding-3-small"


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def _persist_learning_records(lesson: LessonResponse) -> None:
    """
    Fire-and-forget: persist xAPI statements and CASE credit entry generated
    by the RegistrarAgent. Errors are logged but do not fail the lesson response.
    """
    from app.api.learning_records import (
        RecordLearningRequest, XAPIStatementIn, TranscriptEntryIn,
        record_learning, seal_transcript,
    )
    try:
        if lesson.xapi_statements:
            stmts = [
                XAPIStatementIn(
                    id=s.get("id", ""),
                    student_id=s.get("actor", {}).get("account", {}).get("name", ""),
                    lesson_id=lesson.lesson_id,
                    block_id=None,
                    verb=s.get("verb", {}).get("display", {}).get("en-US", "experienced"),
                    object_id=s.get("object", {}).get("id", ""),
                    object_name=s.get("object", {}).get("definition", {}).get("name", {}).get("en-US", ""),
                    track=lesson.track.value,
                    agent_name=lesson.agent_name or None,
                    block_type=s.get("context", {}).get("extensions", {}).get(
                        "https://adeline.app/xapi/ext/block_type", ""
                    ),
                    is_homestead=bool(s.get("context", {}).get("extensions", {}).get(
                        "https://adeline.app/xapi/ext/is_homestead", False
                    )),
                    statement_json=s,
                )
                for s in lesson.xapi_statements
            ]
            await record_learning(RecordLearningRequest(statements=stmts))

        if lesson.credits_awarded:
            credit = lesson.credits_awarded[0]
            await seal_transcript(TranscriptEntryIn(
                id=credit.get("id", ""),
                student_id=credit.get("student_id", ""),
                lesson_id=lesson.lesson_id,
                course_title=credit.get("course_title", lesson.title),
                track=lesson.track.value,
                oas_standards=credit.get("oas_standards", []),
                activity_description=credit.get("activity_description", ""),
                credit_hours=float(credit.get("credit_hours", 0)),
                credit_type=credit.get("credit_type", "ELECTIVE"),
                is_homestead_credit=bool(credit.get("is_homestead_credit", False)),
                agent_name=lesson.agent_name or None,
                researcher_activated=bool(credit.get("researcher_activated", False)),
            ))
    except Exception as e:
        logger.warning(f"[Lessons] Learning record persistence failed (non-fatal): {e}")


@router.post(
    "/generate",
    response_model=LessonResponse,
)
@limiter.limit("20/hour")
async def generate_lesson(
    http_request: Request,
    request: LessonRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Generate a Truth-First lesson for a student.

    Flow:
      1. Check Redis cache (topic + track + grade, 24h TTL)
      2. Embed the topic query via OpenAI
      3. Retrieve top-k chunks from Hippocampus (pgvector)
      4. Evaluate each chunk via the Witness Protocol (0.85 threshold)
      5. Graph-link to OAS Standards via Neo4j
      6. RegistrarAgent emits xAPI statements + CASE credits
      7. Fire-and-forget persistence to DB (non-blocking)
      8. Cache result + return structured LessonResponse
    """
    logger.info(
        f"[/lessons/generate] topic='{request.topic}' track={request.track.value} "
        f"grade={request.grade_level} homestead={request.is_homestead}"
    )
    try:
        # ── Cache check ───────────────────────────────────────────────────────
        cache_key = _lesson_cache_key(student_id, request)
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"[/lessons/generate] Cache HIT — {cache_key}")
                return LessonResponse.model_validate_json(cached)
        except Exception as e:
            logger.warning(f"[/lessons/generate] Cache read failed (non-fatal): {e}")

        query_embedding = await _embed(request.topic)

        # Load track interaction count for stealth assessment calibration
        student_state     = await load_student_state(student_id)
        track_mastery     = student_state.get(request.track.value)
        interaction_count = track_mastery.lesson_count

        # Cross-track mastery bias — only computed on first entry to a track
        cross_track_acknowledgment: str | None = None
        if interaction_count == 0:
            try:
                bias_value, cross_track_acknowledgment = await get_cross_track_bias(
                    student_id=student_id,
                    target_track=request.track.value,
                )
                if bias_value > 0.0:
                    biased = apply_cross_track_bias(AdaptiveBKTParams(), bias_value)
                    logger.info(
                        f"[Lessons] Cross-track bias {request.track.value}: "
                        f"pL 0.1 → {biased.pL:.3f} (bias={bias_value:.3f})"
                    )
            except Exception as e:
                logger.warning(f"[Lessons] Cross-track bias lookup failed (non-fatal): {e}")
                cross_track_acknowledgment = None

        lesson = await run_orchestrator(
            request,
            query_embedding,
            interaction_count=interaction_count,
            cross_track_acknowledgment=cross_track_acknowledgment,
        )
        # ── Cache write (non-blocking) ────────────────────────────────────────
        try:
            await redis_client.set(cache_key, lesson.model_dump_json(), ex=LESSON_CACHE_TTL)
            logger.info(f"[/lessons/generate] Cached lesson — {cache_key}")
        except Exception as e:
            logger.warning(f"[/lessons/generate] Cache write failed (non-fatal): {e}")

        # Persist learning records fire-and-forget (don't block lesson response)
        asyncio.create_task(_persist_learning_records(lesson))
        return lesson
    except openai.APIConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {e}")
    except Exception as e:
        logger.exception("[/lessons/generate] Unexpected error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def lesson_health():
    """Quick check that the lesson pipeline's dependencies are reachable."""
    doc_count = await hippocampus.count_documents()

    # Test OpenAI embedding connectivity
    openai_status = "ok"
    openai_error = None
    try:
        await _embed("health check")
    except Exception as e:
        openai_status = "error"
        openai_error = str(e)

    return {
        "status": "ok" if openai_status == "ok" else "degraded",
        "hippocampus_documents": doc_count,
        "witness_threshold": TRUTH_THRESHOLD,
        "openai_embeddings": openai_status,
        "openai_error": openai_error,
    }
