"""
Bookshelf API — book CRUD and download endpoints.

Endpoints:
  GET    /bookshelf                   — List all books (with optional track filter)
  GET    /bookshelf/{book_id}         — Get a single book's details
  POST   /bookshelf/add               — Add a book by title/author, trigger waterfall fetch
  GET    /bookshelf/{book_id}/download — Download the EPUB file
"""
import logging
import os
import uuid

import asyncpg
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response
from pydantic import BaseModel
from typing import Optional

from app.services.book_fetch import fetch_book_with_waterfall

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bookshelf", tags=["bookshelf"])

from app.config import POSTGRES_DSN as _DSN

from app.services.storage import upload_epub, download_epub


async def _get_conn():
    from app.config import get_db_conn
    return await get_db_conn()


# ── Ensure Book table exists (dev safety net — Prisma migrations are canonical) ─

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS "Book" (
    id             TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    author         TEXT NOT NULL,
    "gutenbergId"  TEXT UNIQUE,
    "sourceLibrary" TEXT,
    "downloadUrl"  TEXT,
    "storageKey"   TEXT,
    "isDownloaded" BOOLEAN NOT NULL DEFAULT FALSE,
    format         TEXT NOT NULL DEFAULT 'epub',
    "coverUrl"     TEXT,
    source_url     TEXT UNIQUE,
    lexile_level   INT,
    grade_band     TEXT,
    description    TEXT,
    track          TEXT NOT NULL DEFAULT '',
    "createdAt"    TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt"    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def ensure_table() -> None:
    conn = await _get_conn()
    try:
        await conn.execute(_INIT_SQL)
    finally:
        await conn.close()


# ── Models ────────────────────────────────────────────────────────────────────

class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    sourceLibrary: Optional[str] = None
    isDownloaded: bool = False
    format: str = "epub"
    coverUrl: Optional[str] = None
    track: Optional[str] = None
    lexile_level: Optional[int] = None
    grade_band: Optional[str] = None
    description: Optional[str] = None


class AddBookRequest(BaseModel):
    title: str
    author: str


class AddBookResponse(BaseModel):
    id: str
    title: str
    author: str
    status: str  # "fetching" | "downloaded" | "not_found"
    sourceLibrary: Optional[str] = None


# ── Background waterfall fetch ────────────────────────────────────────────────

async def _run_waterfall(book_id: str, title: str, author: str):
    """Background task: fetch EPUB via waterfall, update Book row."""
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[BookResponse])
async def list_books(track: Optional[str] = Query(None, description="Filter by curriculum track")):
    """List all books, optionally filtered by track."""
    conn = await _get_conn()
    try:
        if track:
            rows = await conn.fetch(
                """
                SELECT id, title, author, "sourceLibrary", "isDownloaded",
                       format, "coverUrl", track, lexile_level, grade_band, description
                FROM "Book"
                WHERE track = $1
                ORDER BY title
                """,
                track,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, title, author, "sourceLibrary", "isDownloaded",
                       format, "coverUrl", track, lexile_level, grade_band, description
                FROM "Book"
                ORDER BY title
                """
            )
        return [
            BookResponse(
                id=str(r["id"]),
                title=r["title"],
                author=r["author"],
                sourceLibrary=r["sourceLibrary"],
                isDownloaded=r["isDownloaded"],
                format=r["format"],
                coverUrl=r["coverUrl"],
                track=r["track"],
                lexile_level=r["lexile_level"],
                grade_band=r["grade_band"],
                description=r["description"],
            )
            for r in rows
        ]
    finally:
        await conn.close()


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    """Get a single book's details."""
    conn = await _get_conn()
    try:
        r = await conn.fetchrow(
            """
            SELECT id, title, author, "sourceLibrary", "isDownloaded",
                   format, "coverUrl", track, lexile_level, grade_band, description
            FROM "Book"
            WHERE id = $1
            """,
            book_id,
        )
        if not r:
            raise HTTPException(status_code=404, detail="Book not found")
        return BookResponse(
            id=str(r["id"]),
            title=r["title"],
            author=r["author"],
            sourceLibrary=r["sourceLibrary"],
            isDownloaded=r["isDownloaded"],
            format=r["format"],
            coverUrl=r["coverUrl"],
            track=r["track"],
            lexile_level=r["lexile_level"],
            grade_band=r["grade_band"],
            description=r["description"],
        )
    finally:
        await conn.close()


@router.post("/add", response_model=AddBookResponse)
async def add_book(request: AddBookRequest, background_tasks: BackgroundTasks):
    """Add a book by title/author — triggers waterfall download in background."""
    book_id = str(uuid.uuid4())
    conn = await _get_conn()
    try:
        await conn.execute(
            """
            INSERT INTO "Book" (id, title, author, track, "updatedAt")
            VALUES ($1, $2, $3, '', now())
            """,
            book_id, request.title, request.author,
        )
    finally:
        await conn.close()

    background_tasks.add_task(_run_waterfall, book_id, request.title, request.author)

    return AddBookResponse(
        id=book_id,
        title=request.title,
        author=request.author,
        status="fetching",
        sourceLibrary=None,
    )


@router.get("/{book_id}/download")
async def download_book(book_id: str):
    """Download the EPUB file for a book."""
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
