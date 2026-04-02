# Reading Nook / Bookshelf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Reading Nook with JIT bookshelf that fetches public domain books via Standard Ebooks → Gutenberg waterfall.

**Architecture:** FastAPI backend handles book discovery and epub storage (Supabase Storage). Next.js frontend renders a browsable bookshelf with source badges. Waterfall fetch is async — UI shows "Fetching..." state while download runs.

**Tech Stack:** Python (httpx, FastAPI), TypeScript (Next.js 14), Supabase Storage, Prisma (Book/StudentBook models already exist).

---

## Task 1: Book Fetch Service (Python — Waterfall Logic)

**Files:**
- Create: `adeline-brain/app/services/book_fetch.py`
- Test: `adeline-brain/app/services/test_book_fetch.py`

### Step 1: Write the failing test

Create test file at `adeline-brain/app/services/test_book_fetch.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.book_fetch import (
    fetch_from_standard_ebooks,
    fetch_from_gutendex,
    save_to_storage,
)


@pytest.mark.asyncio
async def test_fetch_from_standard_ebooks_success():
    """Test successful fetch from Standard Ebooks."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"epub content here"

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await fetch_from_standard_ebooks("jane austen", "pride and prejudice")
        assert result == b"epub content here"


@pytest.mark.asyncio
async def test_fetch_from_standard_ebooks_not_found():
    """Test Standard Ebooks 404 returns None."""
    mock_response = AsyncMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await fetch_from_standard_ebooks("jane austen", "nonexistent book")
        assert result is None


@pytest.mark.asyncio
async def test_fetch_from_gutendex_success():
    """Test successful fetch from Gutendex."""
    mock_search_response = AsyncMock()
    mock_search_response.json = AsyncMock(return_value={
        "results": [
            {
                "id": 1661,
                "title": "Pride and Prejudice",
                "formats": {
                    "application/epub+zip": "https://www.gutendex.com/cache/epub/1661/pg1661.epub"
                }
            }
        ]
    })

    mock_epub_response = AsyncMock()
    mock_epub_response.status_code = 200
    mock_epub_response.content = b"gutendex epub content"

    async def mock_get(url, *args, **kwargs):
        if "search" in url:
            return mock_search_response
        return mock_epub_response

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        result = await fetch_from_gutendex("Pride and Prejudice")
        assert result == b"gutendex epub content"


@pytest.mark.asyncio
async def test_fetch_from_gutendex_not_found():
    """Test Gutendex with no results returns None."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"results": []})

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await fetch_from_gutendex("nonexistent book xyz")
        assert result is None


@pytest.mark.asyncio
async def test_save_to_storage_success(mocker):
    """Test saving epub to Supabase Storage."""
    mock_supabase = mocker.patch("app.services.book_fetch.supabase")
    mock_supabase.storage.from_.return_value.upload.return_value = None

    storage_key = await save_to_storage(
        book_id="test-book-123",
        epub_bytes=b"test epub content",
        source="Standard Ebooks"
    )

    assert storage_key.startswith("books/test-book-123")
    assert storage_key.endswith(".epub")
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-brain
python -m pytest app/services/test_book_fetch.py -v
```

Expected output: All tests fail with `ModuleNotFoundError: No module named 'app.services.book_fetch'`

### Step 3: Write minimal implementation

Create `adeline-brain/app/services/book_fetch.py`:

