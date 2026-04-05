# Bookshelf Production Ready — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Reading Nook bookshelf feature fully production-ready by adding reading session tracking (StudentBook CRUD), Supabase Storage for EPUB files, and gitignore for local book storage.

**Architecture:** Two new API files — `reading_sessions.py` (StudentBook CRUD) and `storage.py` (abstraction over local disk vs Supabase Storage). The bookshelf API's waterfall and download endpoints switch to `storage.py`. Frontend brain-client gets reading session functions. BookshelfGrid shows per-student reading progress.

**Tech Stack:** FastAPI + asyncpg (Python), httpx for Supabase REST, Next.js + TypeScript (frontend)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `adeline-brain/app/api/reading_sessions.py` | StudentBook CRUD: start, progress, finish, list shelf |
| Create | `adeline-brain/app/services/storage.py` | Storage abstraction: local disk (dev) or Supabase Storage (prod) |
| Create | `adeline-brain/tests/test_reading_sessions.py` | Reading session API + model tests |
| Create | `adeline-brain/tests/test_storage.py` | Storage abstraction tests |
| Modify | `adeline-brain/app/main.py:29,88` | Register reading_sessions router |
| Modify | `adeline-brain/app/api/bookshelf.py:100-132,259-273` | Use storage.py for waterfall save + download |
| Modify | `adeline-brain/.env.example` | Add SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY |
| Modify | `adeline-ui/src/lib/brain-client.ts:655-707` | Add reading session types + API functions |
| Modify | `adeline-ui/src/components/reading-nook/BookshelfGrid.tsx` | Fetch reading sessions, pass to BookCard |
| Modify | `.gitignore` | Add `adeline-brain/data/books/` |

---

### Task 1: Storage abstraction service

**Files:**
- Create: `adeline-brain/app/services/storage.py`
- Create: `adeline-brain/tests/test_storage.py`

- [ ] **Step 1: Write failing tests for storage abstraction**

Create `adeline-brain/tests/test_storage.py`:

```python
"""Tests for the book storage abstraction (local + Supabase)."""
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.storage import upload_epub, download_epub, storage_key_for


def test_storage_key_for():
    key = storage_key_for("book-123", "Standard Ebooks")
    assert key == "books/book-123/Standard_Ebooks.epub"


def test_storage_key_sanitizes():
    key = storage_key_for("book-456", "Gutenberg Project")
    assert key == "books/book-456/Gutenberg_Project.epub"


@pytest.mark.asyncio
async def test_upload_epub_local(tmp_path):
    with patch("app.services.storage._SUPABASE_URL", None), \
         patch("app.services.storage._STORAGE_DIR", str(tmp_path)):
        key = await upload_epub("book-001", b"epub-content", "Standard Ebooks")
    assert key == "books/book-001/Standard_Ebooks.epub"
    assert (tmp_path / "book-001" / "Standard_Ebooks.epub").read_bytes() == b"epub-content"


@pytest.mark.asyncio
async def test_download_epub_local(tmp_path):
    book_dir = tmp_path / "book-001"
    book_dir.mkdir()
    (book_dir / "Standard_Ebooks.epub").write_bytes(b"epub-data")
    with patch("app.services.storage._SUPABASE_URL", None), \
         patch("app.services.storage._STORAGE_DIR", str(tmp_path)):
        data = await download_epub("books/book-001/Standard_Ebooks.epub")
    assert data == b"epub-data"


@pytest.mark.asyncio
async def test_download_epub_local_missing(tmp_path):
    with patch("app.services.storage._SUPABASE_URL", None), \
         patch("app.services.storage._STORAGE_DIR", str(tmp_path)):
        data = await download_epub("books/missing/file.epub")
    assert data is None


@pytest.mark.asyncio
async def test_upload_epub_supabase():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.storage._SUPABASE_URL", "https://test.supabase.co"), \
         patch("app.services.storage._SUPABASE_KEY", "test-key"), \
         patch("app.services.storage.httpx.AsyncClient", return_value=mock_client):
        key = await upload_epub("book-002", b"epub-bytes", "Gutenberg")
    assert key == "books/book-002/Gutenberg.epub"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_download_epub_supabase():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"supabase-epub-data"

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.storage._SUPABASE_URL", "https://test.supabase.co"), \
         patch("app.services.storage._SUPABASE_KEY", "test-key"), \
         patch("app.services.storage.httpx.AsyncClient", return_value=mock_client):
        data = await download_epub("books/book-002/Gutenberg.epub")
    assert data == b"supabase-epub-data"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd adeline-brain && python -m pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.storage'`

