"""Legacy lesson namespace containing diagnostics only.

No endpoint in this router authors or delivers a learner lesson. Production
authoring is exclusively ``POST /experience/build``.
"""
import logging
import os

import openai
from fastapi import APIRouter
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.protocols.witness import get_witness_threshold
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson", tags=["lessons"])


limiter = Limiter(key_func=get_remote_address)

EMBED_MODEL = "text-embedding-3-small"


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


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


@router.get("/health/oas")
async def oas_health():
    """Check Postgres OAS standards count for lesson-generation readiness."""
    from app.config import get_db_conn
    
    try:
        conn = await get_db_conn()
        count = await conn.fetchval('SELECT COUNT(*) FROM "OASStandard"')
        
        expected = 3043
        minimum = 3000
        
        track_result = await conn.fetch(
            'SELECT track, COUNT(*) AS count FROM "OASStandard" GROUP BY track ORDER BY track'
        )
        track_distribution = {record["track"]: record["count"] for record in track_result}
        await conn.close()
        
        return {
            "status": "ok" if count >= minimum else "degraded",
            "oas_standard_count": count,
            "expected_count": expected,
            "minimum_acceptable": minimum,
            "track_distribution": track_distribution,
            "message": f"{'✅' if count >= minimum else '❌'} {count}/{expected} OAS standards loaded"
        }
    except Exception as e:
        logger.error(f"[/health/oas] Failed to check OAS standards: {e}")
        return {
            "status": "error",
            "oas_standard_count": 0,
            "expected_count": 3043,
            "minimum_acceptable": 3000,
            "track_distribution": {},
            "error": str(e),
            "message": f"❌ Failed to check OAS standards: {e}"
        }