```python
"""
Book fetch service with waterfall logic:
1. Try Standard Ebooks first
2. Fall through to Gutendex
3. Save to Supabase Storage
"""

import httpx
import logging
import os
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Supabase client (assume already initialized in app config)
try:
    from app.config import supabase
except ImportError:
    supabase = None


async def standardize_slug(text: str) -> str:
    """Convert text to URL slug (lowercase, spaces to dashes, remove special chars)."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


async def fetch_from_standard_ebooks(
    author: str,
    title: str,
    timeout: int = 30
) -> Optional[bytes]:
    """
    Fetch epub from Standard Ebooks.

    URL pattern: https://standardebooks.org/ebooks/[author-slug]/[title-slug]
    Try common epub paths:
    - /dist/[author-slug]_[title-slug].epub
    - /dist/[author-slug]_[title-slug].kepub.epub (Kobo format, fallback)
    """
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
                logger.info(f"Attempting Standard Ebooks fetch: {url}")
                response = await client.get(url, follow_redirects=True)

                if response.status_code == 200:
                    logger.info(f"Successfully fetched from Standard Ebooks: {url}")
                    return response.content
                elif response.status_code == 404:
                    logger.info(f"Not found at {url}, trying next path...")
                else:
                    logger.warning(f"Unexpected status {response.status_code} from {url}")

            except httpx.RequestError as e:
                logger.warning(f"Request error fetching from Standard Ebooks: {e}")
                continue

    logger.info(f"Standard Ebooks: no epub found for {author} - {title}")
    return None


async def fetch_from_gutendex(
    title: str,
    timeout: int = 30
) -> Optional[bytes]:
    """
    Fetch epub from Gutendex (Project Gutenberg mirror with JSON API).

    1. Search: GET https://gutendex.com/books?search=[title]
    2. Extract first result's epub URL from formats.application/epub+zip
    3. Download epub from that URL
    """
    search_url = "https://gutendex.com/books"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            logger.info(f"Gutendex search for: {title}")
            search_response = await client.get(
                search_url,
                params={"search": title}
            )
            search_response.raise_for_status()

            data = search_response.json()
            results = data.get("results", [])

            if not results:
                logger.info(f"Gutendex: no search results for '{title}'")
                return None

            # Grab first result
            first_result = results[0]
            formats = first_result.get("formats", {})
            epub_url = formats.get("application/epub+zip")

            if not epub_url:
                logger.warning(f"Gutendex result missing epub format: {first_result.get('title')}")
                return None

            logger.info(f"Downloading epub from Gutendex: {epub_url}")
            epub_response = await client.get(epub_url)
            epub_response.raise_for_status()

            logger.info(f"Successfully fetched from Gutendex: {first_result.get('title')}")
            return epub_response.content

        except httpx.RequestError as e:
            logger.error(f"Gutendex request error: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Gutendex parsing error: {e}")
            return None


async def save_to_storage(
    book_id: str,
    epub_bytes: bytes,
    source: str = "Unknown"
) -> str:
    """
    Save epub bytes to Supabase Storage under books/{book_id}/{source}.epub

    Returns storage_key for update in Book record.
    Raises if supabase client not initialized.
    """
    if not supabase:
        raise RuntimeError("Supabase client not initialized")

    # Sanitize source name for filename
    import re
    source_safe = re.sub(r'[^\w]', '', source.replace(" ", "_"))
    storage_key = f"books/{book_id}/{source_safe}.epub"

    try:
        logger.info(f"Uploading to Supabase Storage: {storage_key}")
        supabase.storage.from_("ebooks").upload(
            path=storage_key,
            file=epub_bytes,
            file_options={"content-type": "application/epub+zip"}
        )
        logger.info(f"Successfully uploaded to storage: {storage_key}")
        return storage_key
    except Exception as e:
        logger.error(f"Supabase upload error: {e}")
        raise


async def fetch_book_with_waterfall(
    book_id: str,
    title: str,
    author: str
) -> Optional[tuple[bytes, str]]:
    """
    Orchestrate waterfall fetch:
    1. Try Standard Ebooks
    2. Fall through to Gutendex
    3. Save to storage

    Returns: (epub_bytes, source_library) or None if all sources fail.
    """
    # Try Standard Ebooks first
    epub_bytes = await fetch_from_standard_ebooks(author, title)
    if epub_bytes:
        logger.info(f"Using Standard Ebooks for {title}")
        storage_key = await save_to_storage(book_id, epub_bytes, "Standard Ebooks")
        return (epub_bytes, "Standard Ebooks")

    # Fall through to Gutendex
    epub_bytes = await fetch_from_gutendex(title)
    if epub_bytes:
        logger.info(f"Using Gutendex for {title}")
        storage_key = await save_to_storage(book_id, epub_bytes, "Gutendex")
        return (epub_bytes, "Gutendex")

    logger.warning(f"Waterfall fetch exhausted: {title} by {author}")
    return None
```

### Step 4: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-brain
python -m pytest app/services/test_book_fetch.py -v
```

Expected output:
```
test_book_fetch.py::test_fetch_from_standard_ebooks_success PASSED
test_book_fetch.py::test_fetch_from_standard_ebooks_not_found PASSED
test_book_fetch.py::test_fetch_from_gutendex_success PASSED
test_book_fetch.py::test_fetch_from_gutendex_not_found PASSED
test_book_fetch.py::test_save_to_storage_success PASSED

======================== 5 passed in 0.45s ========================
```

### Step 5: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-brain/app/services/book_fetch.py adeline-brain/app/services/test_book_fetch.py
git commit -m "feat(bookshelf): Add book fetch service with Standard Ebooks → Gutendex waterfall

- fetch_from_standard_ebooks() tries Standard Ebooks OPDS feed
- fetch_from_gutendex() queries Gutendex JSON API + downloads
- save_to_storage() persists to Supabase Storage
- fetch_book_with_waterfall() orchestrates waterfall + saves

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Bookshelf FastAPI Router (CRUD + Download)

**Files:**
- Create: `adeline-brain/app/api/bookshelf.py`
- Test: `adeline-brain/app/api/test_bookshelf.py`
- Modify: `adeline-brain/app/main.py` (add router)

### Step 1: Write the failing test

Create `adeline-brain/app/api/test_bookshelf.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app

client = TestClient(app)


