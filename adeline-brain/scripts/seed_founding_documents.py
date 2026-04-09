"""
seed_founding_documents.py — Seed U.S. Founding Documents

Seeds Declaration of Independence, Constitution, and Bill of Rights
into Hippocampus for Truth-Based History track.

Usage:
    python scripts/seed_founding_documents.py
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
log = logging.getLogger("seed_founding")

SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "seeds" / "founding_documents.json"


async def embed_text(text: str) -> list[float]:
    """Generate embedding using OpenAI."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return resp.data[0].embedding


async def seed_document_chunk(
    title: str,
    section: str,
    text: str,
    track: str,
    citation_author: str,
    citation_year: int,
    source_url: str,
    archive: str
) -> bool:
    """Seed a single document chunk to Hippocampus."""
    try:
        # Build full chunk with context
        chunk = f"{title}\n{section}\n\n{text}"
        
        log.info(f"  Embedding {section}...")
        embedding = await embed_text(chunk)
        
        # Connect to database
        conn = await get_db_conn()
        
        # Check if already exists
        existing = await conn.fetchrow(
            'SELECT id FROM "HippocampusDocument" WHERE "sourceUrl" = $1 AND chunk LIKE $2',
            source_url,
            f"%{section}%"
        )
        
        if existing:
            log.info(f"    [skip] Already seeded: {section}")
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
            f"{title} - {section}",
            source_url,
            "PRIMARY_SOURCE",
            track,
            chunk,
            embedding,
            citation_author,
            citation_year,
            archive
        )
        
        await conn.close()
        
        doc_id = result['id']
        log.info(f"    ✓ Seeded {section} → {doc_id}")
        return True
        
    except Exception as e:
        log.error(f"    ✗ Error seeding {section}: {e}")
        return False


async def seed_all_documents():
    """Seed all founding documents from JSON file."""
    
    if not SEED_FILE.exists():
        log.error(f"Seed file not found: {SEED_FILE}")
        return
    
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_seeded = 0
    total_attempted = 0
    
    for doc_key, doc_data in data.items():
        log.info(f"\n{'='*60}")
        log.info(f"Seeding {doc_data['title']}...")
        log.info(f"{'='*60}")
        
        for chunk in doc_data['chunks']:
            total_attempted += 1
            success = await seed_document_chunk(
                title=doc_data['title'],
                section=chunk['section'],
                text=chunk['text'],
                track=doc_data['track'],
                citation_author=doc_data['citation_author'],
                citation_year=doc_data['citation_year'],
                source_url=doc_data['source_url'],
                archive=doc_data['archive']
            )
            if success:
                total_seeded += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.3)
    
    log.info(f"\n{'='*60}")
    log.info(f"✓ Seeded {total_seeded}/{total_attempted} document chunks")
    log.info(f"{'='*60}")


async def main():
    await seed_all_documents()


if __name__ == "__main__":
    asyncio.run(main())
