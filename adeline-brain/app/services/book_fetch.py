"""
Book fetch service with waterfall logic:
1. Try Standard Ebooks first
2. Fall through to Gutendex
3. Save to Supabase Storage
"""
import httpx
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


async def standardize_slug(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


async def fetch_from_standard_ebooks(author: str, title: str, timeout: int = 30) -> Optional[bytes]:
    author_slug = await standardize_slug(author)
    title_slug = await standardize_slug(title)
    base_url = f"https://standardebooks.org/ebooks/{author_slug}/{title_slug}"
    epub_paths = [
        f"/dist/{author_slug}_{title_slug}.epub",
        f"/dist/{author_slug}_{title_slug}.kepub.epub",
    ]
    async with httpx.AsyncClient(timeout=timeout) as client:
        for epub_path in epub_paths:
            url = f"{base_url}{epub_path}"
            try:
                response = await client.get(url, follow_redirects=True)
                if response.status_code == 200:
                    return response.content
            except httpx.RequestError:
                continue
    return None


async def fetch_from_gutendex(title: str, timeout: int = 30) -> Optional[bytes]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            search_response = await client.get("https://gutendex.com/books", params={"search": title})
            data = search_response.json()
            results = data.get("results", [])
            if not results:
                return None
            epub_url = results[0].get("formats", {}).get("application/epub+zip")
            if not epub_url:
                return None
            epub_response = await client.get(epub_url)
            return epub_response.content if epub_response.status_code == 200 else None
        except Exception:
            return None


async def save_to_storage(book_id: str, epub_bytes: bytes, source: str = "Unknown") -> str:
    source_safe = re.sub(r'[^\w]', '', source.replace(" ", "_"))
    storage_key = f"books/{book_id}/{source_safe}.epub"
    # In production, upload to Supabase Storage here
    logger.info(f"Would upload to storage: {storage_key} ({len(epub_bytes)} bytes)")
    return storage_key


async def fetch_book_with_waterfall(book_id: str, title: str, author: str) -> Optional[tuple[bytes, str]]:
    epub_bytes = await fetch_from_standard_ebooks(author, title)
    if epub_bytes:
        await save_to_storage(book_id, epub_bytes, "Standard Ebooks")
        return (epub_bytes, "Standard Ebooks")
    epub_bytes = await fetch_from_gutendex(title)
    if epub_bytes:
        await save_to_storage(book_id, epub_bytes, "Gutenberg")
        return (epub_bytes, "Gutenberg")
    return None
