"""
Lesson Generation API — /lessons/*
The primary delivery endpoint. Orchestrates retrieval, Witness Protocol
verification, and Neo4j graph-linking into a structured LessonResponse.
"""
import json
import logging
import os
import asyncio
import time
from typing import Optional

import openai
from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from arq.connections import RedisSettings, create_pool as arq_create_pool
from arq.jobs import Job as ARQJob, JobStatus

from app.schemas.api_models import LessonRequest, LessonResponse, TRUTH_THRESHOLD, UserRole
from app.protocols.witness import get_witness_threshold
from app.api.middleware import require_role, get_current_user_id
from app.connections.pgvector_client import hippocampus
from app.connections.knowledge_graph import get_cross_track_bias
from app.models.student import load_student_state
from app.connections.canonical_store import canonical_store, canonical_slug
from app.tools.graph_query import tool_get_zpd_candidates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lessons"])


async def _get_best_canonical_for_zpd(student_id: str, track: str) -> Optional[dict]:
    """
    Find the best matching canonical lesson for a student based on ZPD candidates.

    1. Fetch ZPD candidates (concepts the student is ready to learn next).
    2. Fetch available canonicals for the track.
    3. Match ZPD concept titles to canonical topics (case-insensitive fuzzy match).
    4. Return the canonical for the highest-priority ZPD concept that has a match.

    Returns None if no match is found.
    """
    try:
        # Step 1: Fetch ZPD candidates
        zpd_candidates = await tool_get_zpd_candidates(student_id, track, limit=5)
        if not zpd_candidates:
            logger.info(f"[/lessons/zpd] No ZPD candidates found for student={student_id[:8]} track={track}")
            return None

        # Step 2: Fetch available canonicals for the track
        canonicals = await canonical_store.get_by_track(track, limit=50)
        if not canonicals:
            logger.info(f"[/lessons/zpd] No canonicals available for track={track}")
            return None

        # Step 3: Match ZPD concepts to canonicals (case-insensitive fuzzy match)
        for candidate in zpd_candidates:
            concept_title = candidate.title.lower()
            for canonical in canonicals:
                canonical_topic = canonical["topic"].lower()
                canonical_title = canonical["title"].lower()
                # Fuzzy match: concept title appears in canonical topic or title
                if concept_title in canonical_topic or concept_title in canonical_title:
                    logger.info(
                        f"[/lessons/zpd] Matched ZPD concept '{candidate.title}' to "
                        f"canonical topic '{canonical['topic']}' for student={student_id[:8]}"
                    )
                    # Fetch the full canonical record
                    slug = canonical["topic_slug"]
                    full_canonical = await canonical_store.get(slug)
                    return full_canonical

        logger.info(f"[/lessons/zpd] No canonical match found for ZPD candidates in track={track}")
        return None

    except Exception as e:
        logger.warning(f"[/lessons/zpd] ZPD auto-selection failed: {e}")
        return None

# Per-user lesson rate limit: 20 lessons/hour
limiter = Limiter(key_func=get_remote_address)

EMBED_MODEL = "text-embedding-3-small"


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def _get_arq_redis_pool():
    """Create a short-lived ARQ Redis pool for enqueue/status operations."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if redis_url.startswith("https://") or redis_url.startswith("http://"):
        raise ValueError(
            f"REDIS_URL must be a redis:// TCP DSN for ARQ, got: {redis_url}"
        )
    return await arq_create_pool(RedisSettings.from_dsn(redis_url))


async def _enqueue_lesson_job(lesson_request_dict: dict, student_id: str):
    """Enqueue a lesson generation job and return the ARQ Job object."""
    pool = await _get_arq_redis_pool()
    job = await pool.enqueue_job(
        "generate_lesson_job",
        lesson_request_dict,
        student_id,
    )
    await pool.aclose()
    return job


def _get_arq_job(job_id: str, pool) -> ARQJob:
    """Return an ARQ Job handle for status checking."""
    return ARQJob(job_id, pool)


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
    status_code=202,
)
@limiter.limit("20/hour")
async def generate_lesson(
    request: Request,
    lesson_request: LessonRequest,
    student_id: str = Depends(get_current_user_id),
):
    """
    Enqueue a lesson generation job and return immediately.

    The full orchestration pipeline (embed → canonical check → agent → registrar)
    runs in an ARQ background worker. Poll GET /lesson/status/{job_id} for the result.
    """
    job = await _enqueue_lesson_job(lesson_request.model_dump(mode="json"), student_id)
    logger.info(
        f"[/lesson/generate] Enqueued job={job.job_id} "
        f"topic='{lesson_request.topic}' track={lesson_request.track.value}"
    )
    return {"job_id": job.job_id, "status": "queued"}


@router.get("/status/{job_id}")
async def get_lesson_status(
    job_id: str,
    student_id: str = Depends(get_current_user_id),
):
    """
    Poll for lesson generation status.

    Returns:
      { status: "queued" }               — job is waiting
      { status: "running" }              — job is executing
      { status: "done", result: {...} }  — lesson ready
      { status: "failed", error: "..." } — generation failed
    """
    pool = None
    try:
        pool = await _get_arq_redis_pool()
        job = _get_arq_job(job_id, pool)
        status = await job.status()

        if status == JobStatus.complete:
            result = await job.result(timeout=0)
            return {"status": "done", "result": result}
        elif status in (JobStatus.deferred, JobStatus.queued):
            return {"status": "queued"}
        elif status == JobStatus.in_progress:
            return {"status": "running"}
        elif status == JobStatus.not_found:
            return {"status": "not_found"}
        else:
            return {"status": "unknown", "detail": str(status)}

    except Exception as e:
        logger.error(f"[/lesson/status] Error checking job {job_id}: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        if pool is not None:
            await pool.aclose()


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
