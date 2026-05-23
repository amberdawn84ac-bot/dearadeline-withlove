"""
Seed External Sources — Ingest content from specific websites and books.

This script scrapes content from trusted homesteading sources and adds books
to the knowledge archive (Hippocampus) so Adeline can reference them in lessons.

Usage:
    cd adeline-brain
    railway run -- python scripts/seed_external_sources.py

Sources:
    - mountainroseherbs.com (herbalism, natural health)
    - rareseeds.com (heirloom seeds, gardening)
    - Do Hard Things book (Brett & Alex Harris)
"""
import asyncio
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connections.pgvector_client import hippocampus

# Source definitions with key pages to scrape
EXTERNAL_SOURCES = {
    "mountainroseherbs.com": {
        "track": "HEALTH_NATUROPATHY",
        "base_url": "https://www.mountainroseherbs.com",
        "pages": [
            "/blog/herbal-remedies-for-beginners",
            "/blog/how-to-make-herbal-teas",
            "/learn/growing-medicinal-herbs",
            "/learn/herbal-preparations-101",
        ],
        "description": "Mountain Rose Herbs - Organic herbs, spices, teas",
    },
    "rareseeds.com": {
        "track": "HOMESTEADING",
        "base_url": "https://www.rareseeds.com",
        "pages": [
            "/growing-guides/seed-starting-guide",
            "/growing-guides/heirloom-tomatoes",
            "/growing-guides/saving-seeds",
            "/learn/organic-gardening-basics",
        ],
        "description": "Baker Creek Heirloom Seeds - Rare and heirloom varieties",
    },
}

BOOKS = [
    {
        "title": "Do Hard Things: A Teenage Rebellion Against Low Expectations",
        "author": "Brett Harris, Alex Harris",
        "track": "DISCIPLESHIP",
        "grade_band": [7, 12],
        "lexile": 950,
        "description": "A book challenging teenagers to reject cultural low expectations and do hard things for God's glory.",
        "source_url": "https://www.amazon.com/Do-Hard-Things-Rebellion-Expectations/dp/1601421125",
    },
]


async def fetch_page(url: str) -> str:
    """Fetch page content using httpx."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {url}: {e}")
        return ""


def extract_text(html: str) -> str:
    """Extract readable text from HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text from main content areas
        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main:
            text = main.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)[:8000]  # Limit to 8k chars for embedding
    except ImportError:
        print("  [ERROR] BeautifulSoup not installed. Run: pip install beautifulsoup4")
        return ""
    except Exception as e:
        print(f"  [ERROR] Failed to extract text: {e}")
        return ""


async def ingest_web_source(source_key: str, source_config: dict):
    """Ingest pages from a web source into Hippocampus."""
    print(f"\n[Web Source] {source_key}")
    print(f"  Track: {source_config['track']}")
    
    for page_path in source_config["pages"]:
        url = urljoin(source_config["base_url"], page_path)
        print(f"\n  [Fetching] {url}")
        
        html = await fetch_page(url)
        if not html:
            continue
        
        text = extract_text(html)
        if not text or len(text) < 100:
            print(f"    [SKIP] No meaningful content extracted")
            continue
        
        # Check if already exists (by URL)
        existing = await hippocampus.similarity_search(
            query=text[:200],
            track=source_config["track"],
            limit=1,
            min_similarity=0.95,  # Very high threshold for near-duplicates
        )
        if existing:
            print(f"    [SKIP] Already exists in Hippocampus")
            continue
        
        # Generate embedding and store
        chunk_id = str(uuid.uuid4())
        await hippocampus.add_chunk(
            chunk_id=chunk_id,
            text=text,
            metadata={
                "source_title": f"{source_config['description']} - {page_path}",
                "source_url": url,
                "citation_author": source_key,
                "citation_year": datetime.now().year,
                "track": source_config["track"],
                "tags": ["external_source", "homesteading", "herbalism"],
            }
        )
        print(f"    [ADDED] chunk_id={chunk_id[:8]}... length={len(text)}")


async def ingest_book(book: dict):
    """Add a book to the Book table (lessons reference it via ReadingSession)."""
    from app.config import get_db_conn
    
    print(f"\n[Book] {book['title']}")
    
    conn = await get_db_conn()
    try:
        # Check if already exists
        existing = await conn.fetchrow(
            'SELECT id FROM "Book" WHERE title = $1',
            book["title"]
        )
        if existing:
            print(f"  [SKIP] Already exists in Book table")
            return
        
        # Insert book
        book_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO "Book" (
                id, title, author, track, "gradeBand", "lexileLevel",
                description, "coverImageUrl", "sourceUrl",
                "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4::"Track", $5, $6, $7, $8, $9, NOW(), NOW())
            """,
            book_id,
            book["title"],
            book["author"],
            book["track"],
            json.dumps(book["grade_band"]),
            book["lexile"],
            book["description"],
            None,  # cover_image_url
            book.get("source_url"),
        )
        print(f"  [ADDED] book_id={book_id[:8]}...")
        
        # Note: Full book content would need to be chunked and added to Hippocampus
        # For now, we just add the book record (lessons reference it via literature_agent)
        
    finally:
        await conn.close()


async def seed_all():
    """Main seeding routine."""
    print("=" * 60)
    print("Seeding External Sources into Adeline's Knowledge Archive")
    print("=" * 60)
    
    # Check requirements
    if not os.getenv("DATABASE_URL") and not os.getenv("POSTGRES_DSN"):
        print("ERROR: DATABASE_URL or POSTGRES_DSN not set")
        sys.exit(1)
    
    # Ingest web sources
    for source_key, source_config in EXTERNAL_SOURCES.items():
        try:
            await ingest_web_source(source_key, source_config)
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {source_key}: {e}")
    
    # Ingest books
    for book in BOOKS:
        try:
            await ingest_book(book)
        except Exception as e:
            print(f"  [ERROR] Failed to ingest book: {e}")
    
    print("\n" + "=" * 60)
    print("External source seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_all())
