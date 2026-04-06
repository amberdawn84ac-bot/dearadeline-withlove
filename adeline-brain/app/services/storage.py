"""
Book storage abstraction — local disk (dev) or Supabase Storage (prod).

Set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY to use Supabase Storage.
Otherwise, falls back to local disk at BOOK_STORAGE_DIR.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
_STORAGE_DIR = os.getenv(
    "BOOK_STORAGE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "books"),
)
_BUCKET = "books"


def storage_key_for(book_id: str, source_name: str) -> str:
    safe_source = source_name.replace(" ", "_")
    return f"books/{book_id}/{safe_source}.epub"


async def upload_epub(book_id: str, epub_bytes: bytes, source_name: str) -> str:
    """Upload EPUB and return the storage key."""
    key = storage_key_for(book_id, source_name)

    if _SUPABASE_URL and _SUPABASE_KEY:
        await _upload_supabase(key, epub_bytes)
    else:
        _upload_local(key, epub_bytes)

    return key


async def download_epub(storage_key: str) -> Optional[bytes]:
    """Download EPUB by storage key. Returns None if not found."""
    if _SUPABASE_URL and _SUPABASE_KEY:
        return await _download_supabase(storage_key)
    else:
        return _download_local(storage_key)


# ── Local disk ────────────────────────────────────────────────────────────────

def _upload_local(storage_key: str, epub_bytes: bytes) -> None:
    relative = storage_key.removeprefix("books/")
    path = os.path.join(os.path.abspath(_STORAGE_DIR), relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(epub_bytes)
    logger.info(f"[Storage] Local write: {path} ({len(epub_bytes)} bytes)")


def _download_local(storage_key: str) -> Optional[bytes]:
    relative = storage_key.removeprefix("books/")
    path = os.path.join(os.path.abspath(_STORAGE_DIR), relative)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return f.read()


# ── Supabase Storage ─────────────────────────────────────────────────────────

async def _upload_supabase(storage_key: str, epub_bytes: bytes) -> None:
    url = f"{_SUPABASE_URL}/storage/v1/object/{_BUCKET}/{storage_key}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            content=epub_bytes,
            headers={
                "Authorization": f"Bearer {_SUPABASE_KEY}",
                "Content-Type": "application/epub+zip",
                "x-upsert": "true",
            },
        )
        if resp.status_code not in (200, 201):
            logger.error(f"[Storage] Supabase upload failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"Supabase upload failed: {resp.status_code}")
    logger.info(f"[Storage] Supabase upload: {storage_key} ({len(epub_bytes)} bytes)")


async def _download_supabase(storage_key: str) -> Optional[bytes]:
    url = f"{_SUPABASE_URL}/storage/v1/object/{_BUCKET}/{storage_key}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {_SUPABASE_KEY}"},
        )
        if resp.status_code == 200:
            return resp.content
        if resp.status_code == 404:
            return None
        logger.error(f"[Storage] Supabase download failed: {resp.status_code}")
        return None
