"""
seed_key_passages.py — Seed Essential Bible Passages via Sefaria API

Seeds foundational Bible passages for immediate Hippocampus availability.
Uses Sefaria API for Hebrew + English text, prioritizing Everett Fox when available.

Priority passages:
- Isaiah 43:1 (Fear not, I have redeemed you)
- Deuteronomy 6:4-9 (Shema - Hear O Israel)
- Proverbs 3:1-6 (Trust in the LORD)
- Psalm 23 (The LORD is my shepherd)
- Genesis 1:1-31 (Creation account)
- John 3:16-17 (For God so loved the world)
- Romans 8:28-39 (Nothing can separate us)
- Philippians 4:4-13 (Rejoice in the Lord)

Usage:
    python scripts/seed_key_passages.py
    python scripts/seed_key_passages.py --passage "Isaiah 43:1"
"""
import asyncio
import argparse
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

from app.services.sefaria import fetch_biblical_text, normalize_reference
from app.config import get_db_conn
import openai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_passages")

# ── Key Passages to Seed ──────────────────────────────────────────────────────

KEY_PASSAGES = {
    "DISCIPLESHIP": [
        {
            "ref": "Isaiah 43:1",
            "title": "Fear Not, I Have Redeemed You",
            "notes": "גָּאַלְתִּיךָ (ga'altikha) - 'I have redeemed you' - kinsman-redeemer language",
        },
        {
            "ref": "Deuteronomy 6:4-9",
            "title": "The Shema - Hear O Israel",
            "notes": "שְׁמַע יִשְׂרָאֵל (Shema Yisrael) - Central confession of Jewish faith",
        },
        {
            "ref": "Proverbs 3:1-6",
            "title": "Trust in the LORD with All Your Heart",
            "notes": "Wisdom literature - practical discipleship",
        },
        {
            "ref": "Psalm 23",
            "title": "The LORD is My Shepherd",
            "notes": "David's psalm of trust and provision",
        },
        {
            "ref": "Philippians 4:4-13",
            "title": "Rejoice in the Lord Always",
            "notes": "Paul's letter on contentment and God's provision",
        },
        {
            "ref": "Romans 8:28-39",
            "title": "Nothing Can Separate Us from God's Love",
            "notes": "Paul's declaration of God's sovereign love",
        },
        {
            "ref": "Matthew 5:1-12",
            "title": "The Beatitudes",
            "notes": "Jesus' Sermon on the Mount - Kingdom values",
        },
        {
            "ref": "John 3:16-17",
            "title": "For God So Loved the World",
            "notes": "Gospel in miniature - God's redemptive plan",
        },
    ],
    "TRUTH_HISTORY": [
        {
            "ref": "Genesis 1:1-31",
            "title": "Creation Account - Day by Day",
            "notes": "Foundation of biblical worldview - God as Creator",
        },
        {
            "ref": "Genesis 2:1-25",
            "title": "Garden of Eden and First Man",
            "notes": "Human origins and God's design for humanity",
        },
        {
            "ref": "Exodus 20:1-17",
            "title": "The Ten Commandments",
            "notes": "Moral law given at Sinai - foundation of Western law",
        },
        {
            "ref": "Joshua 1:1-9",
            "title": "Be Strong and Courageous",
            "notes": "Leadership transition from Moses to Joshua",
        },
    ],
    "ENGLISH_LITERATURE": [
        {
            "ref": "Psalm 1",
            "title": "Blessed is the Man Who Walks Not in the Counsel of the Wicked",
            "notes": "Hebrew poetry - parallelism and imagery",
        },
        {
            "ref": "Psalm 19",
            "title": "The Heavens Declare the Glory of God",
            "notes": "Creation psalm - general and special revelation",
        },
        {
            "ref": "Song of Solomon 2:1-17",
            "title": "I Am the Rose of Sharon",
            "notes": "Love poetry - metaphor and allegory",
        },
        {
            "ref": "Ecclesiastes 3:1-8",
            "title": "A Time for Everything",
            "notes": "Wisdom literature - poetic reflection on life's seasons",
        },
    ],
}


