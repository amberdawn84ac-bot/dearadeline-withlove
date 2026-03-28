"""
Lesson Generation API — /lessons/*
The primary delivery endpoint. Orchestrates retrieval, Witness Protocol
verification, and Neo4j graph-linking into a structured LessonResponse.
"""
import logging
import os

import openai
from fastapi import APIRouter, HTTPException, Depends

from app.schemas.api_models import LessonRequest, LessonResponse, TRUTH_THRESHOLD, UserRole
from app.api.middleware import require_role
from app.agents.orchestrator import run_orchestrator
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lessons"])

EMBED_MODEL = "text-embedding-3-small"


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


@router.post(
    "/generate",
    response_model=LessonResponse,
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.ADMIN))],
)
async def generate_lesson(request: LessonRequest):
    """
    Generate a Truth-First lesson for a student.

    Flow:
      1. Embed the topic query via OpenAI
      2. Retrieve top-k chunks from Hippocampus (pgvector)
      3. Evaluate each chunk via the Witness Protocol (0.85 threshold)
      4. Graph-link to OAS Standards via Neo4j
      5. Return structured LessonBlocks with verdicts and citations
    """
    logger.info(
        f"[/lessons/generate] topic='{request.topic}' track={request.track.value} "
        f"grade={request.grade_level} homestead={request.is_homestead}"
    )
    try:
        query_embedding = await _embed(request.topic)
        lesson = await run_orchestrator(request, query_embedding)
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
    return {
        "status": "ok",
        "hippocampus_documents": doc_count,
        "witness_threshold": TRUTH_THRESHOLD,
    }
