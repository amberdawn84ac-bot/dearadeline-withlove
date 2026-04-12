"""
seed_bookshelf.py — Bookshelf v1 Nightly Seed Script
Fetches books from Standard Ebooks and Project Gutenberg APIs.
Assigns curriculum tracks via Claude, estimates Lexile/grade bands, generates embeddings, and populates the books table.

Run from adeline-brain/:
    python scripts/seed_bookshelf.py

Scheduled nightly at 02:00 UTC (off-peak) via cron:
    0 2 * * * cd /app && python -m scripts.seed_bookshelf
"""
import asyncio
import json
import logging
import os
import sys
import uuid as uuid_lib
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx
import openai
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Load .env from adeline-brain directory
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bookshelf-seed")

# ── Config ────────────────────────────────────────────────────────────────────

_pg_password = os.getenv("POSTGRES_PASSWORD", "placeholder_password")
POSTGRES_DSN = (
    os.getenv("POSTGRES_DSN")
    or os.getenv("DIRECT_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or f"postgresql://adeline:{_pg_password}@localhost:5432/hippocampus"
).replace("postgresql://", "postgresql+asyncpg://").replace("@postgres:", "@localhost:")

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

# API configuration
STANDARD_EBOOKS_FEED = "https://standardebooks.org/feeds/atom/new-releases"
GUTENBERG_API = "https://gutendex.com/books/"
BOOKS_PER_SOURCE = 50

# 10-track curriculum tracks
TRACKS = [
    "CREATION_SCIENCE",
    "HEALTH_NATUROPATHY",
    "HOMESTEADING",
    "GOVERNMENT_ECONOMICS",
    "JUSTICE_CHANGEMAKING",
    "DISCIPLESHIP",
    "TRUTH_HISTORY",
    "ENGLISH_LITERATURE",
    "APPLIED_MATHEMATICS",
    "CREATIVE_ECONOMY",
]

# Lexile to Grade Band mapping
LEXILE_TO_GRADE = [
    (250, 350, "K"),
    (350, 450, "1"),
    (450, 550, "2"),
    (550, 650, "3"),
    (650, 750, "4-5"),
    (750, 850, "6"),
    (850, 950, "7"),
    (950, 1050, "8"),
    (1050, 1200, "9-12"),
]


# ── Helper Functions ──────────────────────────────────────────────────────────


async def fetch_standard_ebooks() -> List[dict]:
    """
    Fetch newest books from Standard Ebooks Atom feed.
    Returns list of book dicts with: title, author, url, cover_url, description
    """
    import xml.etree.ElementTree as ET
    log.info("Fetching from Standard Ebooks Atom feed...")
    books = []
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as session:
            resp = await session.get(STANDARD_EBOOKS_FEED)
            if resp.status_code != 200:
                log.error(f"Standard Ebooks feed returned {resp.status_code}")
                return []
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "media": "http://search.yahoo.com/mrss/",
            }
            root = ET.fromstring(resp.text)
            for entry in root.findall("atom:entry", ns)[:BOOKS_PER_SOURCE]:
                title = entry.findtext("atom:title", default="", namespaces=ns)
                author_el = entry.find("atom:author/atom:name", ns)
                author = author_el.text if author_el is not None else "Unknown"
                link_el = entry.find("atom:link[@rel='alternate']", ns) or entry.find("atom:link", ns)
                url = link_el.get("href", "") if link_el is not None else ""
                cover_el = entry.find("media:thumbnail", ns)
                cover_url = cover_el.get("url", "") if cover_el is not None else ""
                summary = entry.findtext("atom:summary", default="", namespaces=ns)
                books.append({
                    "title": title,
                    "author": author,
                    "url": url,
                    "cover_url": cover_url,
                    "description": summary,
                })
            log.info(f"Fetched {len(books)} books from Standard Ebooks")
    except asyncio.TimeoutError:
        log.error("Standard Ebooks feed timeout")
    except Exception as e:
        log.error(f"Standard Ebooks feed error: {e}")
    return books


