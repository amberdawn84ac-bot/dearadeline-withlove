"""Admin endpoints for maintenance tasks."""
import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/env-check")
async def check_env():
    """Check environment variables and key database state."""
    from app.config import get_db_conn

    result = {
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "database_url_set": bool(os.getenv("DATABASE_URL") or os.getenv("DIRECT_DATABASE_URL")),
        "curriculum_graph_backend": "postgres",
    }

    try:
        conn = await get_db_conn()
        result["users_total"] = await conn.fetchval('SELECT COUNT(*) FROM "User"')
        result["users_onboarded"] = await conn.fetchval(
            'SELECT COUNT(*) FROM "User" WHERE "onboardingComplete" = true'
        )
        result["oas_standards_seeded"] = await conn.fetchval('SELECT COUNT(*) FROM "OASStandard"')
        await conn.close()
    except Exception as e:
        result["db_error"] = str(e)

    return result


class SeedResponse(BaseModel):
    status: str
    curriculum_docs: int
    curriculum_concepts: int
    curriculum_track_links: int


@router.post("/seed", response_model=SeedResponse)
async def run_seeds():
    """
    Run curriculum and knowledge graph seeds.
    WARNING: This can take 2-3 minutes and uses OpenAI API credits.
    """
    try:
        # Import here to avoid loading on every request
        import sys
        from pathlib import Path
        
        # Add scripts directory to path
        scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
        sys.path.insert(0, str(scripts_dir))
        
        from seed_curriculum import main as seed_curriculum
        from seed_knowledge_graph import main as seed_kg
        
        logger.info("[Admin] Starting curriculum seed...")
        await seed_curriculum()
        
        logger.info("[Admin] Starting knowledge graph seed...")
        await seed_kg()
        
        # Get counts
        from app.config import get_db_conn
        conn = await get_db_conn()
        doc_count = await conn.fetchval('SELECT COUNT(*) FROM "HippocampusDocument"')
        concept_count = await conn.fetchval('SELECT COUNT(*) FROM "CurriculumConcept"')
        track_count = await conn.fetchval('SELECT COUNT(*) FROM "CurriculumTrackLink"')
        await conn.close()
        
        return SeedResponse(
            status="completed",
            curriculum_docs=doc_count,
            curriculum_concepts=concept_count,
            curriculum_track_links=track_count,
        )
    except Exception as e:
        logger.error(f"[Admin] Seed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
