"""
Storage abstraction — handles books (EPUB) and mastery evidence (photos/videos).

Supabase Storage (prod) or local disk (dev).
Set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY for cloud storage.

Buckets:
- books: EPUB files for Reading Nook
- mastery-evidence: Student photo/video submissions for OAS standards
"""
import logging
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
_STORAGE_DIR = os.getenv(
    "BOOK_STORAGE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "books"),
)
_EVIDENCE_DIR = os.getenv(
    "EVIDENCE_STORAGE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "evidence"),
)
_BUCKET_BOOKS = "books"
_BUCKET_EVIDENCE = "mastery-evidence"
_evidence_bucket_private = False
_evidence_bucket_lock = asyncio.Lock()
_evidence_upload_slots = asyncio.Semaphore(max(1, int(os.getenv("EVIDENCE_UPLOAD_CONCURRENCY", "4"))))


@asynccontextmanager
async def evidence_upload_slot():
    try:
        await asyncio.wait_for(_evidence_upload_slots.acquire(), timeout=15)
    except asyncio.TimeoutError as exc:
        raise RuntimeError("Evidence uploads are busy; please retry shortly") from exc
    try:
        yield
    finally:
        _evidence_upload_slots.release()


async def read_upload_limited(upload_file, max_bytes: int = 50 * 1024 * 1024) -> bytes:
    """Read incrementally and stop before an oversized body consumes unbounded RAM."""
    content = bytearray()
    while True:
        chunk = await upload_file.read(1024 * 1024)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_bytes:
            raise ValueError("File too large (50MB maximum)")
    return bytes(content)


# ═══════════════════════════════════════════════════════════════════════════════
# Mastery Evidence Upload (Wire 2: Blob Storage for OAS)
# ═══════════════════════════════════════════════════════════════════════════════

async def upload_mastery_evidence(
    student_id: str,
    standard_id: str,
    file_bytes: bytes,
    content_type: str,  # "image/jpeg", "image/png", "video/mp4"
    original_filename: Optional[str] = None,
) -> str:
    """
    Upload photo/video evidence for OAS standard mastery.
    
    Returns the storage URL/key for the uploaded file.
    DO NOT store raw bytes in PostgreSQL — use this instead.
    
    Storage path format: mastery-evidence/{student_id}/{standard_id}/{uuid}.{ext}
    
    Example:
        url = await upload_mastery_evidence(
            student_id="user-123",
            standard_id="OAS.MATH.7.N.1",
            file_bytes=photo_bytes,
            content_type="image/jpeg",
        )
        # Returns: "mastery-evidence/user-123/OAS.MATH.7.N.1/abc-123.jpg"
    """
    # Generate unique filename
    ext = _content_type_to_ext(content_type)
    unique_id = str(uuid4())[:8]
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    filename = f"{timestamp}_{unique_id}.{ext}"
    
    # Build storage key
    safe_standard = standard_id.replace(".", "_")
    storage_key = f"{student_id}/{safe_standard}/{filename}"
    
    if _SUPABASE_URL and _SUPABASE_KEY:
        url = await _upload_evidence_supabase(storage_key, file_bytes, content_type)
        logger.info(
            f"[Storage] Evidence uploaded to Supabase: {storage_key} "
            f"({len(file_bytes)} bytes)"
        )
        return url
    else:
        local_path = _upload_evidence_local(storage_key, file_bytes)
        logger.info(
            f"[Storage] Evidence saved locally: {local_path} ({len(file_bytes)} bytes)"
        )
        # Return file:// URL for local storage
        return f"file://{local_path}"


def _content_type_to_ext(content_type: str) -> str:
    """Map MIME type to file extension."""
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
    }
    return mapping.get(content_type, "bin")


async def _upload_evidence_supabase(
    storage_key: str, 
    file_bytes: bytes, 
    content_type: str
) -> str:
    """Upload evidence and return only its private object key."""
    await _ensure_evidence_bucket_private()
    url = f"{_SUPABASE_URL}/storage/v1/object/{_BUCKET_EVIDENCE}/{storage_key}"
    
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            content=file_bytes,
            headers={
                "Authorization": f"Bearer {_SUPABASE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        if resp.status_code not in (200, 201):
            logger.error(f"[Storage] Supabase evidence upload failed: {resp.status_code}")
            raise RuntimeError(f"Evidence upload failed: {resp.status_code}")
    
    return storage_key


async def _ensure_evidence_bucket_private() -> None:
    """Create or harden the child-evidence bucket before accepting uploads."""
    global _evidence_bucket_private
    if _evidence_bucket_private:
        return
    async with _evidence_bucket_lock:
        if _evidence_bucket_private:
            return
        headers = {
            "Authorization": f"Bearer {_SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            bucket_url = f"{_SUPABASE_URL}/storage/v1/bucket/{_BUCKET_EVIDENCE}"
            response = await client.put(bucket_url, json={"public": False}, headers=headers)
            if response.status_code == 404:
                response = await client.post(
                    f"{_SUPABASE_URL}/storage/v1/bucket",
                    json={"id": _BUCKET_EVIDENCE, "name": _BUCKET_EVIDENCE, "public": False},
                    headers=headers,
                )
            response.raise_for_status()
        _evidence_bucket_private = True


def _upload_evidence_local(storage_key: str, file_bytes: bytes) -> str:
    """Save evidence to local disk and return absolute path."""
    # storage_key format: mastery-evidence/{student_id}/{standard_id}/{filename}
    relative_path = storage_key.removeprefix("mastery-evidence/")
    full_path = os.path.join(os.path.abspath(_EVIDENCE_DIR), relative_path)
    
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    
    return full_path


async def get_evidence_url(storage_key_or_url: str) -> Optional[str]:
    """
    Get accessible URL for evidence.
    
    For Supabase: returns a short-lived signed URL for a private object
    For local: returns the file path
    """
    if storage_key_or_url.startswith("http"):
        # Backward compatibility for evidence written before private keys were
        # introduced. A data migration strips our own old public URL prefix.
        return storage_key_or_url
    elif storage_key_or_url.startswith("file://"):
        return storage_key_or_url[7:]  # Strip file:// prefix
    else:
        # Assume it's a storage key in Supabase
        if _SUPABASE_URL and _SUPABASE_KEY:
            await _ensure_evidence_bucket_private()
            sign_url = f"{_SUPABASE_URL}/storage/v1/object/sign/{_BUCKET_EVIDENCE}/{storage_key_or_url}"
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    sign_url,
                    json={"expiresIn": 3600},
                    headers={"Authorization": f"Bearer {_SUPABASE_KEY}"},
                )
                response.raise_for_status()
                signed_path = response.json().get("signedURL") or response.json().get("signedUrl")
                if not signed_path:
                    return None
                return signed_path if str(signed_path).startswith("http") else f"{_SUPABASE_URL}/storage/v1{signed_path}"
        else:
            # Local path
            relative = storage_key_or_url.removeprefix("mastery-evidence/")
            return os.path.join(os.path.abspath(_EVIDENCE_DIR), relative)



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
    url = f"{_SUPABASE_URL}/storage/v1/object/{_BUCKET_BOOKS}/{storage_key}"
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
    url = f"{_SUPABASE_URL}/storage/v1/object/{_BUCKET_BOOKS}/{storage_key}"
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