async def embed_text(text: str) -> list[float]:
    """Generate embedding using OpenAI."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return resp.data[0].embedding


async def seed_passage(ref: str, title: str, notes: str, track: str) -> bool:
    """
    Seed a single Bible passage to Hippocampus.
    
    Returns True if successful, False otherwise.
    """
    try:
        # Normalize reference for Sefaria API
        normalized_ref = normalize_reference(ref)
        
        log.info(f"[{track}] Fetching {ref} from Sefaria...")
        
        # Fetch from Sefaria
        sefaria_data = await fetch_biblical_text(normalized_ref)
        
        if not sefaria_data:
            log.error(f"  ✗ Failed to fetch {ref} from Sefaria")
            return False
        
        # Build full chunk with context
        chunk = f"{title}\n{ref}\n\n"
        
        if notes:
            chunk += f"Context: {notes}\n\n"
        
        if sefaria_data['hebrew']:
            chunk += f"Hebrew:\n{sefaria_data['hebrew']}\n\n"
        
        chunk += f"English ({sefaria_data['version_title']}):\n{sefaria_data['english']}"
        
        # Generate embedding
        log.info(f"  Embedding {ref}...")
        embedding = await embed_text(chunk)
        
        # Connect to database
        conn = await get_db_conn()
        
        # Check if already exists
        existing = await conn.fetchrow(
            'SELECT id FROM "HippocampusDocument" WHERE "sourceUrl" = $1 AND track = $2',
            sefaria_data['url'],
            track
        )
        
        if existing:
            log.info(f"  [skip] Already seeded: {ref}")
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
            f"{ref} - {title}",
            sefaria_data['url'],
            "SEFARIA_TEXT",
            track,
            chunk,
            embedding,
            "Everett Fox (Translator)" if sefaria_data['is_fox'] else "Sefaria.org",
            1995 if sefaria_data['is_fox'] else None,
            "Sefaria / Schocken Books" if sefaria_data['is_fox'] else "Sefaria.org",
        )
        
        await conn.close()
        
        doc_id = result['id']
        fox_indicator = "🦊" if sefaria_data['is_fox'] else ""
        log.info(f"  ✓ Seeded {ref} {fox_indicator} → {doc_id}")
        return True
        
    except Exception as e:
        log.error(f"  ✗ Error seeding {ref}: {e}")
        return False


async def seed_all_passages():
    """Seed all key passages across all tracks."""
    total_seeded = 0
    total_attempted = 0
    
    for track, passages in KEY_PASSAGES.items():
        log.info(f"\n{'='*60}")
        log.info(f"Seeding {track} passages...")
        log.info(f"{'='*60}")
        
        for passage in passages:
            total_attempted += 1
            success = await seed_passage(
                ref=passage["ref"],
                title=passage["title"],
                notes=passage.get("notes", ""),
                track=track
            )
            if success:
                total_seeded += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
    
    log.info(f"\n{'='*60}")
    log.info(f"✓ Seeded {total_seeded}/{total_attempted} passages")
    log.info(f"{'='*60}")


async def seed_single_passage(ref: str, track: str = "DISCIPLESHIP"):
    """Seed a single passage by reference."""
    log.info(f"Seeding single passage: {ref} ({track})")
    
    success = await seed_passage(
        ref=ref,
        title=ref,
        notes="",
        track=track
    )
    
    if success:
        log.info(f"✓ Successfully seeded {ref}")
    else:
        log.error(f"✗ Failed to seed {ref}")


async def main():
    parser = argparse.ArgumentParser(description="Seed key Bible passages via Sefaria API")
    parser.add_argument("--passage", help="Single passage to seed (e.g., 'Isaiah 43:1')")
    parser.add_argument("--track", default="DISCIPLESHIP", help="Track for single passage")
    
    args = parser.parse_args()
    
    if args.passage:
        await seed_single_passage(args.passage, args.track)
    else:
        await seed_all_passages()


if __name__ == "__main__":
    asyncio.run(main())
