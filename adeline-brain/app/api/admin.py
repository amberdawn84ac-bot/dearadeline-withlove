"""Admin endpoints for maintenance tasks."""
import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/env-check")
async def check_env():
    """Check if required environment variables are set."""
    return {
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "database_url_set": bool(os.getenv("DATABASE_URL") or os.getenv("DIRECT_DATABASE_URL")),
        "neo4j_uri_set": bool(os.getenv("NEO4J_URI")),
        "neo4j_password_set": bool(os.getenv("NEO4J_PASSWORD")),
    }


class SeedResponse(BaseModel):
    status: str
    curriculum_docs: int
    neo4j_concepts: int
    neo4j_tracks: int


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
        from app.connections.neo4j_client import neo4j_client
        
        conn = await get_db_conn()
        doc_count = await conn.fetchval('SELECT COUNT(*) FROM "HippocampusDocument"')
        await conn.close()
        
        concept_count = 0
        track_count = 0
        if neo4j_client.driver:
            async with neo4j_client.driver.session() as session:
                result = await session.run("MATCH (c:Concept) RETURN count(c) as count")
                record = await result.single()
                concept_count = record["count"] if record else 0
                
                result = await session.run("MATCH (t:Track) RETURN count(t) as count")
                record = await result.single()
                track_count = record["count"] if record else 0
        
        return SeedResponse(
            status="completed",
            curriculum_docs=doc_count,
            neo4j_concepts=concept_count,
            neo4j_tracks=track_count,
        )
    except Exception as e:
        logger.error(f"[Admin] Seed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
