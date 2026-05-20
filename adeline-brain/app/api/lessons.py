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


async def _get_best_canonical_for_zpd(student_id: str, track: str) -> Optional[tuple[dict, str]]:
    """
    Find the best canonical lesson for a student using BKT-scored ZPD candidates.

    Returns (canonical_dict, zpd_concept_title) or None.

    Replaces the old fragile substring match with a priority-ranked approach:
    1. Fetch BKT-scored ZPD candidates (sorted by compute_priority score)
    2. For the top candidate, inject its title as the lesson topic
    3. Check canonical store for an exact slug match
    4. If no canonical exists, return (None, top_concept_title) so caller
       can use the ZPD concept as the lesson topic for full generation
    """
    try:
        zpd_candidates = await tool_get_zpd_candidates(student_id, track, limit=5)
        if not zpd_candidates:
            logger.info(f"[/lessons/zpd] No ZPD candidates for student={student_id[:8]} track={track}")
            return None

        # Candidates are already sorted by BKT priority score (highest first)
        for candidate in zpd_candidates:
            logger.info(
                f"[/lessons/zpd] Trying ZPD candidate '{candidate.title}' "
                f"priority={candidate.priority:.3f} mastery={candidate.current_mastery:.3f}"
            )
            # Try exact slug match in canonical store
            try:
                from app.connections.canonical_store import canonical_slug
                slug = canonical_slug(candidate.title, track)
                canonical = await canonical_store.get(slug)
                if canonical:
                    logger.info(
                        f"[/lessons/zpd] Canonical HIT for ZPD concept '{candidate.title}'"
                    )
                    return canonical, candidate.title
            except Exception:
                pass

        # No canonical found — return top candidate's title so caller can generate fresh
        top = zpd_candidates[0]
        logger.info(
            f"[/lessons/zpd] No canonical match — returning ZPD topic '{top.title}' "
            f"for fresh generation (priority={top.priority:.3f})"
        )
        return None, top.title

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
