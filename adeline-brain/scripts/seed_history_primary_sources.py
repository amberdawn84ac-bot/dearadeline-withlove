"""
seed_history_primary_sources.py — Seed Historical Primary Sources

Seeds comprehensive U.S. history primary sources across multiple eras:
- Revolutionary War (Paine, Henry, Washington, Jefferson)
- Civil War (Lincoln, Lee, Douglass)
- Native American perspectives (Chief Joseph, Tecumseh)
- Women's suffrage (Stanton, Sojourner Truth)
- Civil Rights (MLK)
- WWI, WWII, Cold War (Wilson, FDR, JFK, Reagan)
- Oklahoma/Homesteading (Land Run, Homestead Act)

Usage:
    python scripts/seed_history_primary_sources.py
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

from app.connections.pgvector_client import hippocampus
import openai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_history")

SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "seeds" / "history_primary_sources.json"


async def embed_text(text: str) -> list[float]:
    """Generate embedding using OpenAI."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return resp.data[0].embedding


async def seed_historical_document(
    doc_key: str,
    doc_data: dict
) -> bool:
    """Seed a single historical document to Hippocampus."""
    try:
        # Build full chunk with context
        chunk = f"{doc_data['title']}\n"
        chunk += f"Author: {doc_data['author']} ({doc_data['year']})\n\n"
        chunk += doc_data['text']
        
        log.info(f"  Embedding {doc_data['title']}...")
        embedding = await embed_text(chunk)
        
        # Use hippocampus.upsert_document()
        doc_id = await hippocampus.upsert_document(
            source_title=doc_data['title'],
            source_url=doc_data['source_url'],
            source_type="PRIMARY_SOURCE",
            track=doc_data['track'],
            chunk=chunk,
            embedding=embedding,
            citation_author=doc_data['author'],
            citation_year=doc_data['year'],
            citation_archive_name=doc_data['archive'],
        )
        
        log.info(f"    ✓ Seeded {doc_data['title']} → {doc_id}")
        return True
        
    except Exception as e:
        log.error(f"    ✗ Error seeding {doc_data['title']}: {e}")
        return False


async def seed_all_documents():
    """Seed all historical primary sources from JSON file."""
    # Initialize hippocampus connection
    await hippocampus.connect()
    
    if not SEED_FILE.exists():
        log.error(f"Seed file not found: {SEED_FILE}")
        return
    
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_seeded = 0
    total_attempted = 0
    
    log.info(f"\n{'='*60}")
    log.info(f"Seeding Historical Primary Sources...")
    log.info(f"{'='*60}")
    
    # Group by era for better logging
    eras = {
        "Colonial Era": ["mayflower_compact"],
        "Revolutionary War": ["revolutionary_war_common_sense", "revolutionary_war_patrick_henry", "washington_farewell_address", "jefferson_religious_freedom"],
        "Civil War": ["civil_war_emancipation_proclamation", "civil_war_gettysburg_address", "civil_war_robert_e_lee_surrender"],
        "Native American": ["native_american_chief_joseph", "native_american_tecumseh"],
        "Women's Suffrage": ["womens_suffrage_seneca_falls", "womens_suffrage_sojourner_truth"],
        "Homesteading": ["homesteading_act", "oklahoma_land_run_proclamation"],
        "WWI": ["wwi_wilson_fourteen_points"],
        "WWII & Great Depression": ["great_depression_fdr_inaugural", "wwii_fdr_day_of_infamy"],
        "Cold War": ["cold_war_jfk_inaugural", "cold_war_reagan_tear_down_wall"],
        "Civil Rights": ["civil_rights_mlk_letter_birmingham", "civil_rights_mlk_i_have_a_dream"]
    }
    
    for era_name, doc_keys in eras.items():
        log.info(f"\n--- {era_name} ---")
        for doc_key in doc_keys:
            if doc_key in data:
                total_attempted += 1
                success = await seed_historical_document(doc_key, data[doc_key])
                if success:
                    total_seeded += 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.3)
    
    log.info(f"\n{'='*60}")
    log.info(f"✓ Seeded {total_seeded}/{total_attempted} historical documents")
    log.info(f"{'='*60}")


async def main():
    await seed_all_documents()


if __name__ == "__main__":
    asyncio.run(main())
