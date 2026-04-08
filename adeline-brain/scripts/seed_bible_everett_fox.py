"""
seed_bible_everett_fox.py — Seed Everett Fox Bible Translation

Seeds the Everett Fox translation of the Hebrew Bible into Hippocampus.
Chunks by chapter or narrative unit for optimal retrieval.

Usage:
    python scripts/seed_bible_everett_fox.py --book genesis
    python scripts/seed_bible_everett_fox.py --all
"""
import asyncio
import argparse
import logging
import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import openai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_bible")

# ── Config ────────────────────────────────────────────────────────────────────

_pg_password = os.getenv("POSTGRES_PASSWORD", "placeholder_password")
POSTGRES_DSN = (
    os.getenv("POSTGRES_DSN")
    or os.getenv("DIRECT_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or f"postgresql://adeline:{_pg_password}@localhost:5432/hippocampus"
).replace("postgresql://", "postgresql+asyncpg://")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

# ── Bible Book Metadata ───────────────────────────────────────────────────────

BIBLE_BOOKS = {
    # Torah (Pentateuch) - TRUTH_HISTORY
    "genesis": {
        "title": "The Book of Genesis (Everett Fox Translation)",
        "track": "TRUTH_HISTORY",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 1995,
        "source_url": "https://www.schocken.com/book/the-five-books-of-moses/",
        "archive": "Schocken Books",
    },
    "exodus": {
        "title": "The Book of Exodus (Everett Fox Translation)",
        "track": "TRUTH_HISTORY",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 1995,
        "source_url": "https://www.schocken.com/book/the-five-books-of-moses/",
        "archive": "Schocken Books",
    },
    "leviticus": {
        "title": "The Book of Leviticus (Everett Fox Translation)",
        "track": "DISCIPLESHIP",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 1995,
        "source_url": "https://www.schocken.com/book/the-five-books-of-moses/",
        "archive": "Schocken Books",
    },
    "numbers": {
        "title": "The Book of Numbers (Everett Fox Translation)",
        "track": "TRUTH_HISTORY",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 1995,
        "source_url": "https://www.schocken.com/book/the-five-books-of-moses/",
        "archive": "Schocken Books",
    },
    "deuteronomy": {
        "title": "The Book of Deuteronomy (Everett Fox Translation)",
        "track": "DISCIPLESHIP",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 1995,
        "source_url": "https://www.schocken.com/book/the-five-books-of-moses/",
        "archive": "Schocken Books",
    },
    # Prophets - ENGLISH_LITERATURE
    "joshua": {
        "title": "The Book of Joshua (Everett Fox Translation)",
        "track": "TRUTH_HISTORY",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 2014,
        "source_url": "https://www.schocken.com/book/the-early-prophets/",
        "archive": "Schocken Books",
    },
    "judges": {
        "title": "The Book of Judges (Everett Fox Translation)",
        "track": "TRUTH_HISTORY",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 2014,
        "source_url": "https://www.schocken.com/book/the-early-prophets/",
        "archive": "Schocken Books",
    },
    "samuel": {
        "title": "The Books of Samuel (Everett Fox Translation)",
        "track": "TRUTH_HISTORY",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 2014,
        "source_url": "https://www.schocken.com/book/the-early-prophets/",
        "archive": "Schocken Books",
    },
    "psalms": {
        "title": "The Book of Psalms (Everett Fox Translation)",
        "track": "ENGLISH_LITERATURE",
        "citation_author": "Everett Fox (Translator)",
        "citation_year": 2023,
        "source_url": "https://www.schocken.com/book/the-book-of-psalms/",
        "archive": "Schocken Books",
    },
}

# ── Helper Functions ──────────────────────────────────────────────────────────


async def embed(text: str) -> List[float]:
    """Generate embedding for text using OpenAI."""
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def upsert_chunk(
    session_factory,
    book_meta: Dict,
    chapter: int,
    verse_range: str,
    chunk_text: str,
):
    """Upsert a Bible chunk into Hippocampus."""
    
    # Create unique source_id
    book_name = book_meta["title"].split("(")[0].strip()
    source_id = f"bible-fox-{book_name.lower().replace(' ', '-')}-{chapter}-{verse_range}"
    
    # Build full chunk with context
    full_chunk = f"{book_meta['title']}, Chapter {chapter}:{verse_range}\n\n{chunk_text}"
    
    # Generate embedding
    log.info(f"  Embedding {book_name} {chapter}:{verse_range}...")
    embedding = await embed(full_chunk)
    
    # Upsert to database
    async with session_factory() as session:
        # Check if already exists
        result = await session.execute(
            text('SELECT id FROM "HippocampusDocument" WHERE "sourceId" = :source_id'),
            {"source_id": source_id}
        )
        existing = result.fetchone()
        
        if existing:
            log.info(f"    [skip] Already seeded: {book_name} {chapter}:{verse_range}")
            return "existing"
        
        # Insert new document
        await session.execute(
            text('''
                INSERT INTO "HippocampusDocument" (
                    id, "sourceId", "sourceTitle", "sourceUrl", "sourceType",
                    track, chunk, embedding, "citationAuthor", "citationYear",
                    "citationArchiveName", "createdAt", "updatedAt"
                ) VALUES (
                    gen_random_uuid(), :source_id, :source_title, :source_url, 'PRIMARY_SOURCE',
                    :track, :chunk, :embedding, :citation_author, :citation_year,
                    :citation_archive, NOW(), NOW()
                )
            '''),
            {
                "source_id": source_id,
                "source_title": book_meta["title"],
                "source_url": book_meta["source_url"],
                "track": book_meta["track"],
                "chunk": full_chunk,
                "embedding": embedding,
                "citation_author": book_meta["citation_author"],
                "citation_year": book_meta["citation_year"],
                "citation_archive": book_meta["archive"],
            }
        )
        await session.commit()
        log.info(f"    ✓ Stored {book_name} {chapter}:{verse_range}")
        return source_id


async def seed_book_from_file(book_key: str, file_path: Path, session_factory):
    """
    Seed a Bible book from a text file.
    
    Expected format:
    Chapter 1
    1 In the beginning...
    2 And the earth was...
    
    Chapter 2
    1 Thus the heavens...
    """
    if book_key not in BIBLE_BOOKS:
        log.error(f"Unknown book: {book_key}")
        return 0
    
    book_meta = BIBLE_BOOKS[book_key]
    log.info(f"[{book_key.upper()}] Seeding {book_meta['title']}...")
    
    if not file_path.exists():
        log.error(f"File not found: {file_path}")
        return 0
    
    content = file_path.read_text(encoding="utf-8")
    
    # Parse chapters and verses
    chunks_seeded = 0
    current_chapter = None
    current_verses = []
    verse_buffer = []
    
    for line in content.split("\n"):
        line = line.strip()
        
        # Detect chapter headers
        if line.startswith("Chapter "):
            # Save previous chapter if exists
            if current_chapter and verse_buffer:
                # Chunk every 10-15 verses for optimal retrieval
                for i in range(0, len(verse_buffer), 12):
                    chunk_verses = verse_buffer[i:i+12]
                    verse_range = f"{chunk_verses[0]['num']}-{chunk_verses[-1]['num']}"
                    chunk_text = "\n".join([f"{v['num']} {v['text']}" for v in chunk_verses])
                    
                    await upsert_chunk(
                        session_factory,
                        book_meta,
                        current_chapter,
                        verse_range,
                        chunk_text
                    )
                    chunks_seeded += 1
            
            # Start new chapter
            current_chapter = int(line.split()[1])
            verse_buffer = []
            continue
        
        # Parse verse lines (format: "1 In the beginning...")
        if line and line[0].isdigit():
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                verse_num = parts[0]
                verse_text = parts[1]
                verse_buffer.append({"num": verse_num, "text": verse_text})
    
    # Save final chapter
    if current_chapter and verse_buffer:
        for i in range(0, len(verse_buffer), 12):
            chunk_verses = verse_buffer[i:i+12]
            verse_range = f"{chunk_verses[0]['num']}-{chunk_verses[-1]['num']}"
            chunk_text = "\n".join([f"{v['num']} {v['text']}" for v in chunk_verses])
            
            await upsert_chunk(
                session_factory,
                book_meta,
                current_chapter,
                verse_range,
                chunk_text
            )
            chunks_seeded += 1
    
    log.info(f"[{book_key.upper()}] Seeded {chunks_seeded} chunks")
    return chunks_seeded


async def main():
    parser = argparse.ArgumentParser(description="Seed Everett Fox Bible translation")
    parser.add_argument("--book", help="Book to seed (e.g., genesis, exodus)")
    parser.add_argument("--all", action="store_true", help="Seed all available books")
    parser.add_argument("--data-dir", default="data/bible/everett_fox", help="Directory containing Bible text files")
    
    args = parser.parse_args()
    
    # Setup database
    engine = create_async_engine(POSTGRES_DSN, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    data_dir = Path(__file__).resolve().parents[1] / args.data_dir
    
    if args.all:
        total_chunks = 0
        for book_key in BIBLE_BOOKS.keys():
            file_path = data_dir / f"{book_key}.txt"
            chunks = await seed_book_from_file(book_key, file_path, session_factory)
            total_chunks += chunks
        log.info(f"✓ Total chunks seeded: {total_chunks}")
    elif args.book:
        file_path = data_dir / f"{args.book}.txt"
        chunks = await seed_book_from_file(args.book, file_path, session_factory)
        log.info(f"✓ Seeded {chunks} chunks from {args.book}")
    else:
        parser.print_help()
        return
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