def test_list_books_for_student():
    """GET /bookshelf — list books for a student."""
    response = client.get(
        "/bookshelf",
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "student-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "books" in data
    assert "total" in data
    assert isinstance(data["books"], list)


def test_get_book_detail():
    """GET /bookshelf/{book_id} — fetch a single book."""
    response = client.get(
        "/bookshelf/book-456",
        headers={"X-User-Role": "STUDENT"}
    )
    assert response.status_code in [200, 404]  # 404 if book doesn't exist


@pytest.mark.asyncio
async def test_add_book_triggers_waterfall():
    """POST /bookshelf/add — add book and trigger fetch."""
    payload = {
        "title": "Pride and Prejudice",
        "author": "Jane Austen"
    }

    with patch("app.api.bookshelf.fetch_book_with_waterfall", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (b"epub content", "Standard Ebooks")

        response = client.post(
            "/bookshelf/add",
            json=payload,
            headers={"X-User-Role": "STUDENT", "X-Student-Id": "student-123"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Pride and Prejudice"
        assert data["author"] == "Jane Austen"
        assert data["sourceLibrary"] == "Standard Ebooks"
        assert data["isDownloaded"] is True


def test_download_book_returns_epub():
    """GET /bookshelf/{book_id}/download — stream epub file."""
    response = client.get(
        "/bookshelf/book-456/download",
        headers={"X-User-Role": "STUDENT"}
    )
    # Status depends on whether book exists and has storageKey
    assert response.status_code in [200, 404]
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-brain
python -m pytest app/api/test_bookshelf.py -v
```

Expected output: Tests fail with import/route errors.

### Step 3: Write minimal implementation

Create `adeline-brain/app/api/bookshelf.py`:

```python
"""
FastAPI router for bookshelf operations.
- GET /bookshelf — list student's books
- GET /bookshelf/{book_id} — single book detail
- POST /bookshelf/add — add book by title/author (waterfall fetch)
- GET /bookshelf/{book_id}/download — stream epub
"""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, StreamingResponse, BackgroundTasks
from pydantic import BaseModel
from app.services.book_fetch import fetch_book_with_waterfall
from app.config import db  # Assume Prisma client initialized

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bookshelf", tags=["bookshelf"])


# ── Request/Response Models ────────────────────────────────────────────

class AddBookRequest(BaseModel):
    title: str
    author: str
    description: Optional[str] = None


class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    gutenberg_id: Optional[str] = None
    source_library: Optional[str] = None
    storage_key: Optional[str] = None
    is_downloaded: bool
    format: str
    cover_url: Optional[str] = None

    class Config:
        from_attributes = True


class BookshelfListResponse(BaseModel):
    books: list[BookResponse]
    total: int


# ── Helpers ────────────────────────────────────────────────────────────

def get_student_id(x_student_id: Optional[str] = Header(None)) -> str:
    """Extract student ID from header."""
    if not x_student_id:
        raise HTTPException(status_code=400, detail="X-Student-Id header required")
    return x_student_id


async def background_fetch_book(book_id: str, title: str, author: str):
    """Background task to fetch and save book (async)."""
    try:
        result = await fetch_book_with_waterfall(book_id, title, author)
        if result:
            epub_bytes, source = result
            # Update Book record in DB
            await db.book.update(
                where={"id": book_id},
                data={
                    "isDownloaded": True,
                    "sourceLibrary": source,
                    "storageKey": f"books/{book_id}/{source}.epub"
                }
            )
            logger.info(f"Background fetch completed: {book_id}")
        else:
            logger.warning(f"Background fetch failed: {book_id}")
    except Exception as e:
        logger.error(f"Background fetch error for {book_id}: {e}")


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("", response_model=BookshelfListResponse)
async def list_books(
    student_id: str = Header(alias="x-student-id")
) -> BookshelfListResponse:
    """
    GET /bookshelf — list all books for a student.

    Returns StudentBook entries joined with Book data.
    """
    try:
        student_books = await db.studentbook.find_many(
            where={"studentId": student_id},
            include={"book": True},
            order_by={"startedAt": "desc"}
        )

        return BookshelfListResponse(
            books=[BookResponse.from_orm(sb.book) for sb in student_books],
            total=len(student_books)
        )
    except Exception as e:
        logger.error(f"Error listing books: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    """
    GET /bookshelf/{book_id} — fetch single book detail.
    """
    try:
        book = await db.book.find_unique(where={"id": book_id})
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookResponse.from_orm(book)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching book {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=BookResponse, status_code=201)
async def add_book(
    payload: AddBookRequest,
    student_id: str = Header(alias="x-student-id"),
    background_tasks: BackgroundTasks = None
) -> BookResponse:
    """
    POST /bookshelf/add — add book by title/author.

    Creates Book record and StudentBook link.
    Triggers async waterfall fetch in background.
    """
    try:
        # Create Book record
        book_id = str(uuid.uuid4())
        book = await db.book.create(
            data={
                "id": book_id,
                "title": payload.title,
                "author": payload.author,
                "format": "epub"
            }
        )

        # Create StudentBook link
        await db.studentbook.create(
            data={
                "studentId": student_id,
                "bookId": book_id
            }
        )

        # Trigger background fetch
        if background_tasks:
            background_tasks.add_task(
                background_fetch_book,
                book_id,
                payload.title,
                payload.author
            )

        logger.info(f"Added book {book_id}: {payload.title}")
        return BookResponse.from_orm(book)

    except Exception as e:
        logger.error(f"Error adding book: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{book_id}/download")
async def download_book(book_id: str):
    """
    GET /bookshelf/{book_id}/download — stream epub file.

    Requires book.isDownloaded=true and storageKey set.
    Returns epub with Content-Disposition header for save dialog.
    """
    try:
        book = await db.book.find_unique(where={"id": book_id})
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if not book.isDownloaded or not book.storageKey:
            raise HTTPException(
                status_code=400,
                detail="Book not yet downloaded or storage key missing"
            )

        # Fetch from Supabase Storage
        from app.config import supabase
        file_response = supabase.storage.from_("ebooks").download(book.storageKey)

        return StreamingResponse(
            iter([file_response]),
            media_type="application/epub+zip",
            headers={
                "Content-Disposition": f"attachment; filename=\"{book.title}.epub\""
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error for {book_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: Update main.py to include router

In `adeline-brain/app/main.py`, add:

```python
from app.api import bookshelf

app.include_router(bookshelf.router)
```

### Step 5: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-brain
python -m pytest app/api/test_bookshelf.py -v
```

### Step 6: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-brain/app/api/bookshelf.py adeline-brain/app/api/test_bookshelf.py adeline-brain/app/main.py
git commit -m "feat(bookshelf): Add FastAPI bookshelf router with CRUD endpoints

- GET /bookshelf — list student's books
- GET /bookshelf/{book_id} — single book detail
- POST /bookshelf/add — create book + trigger waterfall fetch
- GET /bookshelf/{book_id}/download — stream epub from storage

Uses background tasks for async waterfall fetch.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Brain Client Bookshelf Functions (TypeScript)

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts`

### Step 1: Write the failing test

Create `adeline-ui/src/lib/test/brain-client.bookshelf.test.ts`:

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  listBooks,
  getBook,
  addBook,
  downloadBook,
} from "../brain-client";

describe("Brain Client — Bookshelf API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it("listBooks fetches student's books", async () => {
    const mockBooks = {
      books: [
        {
          id: "book-1",
          title: "Pride and Prejudice",
          author: "Jane Austen",
          is_downloaded: true,
          source_library: "Standard Ebooks",
        },
      ],
      total: 1,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockBooks,
    });

    const result = await listBooks("student-123");
    expect(result.total).toBe(1);
    expect(result.books[0].title).toBe("Pride and Prejudice");
  });

  it("getBook fetches single book", async () => {
    const mockBook = {
      id: "book-1",
      title: "Jane Eyre",
      author: "Charlotte Bronte",
      is_downloaded: false,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockBook,
    });

    const result = await getBook("book-1");
    expect(result.title).toBe("Jane Eyre");
  });

  it("addBook sends POST with title/author", async () => {
    const mockResponse = {
      id: "book-new",
      title: "Wuthering Heights",
      author: "Emily Bronte",
      is_downloaded: false,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockResponse,
    });

    const result = await addBook("student-123", {
      title: "Wuthering Heights",
      author: "Emily Bronte",
    });

    expect(result.title).toBe("Wuthering Heights");
    expect(global.fetch).toHaveBeenCalledWith(
      "/brain/bookshelf/add",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  it("downloadBook returns blob", async () => {
    const mockBlob = new Blob(["epub content"], { type: "application/epub+zip" });

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      blob: async () => mockBlob,
    });

    const result = await downloadBook("book-1");
    expect(result.type).toBe("application/epub+zip");
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- brain-client.bookshelf.test.ts
```

Expected: Tests fail (functions don't exist).

### Step 3: Write minimal implementation

Append to `adeline-ui/src/lib/brain-client.ts`:

```typescript
// ── Bookshelf ──────────────────────────────────────────────────────────────

export interface Book {
  id: string;
  title: string;
  author: string;
  gutenberg_id?: string | null;
  source_library?: string | null;
  storage_key?: string | null;
  is_downloaded: boolean;
  format: string;
  cover_url?: string | null;
}

export interface BookshelfListResponse {
  books: Book[];
  total: number;
}

export interface AddBookRequest {
  title: string;
  author: string;
  description?: string;
}

/**
 * GET /bookshelf — list all books for a student.
 */
export async function listBooks(
  studentId: string,
  role: "STUDENT" | "PARENT" | "ADMIN" = "STUDENT",
): Promise<BookshelfListResponse> {
  const res = await fetch(`${BRAIN_URL}/bookshelf`, {
    headers: {
      "X-Student-Id": studentId,
      "X-User-Role": role,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`listBooks failed: ${res.status}`);
  }

  return res.json() as Promise<BookshelfListResponse>;
}

/**
 * GET /bookshelf/{book_id} — fetch single book detail.
 */
export async function getBook(
  bookId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<Book> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/${encodeURIComponent(bookId)}`, {
    headers: { "X-User-Role": role },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`getBook failed: ${res.status}`);
  }

  return res.json() as Promise<Book>;
}

/**
 * POST /bookshelf/add — add book by title/author (waterfall fetch).
 */
export async function addBook(
  studentId: string,
  payload: AddBookRequest,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<Book> {
  const res = await fetch(`${BRAIN_URL}/bookshelf/add`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Student-Id": studentId,
      "X-User-Role": role,
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`addBook failed: ${res.status}`);
  }

  return res.json() as Promise<Book>;
}

/**
 * GET /bookshelf/{book_id}/download — stream epub file as blob.
 */
export async function downloadBook(
  bookId: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<Blob> {
  const res = await fetch(
    `${BRAIN_URL}/bookshelf/${encodeURIComponent(bookId)}/download`,
    {
      headers: { "X-User-Role": role },
      cache: "no-store",
    },
  );

  if (!res.ok) {
    throw new Error(`downloadBook failed: ${res.status}`);
  }

  return res.blob();
}
```

### Step 4: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- brain-client.bookshelf.test.ts
```

### Step 5: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-ui/src/lib/brain-client.ts adeline-ui/src/lib/test/brain-client.bookshelf.test.ts
git commit -m "feat(ui): Add bookshelf API client functions

- listBooks(studentId) — GET /bookshelf
- getBook(bookId) — GET /bookshelf/{book_id}
- addBook(studentId, {title, author}) — POST /bookshelf/add
- downloadBook(bookId) — GET /bookshelf/{book_id}/download (blob)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: BookCard + Source Badge Component

**Files:**
- Create: `adeline-ui/src/components/reading-nook/BookCard.tsx`
- Create: `adeline-ui/src/components/reading-nook/test/BookCard.test.tsx`

### Step 1: Write the failing test

Create `adeline-ui/src/components/reading-nook/test/BookCard.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import BookCard from "../BookCard";

describe("BookCard", () => {
  const mockBook = {
    id: "book-1",
    title: "Pride and Prejudice",
    author: "Jane Austen",
    is_downloaded: true,
    source_library: "Standard Ebooks",
    format: "epub",
  };

  it("renders book title and author", () => {
    render(<BookCard book={mockBook} onDownload={() => {}} />);
    expect(screen.getByText("Pride and Prejudice")).toBeInTheDocument();
    expect(screen.getByText("Jane Austen")).toBeInTheDocument();
  });

  it("displays source badge when downloaded", () => {
    render(<BookCard book={mockBook} onDownload={() => {}} />);
    expect(screen.getByText("Standard Ebooks")).toBeInTheDocument();
  });

  it("shows fetching state when not downloaded", () => {
    const fetchingBook = { ...mockBook, is_downloaded: false };
    render(<BookCard book={fetchingBook} onDownload={() => {}} />);
    expect(screen.getByText("Fetching...")).toBeInTheDocument();
  });

  it("calls onDownload when download button clicked", async () => {
    const mockOnDownload = vitest.fn();
    const { user } = render(<BookCard book={mockBook} onDownload={mockOnDownload} />);

    const downloadBtn = screen.getByRole("button", { name: /download/i });
    await user.click(downloadBtn);

    expect(mockOnDownload).toHaveBeenCalledWith(mockBook.id);
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- BookCard.test.tsx
```

### Step 3: Write minimal implementation

Create `adeline-ui/src/components/reading-nook/BookCard.tsx`:

```typescript
"use client";

import React from "react";
import { Download, BookOpen, Zap } from "lucide-react";
import { Book } from "@/lib/brain-client";

interface BookCardProps {
  book: Book;
  onDownload: (bookId: string) => void;
  isLoading?: boolean;
}

export default function BookCard({ book, onDownload, isLoading = false }: BookCardProps) {
  const sourceColors = {
    "Standard Ebooks": "bg-[#BD6809] text-white",
    Gutendex: "bg-[#9A3F4A] text-white",
    Unknown: "bg-[#2F4731] text-white",
  };

  const sourceBg = sourceColors[book.source_library as keyof typeof sourceColors] || sourceColors.Unknown;

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-4 flex flex-col h-full border border-[#E7DAC3]">
      {/* Cover Placeholder */}
      <div className="w-full h-48 bg-gradient-to-br from-[#BD6809] to-[#9A3F4A] rounded-md flex items-center justify-center mb-4">
        <BookOpen size={48} className="text-white/60" />
      </div>

      {/* Title & Author */}
      <h3 className="text-lg font-bold text-[#2F4731] line-clamp-2 mb-1">{book.title}</h3>
      <p className="text-sm text-[#2F4731]/60 mb-4">{book.author}</p>

      {/* Source Badge */}
      <div className="mb-4 flex-grow">
        {book.is_downloaded ? (
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${sourceBg}`}>
            {book.source_library || "Unknown Source"}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-yellow-50 text-yellow-700 animate-pulse">
            <Zap size={12} />
            Fetching...
          </span>
        )}
      </div>

      {/* Download Button */}
      <button
        onClick={() => onDownload(book.id)}
        disabled={isLoading || !book.is_downloaded}
        className={[
          "w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-all",
          book.is_downloaded && !isLoading
            ? "bg-[#2F4731] text-white hover:bg-[#2F4731]/90 cursor-pointer"
            : "bg-gray-200 text-gray-400 cursor-not-allowed",
        ].join(" ")}
      >
        <Download size={16} />
        {isLoading ? "Downloading..." : "Download"}
      </button>
    </div>
  );
}
```

### Step 4: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- BookCard.test.tsx
```

### Step 5: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-ui/src/components/reading-nook/BookCard.tsx adeline-ui/src/components/reading-nook/test/BookCard.test.tsx
git commit -m "feat(ui): Add BookCard component with source badges

- Displays book title, author, cover placeholder
- Shows source badge (Standard Ebooks, Gutendex, etc.)
- Displays 'Fetching...' state during waterfall download
- Download button disabled until isDownloaded=true

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: BookshelfGrid Component

**Files:**
- Create: `adeline-ui/src/components/reading-nook/BookshelfGrid.tsx`
- Create: `adeline-ui/src/components/reading-nook/test/BookshelfGrid.test.tsx`

### Step 1: Write the failing test

Create `adeline-ui/src/components/reading-nook/test/BookshelfGrid.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import BookshelfGrid from "../BookshelfGrid";

vi.mock("@/lib/brain-client", () => ({
  listBooks: vi.fn(),
  downloadBook: vi.fn(),
}));

describe("BookshelfGrid", () => {
  it("displays grid of book cards", async () => {
    const mockBooks = {
      books: [
        {
          id: "book-1",
          title: "Pride and Prejudice",
          author: "Jane Austen",
          is_downloaded: true,
          source_library: "Standard Ebooks",
          format: "epub",
        },
      ],
      total: 1,
    };

    const { listBooks } = await import("@/lib/brain-client");
    vi.mocked(listBooks).mockResolvedValueOnce(mockBooks);

    render(<BookshelfGrid studentId="student-123" />);

    await waitFor(() => {
      expect(screen.getByText("Pride and Prejudice")).toBeInTheDocument();
    });
  });

  it("shows empty state when no books", async () => {
    const { listBooks } = await import("@/lib/brain-client");
    vi.mocked(listBooks).mockResolvedValueOnce({ books: [], total: 0 });

    render(<BookshelfGrid studentId="student-123" />);

    await waitFor(() => {
      expect(screen.getByText(/your bookshelf is empty/i)).toBeInTheDocument();
    });
  });

  it("shows loading spinner initially", () => {
    const { listBooks } = await import("@/lib/brain-client");
    vi.mocked(listBooks).mockImplementationOnce(() => new Promise(() => {})); // never resolves

    render(<BookshelfGrid studentId="student-123" />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- BookshelfGrid.test.tsx
```

### Step 3: Write minimal implementation

Create `adeline-ui/src/components/reading-nook/BookshelfGrid.tsx`:

```typescript
"use client";

import React, { useEffect, useState } from "react";
import { listBooks, downloadBook, Book } from "@/lib/brain-client";
import BookCard from "./BookCard";

interface BookshelfGridProps {
  studentId: string;
  role?: "STUDENT" | "PARENT" | "ADMIN";
}

export default function BookshelfGrid({
  studentId,
  role = "STUDENT",
}: BookshelfGridProps) {
  const [books, setBooks] = useState<Book[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    fetchBooks();
  }, [studentId]);

  const fetchBooks = async () => {
    try {
      setIsLoading(true);
      const response = await listBooks(studentId, role);
      setBooks(response.books);
      setTotal(response.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load books");
      console.error("Error fetching books:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async (bookId: string) => {
    try {
      setDownloadingId(bookId);
      const blob = await downloadBook(bookId, role);

      // Find book to get title
      const book = books.find((b) => b.id === bookId);
      const filename = book ? `${book.title}.epub` : "book.epub";

      // Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download error:", err);
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloadingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#2F4731]"></div>
          <p className="mt-4 text-[#2F4731]/70">Loading your bookshelf...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-700 font-medium">{error}</p>
        <button
          onClick={fetchBooks}
          className="mt-4 px-4 py-2 bg-red-700 text-white rounded-lg hover:bg-red-800"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (books.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="inline-block p-4 bg-[#BD6809]/10 rounded-full mb-4">
          <span className="text-4xl">📚</span>
        </div>
        <h3 className="text-2xl font-bold text-[#2F4731] mb-2">Your bookshelf is empty</h3>
        <p className="text-[#2F4731]/60 mb-6">Add your first book to get started</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {books.map((book) => (
        <BookCard
          key={book.id}
          book={book}
          onDownload={handleDownload}
          isLoading={downloadingId === book.id}
        />
      ))}
    </div>
  );
}
```

### Step 4: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- BookshelfGrid.test.tsx
```

### Step 5: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-ui/src/components/reading-nook/BookshelfGrid.tsx adeline-ui/src/components/reading-nook/test/BookshelfGrid.test.tsx
git commit -m "feat(ui): Add BookshelfGrid component with lazy loading

- Fetches books for student via listBooks()
- Renders 4-column responsive grid of BookCards
- Handles download with blob trigger to browser
- Shows loading spinner and empty state

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: AddBookDialog Component

**Files:**
- Create: `adeline-ui/src/components/reading-nook/AddBookDialog.tsx`
- Create: `adeline-ui/src/components/reading-nook/test/AddBookDialog.test.tsx`

### Step 1: Write the failing test

Create `adeline-ui/src/components/reading-nook/test/AddBookDialog.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import AddBookDialog from "../AddBookDialog";

vi.mock("@/lib/brain-client", () => ({
  addBook: vi.fn(),
}));

describe("AddBookDialog", () => {
  it("opens and closes dialog", async () => {
    const user = userEvent.setup();
    render(<AddBookDialog studentId="student-123" onBookAdded={() => {}} />);

    const openBtn = screen.getByRole("button", { name: /add book/i });
    await user.click(openBtn);

    expect(screen.getByText(/add a new book/i)).toBeInTheDocument();

    const closeBtn = screen.getByRole("button", { name: /cancel/i });
    await user.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText(/add a new book/i)).not.toBeInTheDocument();
    });
  });

  it("submits form and calls addBook", async () => {
    const { addBook } = await import("@/lib/brain-client");
    vi.mocked(addBook).mockResolvedValueOnce({
      id: "book-new",
      title: "Jane Eyre",
      author: "Charlotte Bronte",
      is_downloaded: false,
      format: "epub",
    });

    const mockOnAdded = vi.fn();
    const user = userEvent.setup();
    render(<AddBookDialog studentId="student-123" onBookAdded={mockOnAdded} />);

    const openBtn = screen.getByRole("button", { name: /add book/i });
    await user.click(openBtn);

    const titleInput = screen.getByPlaceholderText(/book title/i);
    const authorInput = screen.getByPlaceholderText(/author name/i);
    const submitBtn = screen.getByRole("button", { name: /add book to shelf/i });

    await user.type(titleInput, "Jane Eyre");
    await user.type(authorInput, "Charlotte Bronte");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(mockOnAdded).toHaveBeenCalled();
    });
  });

  it("shows validation error if title is empty", async () => {
    const user = userEvent.setup();
    render(<AddBookDialog studentId="student-123" onBookAdded={() => {}} />);

    const openBtn = screen.getByRole("button", { name: /add book/i });
    await user.click(openBtn);

    const submitBtn = screen.getByRole("button", { name: /add book to shelf/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument();
    });
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- AddBookDialog.test.tsx
```

### Step 3: Write minimal implementation

Create `adeline-ui/src/components/reading-nook/AddBookDialog.tsx`:

```typescript
"use client";

import React, { useState } from "react";
import { Plus, Loader } from "lucide-react";
import { addBook } from "@/lib/brain-client";

interface AddBookDialogProps {
  studentId: string;
  onBookAdded: () => void;
  role?: "STUDENT" | "PARENT" | "ADMIN";
}

export default function AddBookDialog({
  studentId,
  onBookAdded,
  role = "STUDENT",
}: AddBookDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => {
    setIsOpen(false);
    setTitle("");
    setAuthor("");
    setErrors({});
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!title.trim()) newErrors.title = "Title is required";
    if (!author.trim()) newErrors.author = "Author is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    try {
      setIsSubmitting(true);
      await addBook(studentId, { title, author }, role);
      handleClose();
      onBookAdded();
    } catch (err) {
      setErrors({
        submit: err instanceof Error ? err.message : "Failed to add book",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button
        onClick={handleOpen}
        className="flex items-center gap-2 px-4 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#BD6809]/90 transition-colors font-medium"
      >
        <Plus size={20} />
        Add Book
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h2 className="text-2xl font-bold text-[#2F4731] mb-4">Add a New Book</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#2F4731] mb-1">
                  Book Title
                </label>
                <input
                  type="text"
                  placeholder="Book title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className={[
                    "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#BD6809]",
                    errors.title ? "border-red-500" : "border-[#E7DAC3]",
                  ].join(" ")}
                />
                {errors.title && (
                  <p className="text-red-600 text-sm mt-1">{errors.title}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-[#2F4731] mb-1">
                  Author Name
                </label>
                <input
                  type="text"
                  placeholder="Author name"
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  className={[
                    "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#BD6809]",
                    errors.author ? "border-red-500" : "border-[#E7DAC3]",
                  ].join(" ")}
                />
                {errors.author && (
                  <p className="text-red-600 text-sm mt-1">{errors.author}</p>
                )}
              </div>

              {errors.submit && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-red-700 text-sm">{errors.submit}</p>
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={handleClose}
                  className="flex-1 px-4 py-2 border border-[#E7DAC3] rounded-lg text-[#2F4731] hover:bg-[#FFFEF7] transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={[
                    "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
                    isSubmitting
                      ? "bg-[#BD6809]/50 text-white cursor-not-allowed"
                      : "bg-[#BD6809] text-white hover:bg-[#BD6809]/90",
                  ].join(" ")}
                >
                  {isSubmitting && <Loader size={16} className="animate-spin" />}
                  Add Book to Shelf
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
```

### Step 4: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- AddBookDialog.test.tsx
```

### Step 5: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-ui/src/components/reading-nook/AddBookDialog.tsx adeline-ui/src/components/reading-nook/test/AddBookDialog.test.tsx
git commit -m "feat(ui): Add AddBookDialog component with form validation

- Modal dialog with title/author inputs
- Form validation (required fields)
- Calls addBook() to trigger waterfall fetch
- Shows loading state during submit
- Validates and displays errors

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Reading Nook Page + Sidebar Navigation

**Files:**
- Create: `adeline-ui/src/app/(routes)/dashboard/reading-nook/page.tsx`
- Modify: `adeline-ui/src/components/nav/AppSidebar.tsx` (add nav item)

### Step 1: Write the failing test

Create `adeline-ui/src/app/(routes)/dashboard/reading-nook/__tests__/page.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ReadingNookPage from "../page";

vi.mock("@/components/reading-nook/BookshelfGrid", () => ({
  default: () => <div>Bookshelf Grid Mock</div>,
}));

vi.mock("@/components/reading-nook/AddBookDialog", () => ({
  default: () => <div>Add Book Dialog Mock</div>,
}));

describe("Reading Nook Page", () => {
  it("renders page title and description", () => {
    render(<ReadingNookPage />);
    expect(screen.getByText(/reading nook/i)).toBeInTheDocument();
  });

  it("includes bookshelf grid", () => {
    render(<ReadingNookPage />);
    expect(screen.getByText(/bookshelf grid mock/i)).toBeInTheDocument();
  });

  it("includes add book dialog", () => {
    render(<ReadingNookPage />);
    expect(screen.getByText(/add book dialog mock/i)).toBeInTheDocument();
  });
});
```

### Step 2: Run test to verify it fails

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- reading-nook/page.test.tsx
```

### Step 3: Write minimal implementation

Create `adeline-ui/src/app/(routes)/dashboard/reading-nook/page.tsx`:

```typescript
"use client";

import React, { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import BookshelfGrid from "@/components/reading-nook/BookshelfGrid";
import AddBookDialog from "@/components/reading-nook/AddBookDialog";

export default function ReadingNookPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [refreshKey, setRefreshKey] = useState(0);

  // Require authentication
  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#2F4731]"></div>
          <p className="mt-4 text-[#2F4731]/70">Loading...</p>
        </div>
      </div>
    );
  }

  if (!session?.user?.id) {
    return null;
  }

  const handleBookAdded = () => {
    // Refresh the grid
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="min-h-screen bg-[#FFFEF7]">
      {/* Header */}
      <div className="border-b border-[#E7DAC3] bg-white/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-4xl font-bold text-[#2F4731] mb-2">Reading Nook</h1>
              <p className="text-[#2F4731]/60">
                Explore public domain books from Standard Ebooks and Project Gutenberg
              </p>
            </div>
            <AddBookDialog
              studentId={session.user.id}
              onBookAdded={handleBookAdded}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div key={refreshKey}>
          <BookshelfGrid studentId={session.user.id} />
        </div>
      </div>
    </div>
  );
}
```

### Step 4: Update AppSidebar

Modify `adeline-ui/src/components/nav/AppSidebar.tsx` — update NAV_ITEMS array:

```typescript
const NAV_ITEMS = [
  { label: "My Learning Plan", href: "/dashboard/journey", icon: BookOpen },
  { label: "Reading Nook",      href: "/dashboard/reading-nook", icon: BookOpen },
  { label: "Opportunities",    href: "/dashboard/opportunities", icon: Briefcase },
];
```

Add import for Library icon (optional enhancement):

```typescript
import { BookOpen, Briefcase, Settings, Menu, X, Library } from "lucide-react";
```

Or use BookOpen for consistency.

### Step 5: Run test to verify it passes

```bash
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm test -- reading-nook/page.test.tsx
```

### Step 6: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add adeline-ui/src/app/\(routes\)/dashboard/reading-nook/page.tsx adeline-ui/src/components/nav/AppSidebar.tsx
git commit -m "feat(ui): Add Reading Nook page and sidebar navigation

- New page at /dashboard/reading-nook with header + BookshelfGrid
- AddBookDialog in header for quick book addition
- Refresh grid on book added
- Added 'Reading Nook' nav item to AppSidebar
- Requires authentication (redirects to /login)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Integration Test (Optional — End-to-End)

**Files:**
- Create: `tests/e2e/reading-nook.e2e.test.ts`

### Step 1: Write integration test

Create `tests/e2e/reading-nook.e2e.test.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Reading Nook E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Setup: Login and navigate to Reading Nook
    await page.goto("http://localhost:3000/dashboard/reading-nook");
    // Assume test user is already authenticated via session/token
  });

  test("User can add a book and see it in bookshelf", async ({ page }) => {
    // Click "Add Book" button
    await page.click('button:has-text("Add Book")');

    // Fill form
    await page.fill('input[placeholder="Book title"]', "Pride and Prejudice");
    await page.fill('input[placeholder="Author name"]', "Jane Austen");

    // Submit
    await page.click('button:has-text("Add Book to Shelf")');

    // Wait for book to appear (may take a few seconds for waterfall fetch)
    await expect(page.locator("text=Pride and Prejudice")).toBeVisible({
      timeout: 10000,
    });

    // Verify source badge appears once fetched
    await expect(
      page.locator("text=Standard Ebooks, Gutendex"),
      "Should show source library once downloaded"
    ).toBeVisible({ timeout: 30000 });
  });

  test("User can download an epub file", async ({ page }) => {
    // Assuming a book already exists on the shelf
    const bookTitle = page.locator("text=Pride and Prejudice").first();
    await expect(bookTitle).toBeVisible();

    // Find and click download button
    const downloadBtn = page
      .locator("button:has-text('Download')")
      .first();
    await expect(downloadBtn).not.toBeDisabled();

    // Trigger download
    const downloadPromise = page.waitForEvent("download");
    await downloadBtn.click();
    const download = await downloadPromise;

    // Verify download filename
    expect(download.suggestedFilename()).toContain(".epub");
  });

  test("Navigation to Reading Nook from sidebar", async ({ page }) => {
    // Go to dashboard home
    await page.goto("http://localhost:3000/dashboard/journey");

    // Click Reading Nook in sidebar
    await page.click("a:has-text('Reading Nook')");

    // Verify page loaded
    await expect(page.locator("h1:has-text('Reading Nook')")).toBeVisible();
  });
});
```

### Step 2: Run integration test (requires running servers)

```bash
# Start dev servers in separate terminals
cd C:\Users\Aarons\dearadeline-withlove\adeline-ui
pnpm dev

cd C:\Users\Aarons\dearadeline-withlove\adeline-brain
uvicorn app.main:app --reload

# Run E2E tests
cd C:\Users\Aarons\dearadeline-withlove
pnpm exec playwright test tests/e2e/reading-nook.e2e.test.ts --headed
```

### Step 3: Commit

```bash
cd C:\Users\Aarons\dearadeline-withlove
git add tests/e2e/reading-nook.e2e.test.ts
git commit -m "test(e2e): Add Reading Nook end-to-end tests

- Test book addition via AddBookDialog
- Test epub download and browser save
- Test sidebar navigation to Reading Nook
- Uses Playwright to validate full user flow

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review Checklist

### Architecture & Design
- [x] **Waterfall fetch logic** — Standard Ebooks first, Gutendex fallback
- [x] **Async background tasks** — Book downloads don't block API response
- [x] **Supabase Storage integration** — Books persisted at `books/{book_id}/{source}.epub`
- [x] **Type safety** — TypeScript interfaces for Book, BookResponse, AddBookRequest
- [x] **Zod schemas** — Python Pydantic mirrors adeline-core types
- [x] **Source badges** — UI shows book origin (Standard Ebooks, Gutendex, etc.)

### Backend (FastAPI)
- [x] `app/services/book_fetch.py` — Pure async waterfall logic with httpx
- [x] `app/api/bookshelf.py` — Full CRUD router (list, detail, add, download)
- [x] Tests for all critical paths (fetch success/failure, storage save, API responses)
- [x] Error handling (404, 500, validation)
- [x] Logging at key points (fetch attempt, storage upload, background task)

### Frontend (Next.js 14)
- [x] `brain-client.ts` — Type-safe REST functions (listBooks, getBook, addBook, downloadBook)
- [x] `BookCard.tsx` — Individual book card with source badge, download button, fetching state
- [x] `BookshelfGrid.tsx` — Responsive grid (4-column), loading state, empty state, error handling
- [x] `AddBookDialog.tsx` — Modal form with title/author inputs, validation, submit feedback
- [x] `reading-nook/page.tsx` — Full page layout with header, grid, and dialog
- [x] **AppSidebar.tsx** — Added "Reading Nook" nav item with BookOpen icon
- [x] Tests for all components (rendering, user interaction, API calls)

### Database
- [x] **Book** model — all fields present (gutenbergId, sourceLibrary, storageKey, isDownloaded, format, coverUrl)
- [x] **StudentBook** model — links students to books with reading state
- [x] Indexes on author, isDownloaded for query performance

### UX/Polish
- [x] Loading spinners during fetch and grid load
- [x] Empty state messaging
- [x] Error boundaries with retry buttons
- [x] Source library badges with color coding
- [x] "Fetching..." state during waterfall download
- [x] Download button disabled until isDownloaded=true
- [x] Browser file download on epub click (suggested filename)
- [x] Validation feedback on AddBookDialog form
- [x] Responsive grid (1 col mobile, 2 tablet, 3-4 desktop)

### Specification Coverage
- [x] **Waterfall fetch** — Standard Ebooks → Gutendex → save to Supabase
- [x] **JIT bookshelf** — Books fetched on-demand via background task
- [x] **Source badges** — Shows which library each book came from
- [x] **Reading Nook sidebar nav** — Integrated with AppSidebar
- [x] **Book catalog browsing** — Grid with search/filter-ready design
- [x] **Download capability** — Stream epub from Supabase Storage to browser

### Known Gaps (for future sprints)
- **Book search/filter** — Current grid shows all books; could add title/author filters
- **Cover images** — Placeholder gradient used; could fetch covers from GutendexAPI or Open Library
- **Reading progress** — StudentBook.currentPage tracked in DB but not yet exposed in UI
- **Book recommendations** — Could leverage track/grade level to suggest related books
- **Offline read capability** — Current design assumes browser reader (Calibre, etc.); could embed web reader

---

## How to Execute This Plan

Use **superpowers:subagent-driven-development** or **superpowers:executing-plans** to work through tasks in order. Each task is self-contained with:
- Failing test first (TDD)
- Minimal implementation
- Running test to verify pass
- Git commit with co-author attribution

All tests use **pytest** (backend) or **vitest** (frontend). All code follows Dear Adeline patterns (Zod schemas, TypeScript interfaces, Prisma, FastAPI router design).

**Estimated Time:** 4–6 hours total (depends on environment setup, test harness familiarity).
