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
    storage_key = f"mastery-evidence/{student_id}/{safe_standard}/{filename}"
    
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
    """Upload evidence to Supabase Storage and return public URL."""
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
    
    # Return public URL
    public_url = f"{_SUPABASE_URL}/storage/v1/object/public/{_BUCKET_EVIDENCE}/{storage_key}"
    return public_url


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
    
    For Supabase: returns the public URL
    For local: returns the file path
    """
    if storage_key_or_url.startswith("http"):
        return storage_key_or_url  # Already a full URL
    elif storage_key_or_url.startswith("file://"):
        return storage_key_or_url[7:]  # Strip file:// prefix
    else:
        # Assume it's a storage key in Supabase
        if _SUPABASE_URL:
            return f"{_SUPABASE_URL}/storage/v1/object/public/{_BUCKET_EVIDENCE}/{storage_key_or_url}"
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