async def fetch_gutenberg() -> List[dict]:
    """
    Fetch 50 popular books from Project Gutenberg (Gutendex) API.
    Returns list of book dicts with: title, authors, cover_image, formats
    """
    log.info(f"Fetching from Project Gutenberg API...")
    books = []
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as session:
            params = {"sort": "popular", "languages": "en"}
            resp = await session.get(GUTENBERG_API, params=params)
            if resp.status_code != 200:
                log.error(f"Gutenberg API returned {resp.status_code}")
                return []
            data = resp.json()
            books = data.get("results", [])[:BOOKS_PER_SOURCE]
            log.info(f"Fetched {len(books)} books from Project Gutenberg")
    except asyncio.TimeoutError:
        log.error("Project Gutenberg API timeout")
    except Exception as e:
        log.error(f"Project Gutenberg API error: {e}")
    return books


async def assign_track(title: str, description: str, max_retries: int = 2) -> str:
    """
    Use Gemini Flash to classify a book into one of 10 curriculum tracks.
    Falls back to ENGLISH_LITERATURE on failure.
    """
    tracks_list = ", ".join(TRACKS)
    prompt = f"""Assign this book to ONE curriculum track from: {tracks_list}

Title: {title}
Description: {description[:500]}

Return ONLY the track name. If unsure, return ENGLISH_LITERATURE."""

    for attempt in range(max_retries):
        try:
            client = openai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
            response = await client.chat.completions.create(
                model=GEMINI_MODEL,
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            track = response.choices[0].message.content.strip().upper()
            if track in TRACKS:
                return track
            if attempt < max_retries - 1:
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                log.warning(f"Gemini track assignment retry {attempt + 1}: {e}")
                await asyncio.sleep(1)
                continue
            log.error(f"Claude track assignment failed: {e}")
            break

    log.warning(f"Track assignment failed for '{title}' — defaulting to ENGLISH_LITERATURE")
    return "ENGLISH_LITERATURE"


def estimate_lexile(description: str, word_count: int = None) -> int:
    """
    Estimate Lexile level from word count or description length.
    Heuristic: base 400 + (word_count / 1000) * 150, clamped to [250, 1200]
    """
    if word_count:
        return min(1200, max(250, 400 + (word_count // 1000) * 150))

    # Estimate from description length
    desc_words = len(description.split())
    return min(1200, max(250, 400 + (desc_words // 100) * 100))


def estimate_grade_band(lexile_level: int) -> str:
    """Convert Lexile to grade band."""
    for min_l, max_l, grade in LEXILE_TO_GRADE:
        if min_l <= lexile_level <= max_l:
            return grade
    return "9-12"  # Default for very high


async def generate_embedding(title: str, author: str, description: str) -> Optional[List[float]]:
    """
    Generate OpenAI embedding (text-embedding-3-small) from book metadata.
    Truncates to 8191 chars to stay within token limits.
    """
    try:
        text_input = f"{title} {author} {description}"[:8191]
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.embeddings.create(
            model=EMBED_MODEL,
            input=text_input,
        )
        return resp.data[0].embedding
    except openai.BadRequestError as e:
        if "content_filter" in str(e).lower() or e.status_code == 400:
            log.warning(f"Content filter blocked embedding for '{title}'")
            return None
        log.error(f"OpenAI embedding error: {e}")
        return None
    except Exception as e:
        log.error(f"Embedding generation failed: {e}")
        return None


async def check_duplicate(conn, source_url: str) -> bool:
    """Check if book with this source_url already exists."""
    try:
        result = await conn.fetchval(
            'SELECT id FROM "Book" WHERE source_url = $1 LIMIT 1',
            source_url,
        )
        return result is not None
    except Exception as e:
        log.warning(f"Duplicate check error: {e}")
        return False


async def insert_or_update_book(
    conn,
    title: str,
    author: str,
    source_url: str,
    track: str,
    lexile_level: int,
    grade_band: str,
    embedding: List[float],
    description: str = "",
    cover_url: str = None,
    source_library: str = None,
) -> Optional[str]:
    """
    Insert new book or update existing (by source_url).
    Returns book ID on success, None on failure.
    """
    try:
        book_id = str(uuid_lib.uuid4())
        await conn.execute(
            """
            INSERT INTO "Book" (
              id, title, author, "source_url", track, "lexile_level", "grade_band",
              embedding, description, "coverUrl", "sourceLibrary", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now(), now())
            ON CONFLICT ("source_url") DO UPDATE SET
              title = EXCLUDED.title,
              description = EXCLUDED.description,
              embedding = EXCLUDED.embedding,
              "updatedAt" = now()
            RETURNING id;
            """,
            book_id,
            title,
            author,
            source_url,
            track,
            lexile_level,
            grade_band,
            embedding,
            description,
            cover_url,
            source_library,
        )
        return book_id
    except Exception as e:
        log.error(f"Insert/update failed for '{title}': {e}")
        return None


async def process_standard_ebooks_book(
    conn, book_data: dict, session_factory
) -> tuple[bool, str]:
    """
    Process a single Standard Ebooks book.
    Returns (success: bool, message: str)
    """
    try:
        title = book_data.get("title", "Unknown")
        author = book_data.get("author", {}).get("name", "Unknown") if book_data.get("author") else "Unknown"
        source_url = book_data.get("url", "")
        cover_url = book_data.get("cover_url", "")
        description = book_data.get("description", "")

        if not source_url:
            return False, f"No source_url for '{title}'"

        # Check for duplicate
        if await check_duplicate(conn, source_url):
            return False, f"Duplicate source_url"

        # Assign track
        track = await assign_track(title, description)

        # Estimate Lexile and grade band
        lexile_level = estimate_lexile(description)
        grade_band = estimate_grade_band(lexile_level)

        # Generate embedding
        embedding = await generate_embedding(title, author, description)
        if embedding is None:
            return False, f"Embedding generation failed"

        # Insert/update
        book_id = await insert_or_update_book(
            conn,
            title=title,
            author=author,
            source_url=source_url,
            track=track,
            lexile_level=lexile_level,
            grade_band=grade_band,
            embedding=embedding,
            description=description,
            cover_url=cover_url,
            source_library="Standard Ebooks",
        )

        if book_id:
            return True, f"Track: {track}, Lexile: {lexile_level}, Grade: {grade_band}, ID: {book_id}"
        else:
            return False, f"Insert/update failed"

    except Exception as e:
        return False, f"Processing error: {e}"


async def process_gutenberg_book(
    conn, book_data: dict, session_factory
) -> tuple[bool, str]:
    """
    Process a single Project Gutenberg book (from Gutendex).
    Returns (success: bool, message: str)
    """
    try:
        title = book_data.get("title", "Unknown")
        authors = book_data.get("authors", [])
        author = authors[0].get("name", "Unknown") if authors else "Unknown"
        gutenberg_id = book_data.get("id", "")
        cover_url = book_data.get("cover_image", "")
        description = book_data.get("description", "") or book_data.get("description", "")

        # Build source_url from Gutenberg ID
        source_url = f"https://www.gutenberg.org/ebooks/{gutenberg_id}"

        if not gutenberg_id:
            return False, f"No gutenberg_id for '{title}'"

        # Check for duplicate
        if await check_duplicate(conn, source_url):
            return False, f"Duplicate source_url"

        # Assign track
        track = await assign_track(title, description)

        # Estimate Lexile and grade band
        lexile_level = estimate_lexile(description)
        grade_band = estimate_grade_band(lexile_level)

        # Generate embedding
        embedding = await generate_embedding(title, author, description)
        if embedding is None:
            return False, f"Embedding generation failed"

        # Insert/update
        book_id = await insert_or_update_book(
            conn,
            title=title,
            author=author,
            source_url=source_url,
            track=track,
            lexile_level=lexile_level,
            grade_band=grade_band,
            embedding=embedding,
            description=description,
            cover_url=cover_url,
            source_library="Project Gutenberg",
        )

        if book_id:
            return True, f"Track: {track}, Lexile: {lexile_level}, Grade: {grade_band}, ID: {book_id}"
        else:
            return False, f"Insert/update failed"

    except Exception as e:
        return False, f"Processing error: {e}"


# ── Main ──────────────────────────────────────────────────────────────────────


async def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-placeholder"):
        log.error("OPENAI_API_KEY is not set. Add it to .env and retry.")
        sys.exit(1)

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.startswith("sk-placeholder"):
        log.error("ANTHROPIC_API_KEY is not set. Add it to .env and retry.")
        sys.exit(1)

    log.info("══════════════════════════════════════════════════════════════")
    log.info("  SEEDING BOOKSHELF — Standard Ebooks + Project Gutenberg    ")
    log.info("══════════════════════════════════════════════════════════════")

    # Initialize database engine
    engine = create_async_engine(POSTGRES_DSN, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Ensure pgvector extension exists
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        log.info("[Bookshelf] pgvector extension ready")
    except Exception as e:
        log.error(f"[Bookshelf] Failed to initialize pgvector: {e}")
        await engine.dispose()
        sys.exit(1)

    # Fetch from both APIs
    log.info("── Phase 1: Fetch APIs ────────────────────────────────────")
    standard_ebooks_books = await fetch_standard_ebooks()
    gutenberg_books = await fetch_gutenberg()
    log.info(f"Total books to process: {len(standard_ebooks_books) + len(gutenberg_books)}")

    # Process books
    log.info("── Phase 2: Process & Seed ────────────────────────────────")
    new_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    # Get a connection for the session
    async with engine.begin() as conn:
        # Standard Ebooks
        log.info(f"Processing {len(standard_ebooks_books)} Standard Ebooks books...")
        for book in standard_ebooks_books:
            success, msg = await process_standard_ebooks_book(conn, book, session_factory)
            if success:
                log.info(f"  ✓ '{book.get('title', '?')}' {msg}")
                new_count += 1
            else:
                if "Duplicate" in msg:
                    skipped_count += 1
                    log.debug(f"  ⊘ '{book.get('title', '?')}' {msg}")
                else:
                    error_count += 1
                    log.warning(f"  ✗ '{book.get('title', '?')}' {msg}")

        # Project Gutenberg
        log.info(f"Processing {len(gutenberg_books)} Project Gutenberg books...")
        for book in gutenberg_books:
            success, msg = await process_gutenberg_book(conn, book, session_factory)
            if success:
                log.info(f"  ✓ '{book.get('title', '?')}' {msg}")
                new_count += 1
            else:
                if "Duplicate" in msg:
                    skipped_count += 1
                    log.debug(f"  ⊘ '{book.get('title', '?')}' {msg}")
                else:
                    error_count += 1
                    log.warning(f"  ✗ '{book.get('title', '?')}' {msg}")

    # Summary
    log.info("── Phase 3: Summary ───────────────────────────────────────")
    log.info(f"  ✓ New books: {new_count}")
    log.info(f"  ↻ Updated: {updated_count}")
    log.info(f"  ⊘ Skipped (duplicates): {skipped_count}")
    log.info(f"  ✗ Errors: {error_count}")
    log.info(f"  ━ Total processed: {new_count + updated_count + skipped_count + error_count}")

    await engine.dispose()

    log.info("══════════════════════════════════════════════════════════════")
    log.info("  SEED COMPLETE                                              ")
    log.info("══════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