- [ ] **Step 3: Implement storage abstraction**

Create `adeline-brain/app/services/storage.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd adeline-brain && python -m pytest tests/test_storage.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/services/storage.py adeline-brain/tests/test_storage.py
git commit -m "feat(bookshelf): Add storage abstraction — local disk + Supabase Storage"
```

---

### Task 2: Wire bookshelf API to storage abstraction

**Files:**
- Modify: `adeline-brain/app/api/bookshelf.py`

- [ ] **Step 1: Update `_run_waterfall` to use `storage.upload_epub`**

Replace the local file write block in `_run_waterfall` (lines 100-132) with:

```python
async def _run_waterfall(book_id: str, title: str, author: str):
    """Background task: fetch EPUB via waterfall, update Book row."""
    from app.services.storage import upload_epub

    result = await fetch_book_with_waterfall(book_id, title, author)
    conn = await _get_conn()
    try:
        if result:
            epub_bytes, source = result
            storage_key = await upload_epub(book_id, epub_bytes, source)

            await conn.execute(
                """
                UPDATE "Book"
                SET "isDownloaded" = TRUE,
                    "sourceLibrary" = $2,
                    "storageKey" = $3,
                    "updatedAt" = now()
                WHERE id = $1
                """,
                book_id, source, storage_key,
            )
            logger.info(f"[Bookshelf] Downloaded {title!r} from {source} ({len(epub_bytes)} bytes)")
        else:
            logger.warning(f"[Bookshelf] Waterfall failed for {title!r} — no source found")
    except Exception:
        logger.exception(f"[Bookshelf] Error in waterfall for book {book_id}")
    finally:
        await conn.close()
```

- [ ] **Step 2: Update `download_book` endpoint to use `storage.download_epub`**

Replace the local file read block in `download_book` (lines 242-273) with:

```python
@router.get("/{book_id}/download")
async def download_book(book_id: str):
    """Download the EPUB file for a book."""
    from app.services.storage import download_epub

    conn = await _get_conn()
    try:
        r = await conn.fetchrow(
            'SELECT "isDownloaded", "storageKey", title FROM "Book" WHERE id = $1',
            book_id,
        )
    finally:
        await conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="Book not found")
    if not r["isDownloaded"] or not r["storageKey"]:
        raise HTTPException(status_code=404, detail="Book not yet downloaded")

    epub_bytes = await download_epub(r["storageKey"])
    if not epub_bytes:
        raise HTTPException(status_code=404, detail="EPUB file not found in storage")

    filename = f"{r['title'][:60].replace(chr(34), '')}.epub"
    return Response(
        content=epub_bytes,
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 3: Remove `_STORAGE_DIR` from bookshelf.py**

Delete line 29 (`_STORAGE_DIR = ...`). Storage dir is now owned by `storage.py`.

- [ ] **Step 4: Run existing bookshelf tests**

Run: `cd adeline-brain && python -m pytest tests/test_e2e_bookshelf.py -v`

Update any tests that mock `_STORAGE_DIR` to mock `app.api.bookshelf.upload_epub` and `app.api.bookshelf.download_epub` instead. Specifically:

- `test_run_waterfall_updates_db_on_success`: patch `app.api.bookshelf.upload_epub` instead of `_STORAGE_DIR`
- `test_download_book_success`: patch `app.api.bookshelf.download_epub` to return bytes
- `test_download_book_file_missing_on_disk`: patch `app.api.bookshelf.download_epub` to return `None`

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/api/bookshelf.py adeline-brain/tests/test_e2e_bookshelf.py
git commit -m "refactor(bookshelf): Use storage abstraction for EPUB upload/download"
```

---

### Task 3: Reading session API (StudentBook CRUD)

