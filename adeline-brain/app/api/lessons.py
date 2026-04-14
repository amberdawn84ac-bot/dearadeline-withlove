"""
Lesson Generation API — /lessons/*
The primary delivery endpoint. Orchestrates retrieval, Witness Protocol
verification, and Neo4j graph-linking into a structured LessonResponse.
"""
import json
import logging
import os
import asyncio

import openai
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.api_models import LessonRequest, LessonResponse, TRUTH_THRESHOLD, UserRole
from app.protocols.witness import get_witness_threshold
from app.api.middleware import require_role, get_current_user_id
from app.agents.orchestrator import run_orchestrator
from app.connections.pgvector_client import hippocampus
from app.connections.knowledge_graph import get_cross_track_bias
from app.algorithms.zpd_engine import apply_cross_track_bias, AdaptiveBKTParams
from app.models.student import load_student_state
from app.connections.canonical_store import canonical_store, canonical_slug
from app.agents.adapter import adapt_canonical_for_student, AdaptationRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lessons"])

# Per-user lesson rate limit: 20 lessons/hour
limiter = Limiter(key_func=get_remote_address)

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
    request: Request,
    lesson_request: LessonRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Generate a Truth-First lesson for a student.

    Flow:
      1. Check canonical store (topic + track) — if exists, adapt cheaply for student
      2. If no canonical: embed topic, run full orchestrator (research + generation)
      3. Save new canonical for future students
      4. Retrieve top-k chunks from Hippocampus (pgvector)
      5. Evaluate each chunk via the Witness Protocol (track-aware thresholds)
      6. Graph-link to OAS Standards via Neo4j
      7. RegistrarAgent emits xAPI statements + CASE credits
      8. Fire-and-forget persistence to DB (non-blocking)
      9. Return structured LessonResponse
    """
    lr = lesson_request  # alias for brevity
    logger.info(
        f"[/lessons/generate] topic='{lr.topic}' track={lr.track.value} "
        f"grade={lr.grade_level} homestead={lr.is_homestead}"
    )
    try:
        slug = canonical_slug(lr.topic, lr.track.value)

        # ── Phase 1: Check canonical store ───────────────────────────────────
        canonical = None
        try:
            canonical = await canonical_store.get(slug)
        except Exception as e:
            logger.warning(f"[/lessons/generate] Canonical store read failed (non-fatal): {e}")

        if canonical:
            logger.info(f"[/lessons/generate] Canonical HIT — adapting for student grade={lr.grade_level}")
            student_state = await load_student_state(student_id)
            track_mastery = student_state.get(lr.track.value)
            interaction_count = track_mastery.lesson_count if track_mastery else 10

            interests: list[str] = []
            recent_quiz_scores: list[float] = []
            try:
                from app.config import get_db_conn
                conn = await get_db_conn()
                row = await conn.fetchrow('SELECT interests FROM "User" WHERE id = $1', student_id)
                interests = row["interests"] or [] if row else []
                cards = await conn.fetch(
                    'SELECT "easeFactor" FROM "SpacedRepetitionCard" '
                    'WHERE "studentId" = $1 ORDER BY "updatedAt" DESC LIMIT 5',
                    student_id,
                )
                recent_quiz_scores = [float(r["easeFactor"]) for r in cards]
                await conn.close()
            except Exception:
                pass

            _visual_interests = {"art", "drawing", "visual", "film", "video", "photography", "design"}
            _kinesthetic_interests = {"farming", "building", "cooking", "crafting", "garden", "homestead"}
            interests_lower = {i.lower() for i in interests}
            if interests_lower & _visual_interests:
                modality = "visual"
            elif interests_lower & _kinesthetic_interests:
                modality = "kinesthetic"
            else:
                modality = "text"

            adapt_req = AdaptationRequest(
                grade_level=lr.grade_level,
                track=lr.track.value,
                interests=interests,
                interaction_count=interaction_count,
                recent_quiz_scores=recent_quiz_scores,
                preferred_modality=modality,
            )
            adapted_blocks = await adapt_canonical_for_student(canonical, adapt_req)
            from app.schemas.api_models import LessonBlockResponse
            blocks = [LessonBlockResponse(**b) for b in adapted_blocks]
            return LessonResponse(
                title=canonical["title"],
                track=lr.track,
                blocks=blocks,
                has_research_missions=any(b.get("block_type") == "RESEARCH_MISSION" for b in adapted_blocks),
                oas_standards=canonical.get("oas_standards", []),
                researcher_activated=canonical.get("researcher_activated", False),
                agent_name=canonical.get("agent_name", ""),
            )

        # ── Phase 2: Full generation (no canonical exists yet) ───────────────
        logger.info(f"[/lessons/generate] No canonical — running full orchestrator")
        query_embedding = await _embed(lr.topic)

        student_state     = await load_student_state(student_id)
        track_mastery     = student_state.get(lr.track.value)
        interaction_count = track_mastery.lesson_count

        cross_track_acknowledgment: str | None = None
        if interaction_count == 0:
            try:
                bias_value, cross_track_acknowledgment = await get_cross_track_bias(
                    student_id=student_id,
                    target_track=lr.track.value,
                )
                if bias_value > 0.0:
                    biased = apply_cross_track_bias(AdaptiveBKTParams(), bias_value)
                    logger.info(
                        f"[Lessons] Cross-track bias {lr.track.value}: "
                        f"pL 0.1 → {biased.pL:.3f} (bias={bias_value:.3f})"
                    )
            except Exception as e:
                logger.warning(f"[Lessons] Cross-track bias lookup failed (non-fatal): {e}")
                cross_track_acknowledgment = None

        lesson = await run_orchestrator(
            lr,
            query_embedding,
            interaction_count=interaction_count,
            cross_track_acknowledgment=cross_track_acknowledgment,
            mastery_score=track_mastery.mastery_score,
            mastery_band=track_mastery.mastery_band.value,
        )

        # ── Phase 3: Save as canonical for future students ───────────────────
        try:
            canonical_record = {
                "id": lesson.lesson_id,
                "topic_slug": slug,
                "topic": lr.topic,
                "track": lr.track.value,
                "title": lesson.title,
                "blocks": [b.model_dump() for b in lesson.blocks],
                "oas_standards": lesson.oas_standards,
                "researcher_activated": lesson.researcher_activated,
                "agent_name": lesson.agent_name,
            }
            await canonical_store.save(slug, canonical_record)
            logger.info(f"[/lessons/generate] Saved new canonical — {slug}")
        except Exception as e:
            logger.warning(f"[/lessons/generate] Canonical save failed (non-fatal): {e}")

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
        "witness_thresholds": {
            "TRUTH_HISTORY": get_witness_threshold("TRUTH_HISTORY"),
            "JUSTICE_CHANGEMAKING": get_witness_threshold("JUSTICE_CHANGEMAKING"),
            "CREATION_SCIENCE": get_witness_threshold("CREATION_SCIENCE"),
            "DISCIPLESHIP": get_witness_threshold("DISCIPLESHIP"),
            "ENGLISH_LITERATURE": get_witness_threshold("ENGLISH_LITERATURE"),
        },
        "openai_embeddings": openai_status,
        "openai_error": openai_error,
    }
