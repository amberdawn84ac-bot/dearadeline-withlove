"""
seed_creation_science.py — Seed Creation Science Experiments

Seeds hands-on science experiments with biblical worldview connections
into Hippocampus for Creation Science track.

Usage:
    python scripts/seed_creation_science.py
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.config import get_db_conn
import openai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_science")

SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "seeds" / "creation_science_experiments.json"


async def embed_text(text: str) -> list[float]:
    """Generate embedding using OpenAI."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return resp.data[0].embedding


async def seed_experiment(
    title: str,
    experiment_data: dict,
    track: str,
    citation_author: str,
    citation_year: int,
    source_url: str,
    archive: str,
    scripture_connection: str
) -> bool:
    """Seed a single experiment to Hippocampus."""
    try:
        # Build full chunk with all experiment details
        chunk = f"{title}\n\n"
        chunk += f"Scripture Connection: {scripture_connection}\n\n"
        chunk += f"Objective: {experiment_data['objective']}\n\n"
        
        chunk += "Materials:\n"
        for material in experiment_data['materials']:
            chunk += f"- {material}\n"
        chunk += "\n"
        
        chunk += "Procedure:\n"
        for i, step in enumerate(experiment_data['procedure'], 1):
            chunk += f"{i}. {step}\n"
        chunk += "\n"
        
        chunk += f"Observations: {experiment_data['observations']}\n\n"
        chunk += f"Biblical Worldview: {experiment_data['biblical_worldview']}"
        
        log.info(f"  Embedding {title}...")
        embedding = await embed_text(chunk)
        
        # Connect to database
        conn = await get_db_conn()
        
        # Check if already exists
        existing = await conn.fetchrow(
            'SELECT id FROM "HippocampusDocument" WHERE "sourceUrl" = $1',
            source_url
        )
        
        if existing:
            log.info(f"    [skip] Already seeded: {title}")
            await conn.close()
            return True
        
        # Insert new document
        result = await conn.fetchrow(
            '''
            INSERT INTO "HippocampusDocument" (
                "sourceTitle", "sourceUrl", "sourceType", track,
                chunk, embedding, "citationAuthor", "citationYear",
                "citationArchiveName", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            RETURNING id
            ''',
            title,
            source_url,
            "LAB_EXPERIMENT",
            track,
            chunk,
            embedding,
            citation_author,
            citation_year,
            archive
        )
        
        await conn.close()
        
        doc_id = result['id']
        log.info(f"    ✓ Seeded {title} → {doc_id}")
        return True
        
    except Exception as e:
        log.error(f"    ✗ Error seeding {title}: {e}")
        return False


async def seed_all_experiments():
    """Seed all creation science experiments from JSON file."""
    
    if not SEED_FILE.exists():
        log.error(f"Seed file not found: {SEED_FILE}")
        return
    
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_seeded = 0
    total_attempted = 0
    
    log.info(f"\n{'='*60}")
    log.info(f"Seeding Creation Science Experiments...")
    log.info(f"{'='*60}")
    
    for exp_key, exp_data in data.items():
        total_attempted += 1
        success = await seed_experiment(
            title=exp_data['title'],
            experiment_data=exp_data['experiment'],
            track=exp_data['track'],
            citation_author=exp_data['citation_author'],
            citation_year=exp_data['citation_year'],
            source_url=exp_data['source_url'],
            archive=exp_data['archive'],
            scripture_connection=exp_data['scripture_connection']
        )
        if success:
            total_seeded += 1
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.3)
    
    log.info(f"\n{'='*60}")
    log.info(f"✓ Seeded {total_seeded}/{total_attempted} experiments")
    log.info(f"{'='*60}")


async def main():
    await seed_all_experiments()


if __name__ == "__main__":
    asyncio.run(main())