**Files:**
- Create: `adeline-brain/app/api/reading_sessions.py`
- Create: `adeline-brain/tests/test_reading_sessions.py`
- Modify: `adeline-brain/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `adeline-brain/tests/test_reading_sessions.py`:

```python
"""Tests for reading session (StudentBook) API endpoints."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.api.reading_sessions import router as sessions_router


def _make_mock_conn(rows=None, row=None):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows or [])
    conn.fetchrow = AsyncMock(return_value=row)
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(sessions_router)
    return test_app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


SAMPLE_SESSION = {
    "studentId": "student-001",
    "bookId": "book-001",
    "startedAt": "2026-04-05T10:00:00+00:00",
    "finishedAt": None,
    "currentPage": 42,
}


@pytest.mark.asyncio
async def test_start_reading(client):
    mock_conn = _make_mock_conn(row=SAMPLE_SESSION)
    with patch("app.api.reading_sessions._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.post("/reading/start", json={
            "student_id": "student-001",
            "book_id": "book-001",
        })
    assert resp.status_code == 200
    assert resp.json()["student_id"] == "student-001"
    assert resp.json()["book_id"] == "book-001"


@pytest.mark.asyncio
async def test_update_progress(client):
    mock_conn = _make_mock_conn(row={**SAMPLE_SESSION, "currentPage": 100})
    with patch("app.api.reading_sessions._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.patch("/reading/progress", json={
            "student_id": "student-001",
            "book_id": "book-001",
            "current_page": 100,
        })
    assert resp.status_code == 200
    assert resp.json()["current_page"] == 100


@pytest.mark.asyncio
async def test_finish_reading(client):
    finished_session = {**SAMPLE_SESSION, "finishedAt": "2026-04-05T12:00:00+00:00"}
    mock_conn = _make_mock_conn(row=finished_session)
    with patch("app.api.reading_sessions._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.post("/reading/finish", json={
            "student_id": "student-001",
            "book_id": "book-001",
        })
    assert resp.status_code == 200
    assert resp.json()["finished_at"] is not None


@pytest.mark.asyncio
async def test_get_shelf(client):
    mock_conn = _make_mock_conn(rows=[
        {**SAMPLE_SESSION, "title": "Pride and Prejudice", "author": "Jane Austen",
         "coverUrl": None, "track": "ENGLISH_LITERATURE"},
    ])
    with patch("app.api.reading_sessions._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/reading/shelf/student-001")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Pride and Prejudice"
    assert data[0]["current_page"] == 42


@pytest.mark.asyncio
async def test_get_shelf_empty(client):
    mock_conn = _make_mock_conn(rows=[])
    with patch("app.api.reading_sessions._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.get("/reading/shelf/student-999")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_progress_not_found(client):
    mock_conn = _make_mock_conn(row=None)
    with patch("app.api.reading_sessions._get_conn", new_callable=AsyncMock, return_value=mock_conn):
        resp = await client.patch("/reading/progress", json={
            "student_id": "student-001",
            "book_id": "nonexistent",
            "current_page": 10,
        })
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd adeline-brain && python -m pytest tests/test_reading_sessions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement reading session API**

Create `adeline-brain/app/api/reading_sessions.py`:

```python
"""
Reading Sessions API — StudentBook CRUD for tracking reading progress.

Endpoints:
  POST  /reading/start                    — Start reading a book
  PATCH /reading/progress                 — Update current page
  POST  /reading/finish                   — Mark book as finished
  GET   /reading/shelf/{student_id}       — Student's reading shelf (with book info)
"""
import logging
import os

import asyncpg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reading", tags=["reading"])

_DSN = os.getenv(
    "POSTGRES_DSN",
    os.getenv("DATABASE_URL", "postgresql://adeline:adeline_local_dev@postgres:5432/hippocampus"),
)


async def _get_conn():
    return await asyncpg.connect(_DSN)


_INIT_SQL = """
CREATE TABLE IF NOT EXISTS "StudentBook" (
    "studentId"   TEXT NOT NULL,
    "bookId"      TEXT NOT NULL REFERENCES "Book"(id) ON DELETE CASCADE,
    "startedAt"   TIMESTAMPTZ NOT NULL DEFAULT now(),
    "finishedAt"  TIMESTAMPTZ,
    "currentPage" INT,
    PRIMARY KEY ("studentId", "bookId")
);
CREATE INDEX IF NOT EXISTS idx_student_book_student ON "StudentBook" ("studentId");
"""


async def ensure_table() -> None:
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
    finally:
        await conn.close()


# ── Models ────────────────────────────────────────────────────────────────────

class StartReadingRequest(BaseModel):
    student_id: str
    book_id: str


class UpdateProgressRequest(BaseModel):
    student_id: str
    book_id: str
    current_page: int


class FinishReadingRequest(BaseModel):
    student_id: str
    book_id: str


class ReadingSessionResponse(BaseModel):
    student_id: str
    book_id: str
    started_at: str
    finished_at: Optional[str] = None
    current_page: Optional[int] = None


class ShelfEntryResponse(BaseModel):
    student_id: str
    book_id: str
    title: str
    author: str
    cover_url: Optional[str] = None
    track: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    current_page: Optional[int] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=ReadingSessionResponse)
async def start_reading(body: StartReadingRequest):
    """Start reading a book. Idempotent — re-starting returns existing session."""
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO "StudentBook" ("studentId", "bookId")
            VALUES ($1, $2)
            ON CONFLICT ("studentId", "bookId") DO UPDATE SET "startedAt" = "StudentBook"."startedAt"
            RETURNING "studentId", "bookId", "startedAt"::text, "finishedAt"::text, "currentPage"
            """,
            body.student_id, body.book_id,
        )
    finally:
        await conn.close()

    return ReadingSessionResponse(
        student_id=row["studentId"],
        book_id=row["bookId"],
        started_at=row["startedAt"],
        finished_at=row["finishedAt"],
        current_page=row["currentPage"],
    )


@router.patch("/progress", response_model=ReadingSessionResponse)
async def update_progress(body: UpdateProgressRequest):
    """Update reading progress (current page)."""
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            """
            UPDATE "StudentBook"
            SET "currentPage" = $3
            WHERE "studentId" = $1 AND "bookId" = $2
            RETURNING "studentId", "bookId", "startedAt"::text, "finishedAt"::text, "currentPage"
            """,
            body.student_id, body.book_id, body.current_page,
        )
    finally:
        await conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Reading session not found")

    return ReadingSessionResponse(
        student_id=row["studentId"],
        book_id=row["bookId"],
        started_at=row["startedAt"],
        finished_at=row["finishedAt"],
        current_page=row["currentPage"],
    )


@router.post("/finish", response_model=ReadingSessionResponse)
async def finish_reading(body: FinishReadingRequest):
    """Mark a book as finished."""
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            """
            UPDATE "StudentBook"
            SET "finishedAt" = now()
            WHERE "studentId" = $1 AND "bookId" = $2
            RETURNING "studentId", "bookId", "startedAt"::text, "finishedAt"::text, "currentPage"
            """,
            body.student_id, body.book_id,
        )
    finally:
        await conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Reading session not found")

    return ReadingSessionResponse(
        student_id=row["studentId"],
        book_id=row["bookId"],
        started_at=row["startedAt"],
        finished_at=row["finishedAt"],
        current_page=row["currentPage"],
    )


@router.get("/shelf/{student_id}", response_model=list[ShelfEntryResponse])
async def get_shelf(student_id: str):
    """Get a student's reading shelf with book details."""
    conn = await _get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT sb."studentId", sb."bookId", b.title, b.author,
                   b."coverUrl", b.track,
                   sb."startedAt"::text, sb."finishedAt"::text, sb."currentPage"
            FROM "StudentBook" sb
            JOIN "Book" b ON b.id = sb."bookId"
            WHERE sb."studentId" = $1
            ORDER BY sb."startedAt" DESC
            """,
            student_id,
        )
    finally:
        await conn.close()

    return [
        ShelfEntryResponse(
            student_id=r["studentId"],
            book_id=r["bookId"],
            title=r["title"],
            author=r["author"],
            cover_url=r["coverUrl"],
            track=r["track"],
            started_at=r["startedAt"],
            finished_at=r["finishedAt"],
            current_page=r["currentPage"],
        )
        for r in rows
    ]
```

- [ ] **Step 4: Register router in main.py**

In `adeline-brain/app/main.py`, add import at line 29:

```python
from app.api.reading_sessions import router as reading_sessions_router
```

And register at line 89 (after bookshelf_router):

```python
app.include_router(reading_sessions_router)
```

- [ ] **Step 5: Run tests**

Run: `cd adeline-brain && python -m pytest tests/test_reading_sessions.py -v`
Expected: all 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add adeline-brain/app/api/reading_sessions.py adeline-brain/tests/test_reading_sessions.py adeline-brain/app/main.py
git commit -m "feat(bookshelf): Add reading session API — start, progress, finish, shelf"
```

---

### Task 4: Frontend brain-client reading session functions

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts`

- [ ] **Step 1: Add reading session types and functions**

Append after the bookshelf functions block (after line 707):

```typescript
// ── Reading Session Types ────────────────────────────────────────────────────

export interface ReadingSession {
  student_id: string;
  book_id: string;
  started_at: string;
  finished_at: string | null;
  current_page: number | null;
}

export interface ShelfEntry {
  student_id: string;
  book_id: string;
  title: string;
  author: string;
  cover_url: string | null;
  track: string | null;
  started_at: string;
  finished_at: string | null;
  current_page: number | null;
}

// ── Reading Session Functions ────────────────────────────────────────────────

export async function startReading(studentId: string, bookId: string): Promise<ReadingSession> {
  const res = await fetch(`${BRAIN_URL}/reading/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, book_id: bookId }),
  });
  if (!res.ok) throw new Error(`Failed to start reading: ${res.status}`);
  return res.json();
}

export async function updateProgress(
  studentId: string, bookId: string, currentPage: number,
): Promise<ReadingSession> {
  const res = await fetch(`${BRAIN_URL}/reading/progress`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, book_id: bookId, current_page: currentPage }),
  });
  if (!res.ok) throw new Error(`Failed to update progress: ${res.status}`);
  return res.json();
}

export async function finishReading(studentId: string, bookId: string): Promise<ReadingSession> {
  const res = await fetch(`${BRAIN_URL}/reading/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, book_id: bookId }),
  });
  if (!res.ok) throw new Error(`Failed to finish reading: ${res.status}`);
  return res.json();
}

export async function getShelf(studentId: string): Promise<ShelfEntry[]> {
  const res = await fetch(`${BRAIN_URL}/reading/shelf/${encodeURIComponent(studentId)}`);
  if (!res.ok) throw new Error(`Failed to get shelf: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Run TypeScript check**

Run: `cd adeline-ui && npx tsc --noEmit 2>&1 | grep -i "brain-client"`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/lib/brain-client.ts
git commit -m "feat(bookshelf): Add reading session client functions to brain-client"
```

---

### Task 5: Env config + gitignore

**Files:**
- Modify: `adeline-brain/.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Add Supabase vars to .env.example**

Append after line 37 (before `# ── App`):

```
# ── Supabase Storage (EPUB book files) ───────────────────────────────────────
# Set both to use Supabase Storage. Omit for local filesystem storage.
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

- [ ] **Step 2: Add book storage dir to .gitignore**

Append to `.gitignore`:

```
# EPUB book storage (local dev)
adeline-brain/data/books/
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore adeline-brain/.env.example
git commit -m "chore: Add Supabase Storage env vars and gitignore book storage"
```

---

### Task 6: Update CLAUDE.md — API endpoint table

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add reading session endpoints to API table**

Add to the Key API Endpoints table:

```
| POST | `/reading/start`               | Start reading a book (creates StudentBook) |
| PATCH| `/reading/progress`            | Update current page |
| POST | `/reading/finish`              | Mark book as finished |
| GET  | `/reading/shelf/{student_id}`  | Student's reading shelf with book details |
```

- [ ] **Step 2: Update Known Gaps — remove completed items**

Remove from Known Gaps:
- "projects.py router" line stays (still in progress)
- Remove any mention of bookshelf being placeholder or not production-ready

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: Add reading session endpoints to CLAUDE.md"
```

---

### Task 7: Final integration test

- [ ] **Step 1: Run full bookshelf + reading session test suite**

```bash
cd adeline-brain && python -m pytest tests/test_bookshelf_api.py tests/test_book_fetch.py tests/test_e2e_bookshelf.py tests/test_reading_sessions.py tests/test_storage.py -v
```

Expected: all tests PASS

- [ ] **Step 2: Run TypeScript type check**

```bash
cd adeline-ui && npx tsc --noEmit 2>&1 | grep -i -E "bookshelf|reading|brain-client|BookCard"
```

Expected: no errors

- [ ] **Step 3: Verify no secrets committed**

```bash
git diff HEAD~6 --name-only | grep -i -E "\.env$|secret|credential"
```

Expected: no matches (only .env.example, never .env)
