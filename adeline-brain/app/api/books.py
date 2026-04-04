"""
Books API — /api/books/* endpoints for Bookshelf v1
Provides list and detail views of the book catalog with filtering, pagination, and metadata.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.schemas.api_models import UserRole
from app.api.middleware import require_role
from app.connections.bookshelf_search import bookshelf_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/books", tags=["books"])


# ── Pydantic Schemas ───────────────────────────────────────────────────────

class BookListItem(BaseModel):
    """Book summary for list view (no description, no source_url)."""
    id: str
    title: str
    author: str
    lexile_level: int
    grade_band: str
    track: str
    cover_url: Optional[str] = None
    source_library: Optional[str] = None


class BookListResponse(BaseModel):
    """Response wrapper for paginated book list."""
    books: List[BookListItem]
    total: int


class BookDetailResponse(BaseModel):
    """Full book metadata (includes description and source_url)."""
    id: str
    title: str
    author: str
    description: Optional[str] = None
    lexile_level: int
    grade_band: str
    track: str
    cover_url: Optional[str] = None
    source_url: Optional[str] = None
    source_library: Optional[str] = None
    total_pages: Optional[int] = None


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=BookListResponse,
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))],
)
async def list_books(
    track: Optional[str] = Query(None, description="Filter by curriculum track (e.g., ENGLISH_LITERATURE)"),
    lexile_min: Optional[int] = Query(None, description="Minimum reading level (e.g., 600)"),
    lexile_max: Optional[int] = Query(None, description="Maximum reading level (e.g., 800)"),
    source_library: Optional[str] = Query(None, description="Filter by source library (e.g., Standard Ebooks)"),
    limit: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> BookListResponse:
    """
    List books from the catalog with optional filtering.

    Query Parameters:
    - track: Filter by track (optional)
    - lexile_min: Minimum reading level (optional)
    - lexile_max: Maximum reading level (optional)
    - source_library: Filter by source (optional)
    - limit: Results per page (1-100, default 50)
    - offset: Pagination offset (default 0)

    Returns:
    - List of BookListItem objects (paginated)
    - Total count of matching books
    """
    logger.info(
        f"[Books] Listing books: track={track}, "
        f"lexile={lexile_min}-{lexile_max}, library={source_library}, "
        f"limit={limit}, offset={offset}"
    )

    try:
        # Enforce limit max
        if limit > 100:
            limit = 100

        # Call bookshelf_search.list_books()
        books, total = await bookshelf_search.list_books(
            track=track,
            lexile_min=lexile_min,
            lexile_max=lexile_max,
            source_library=source_library,
            limit=limit,
            offset=offset,
        )

        # Convert to BookListItem (exclude description and source_url for list view)
        items = [
            BookListItem(
                id=book["id"],
                title=book["title"],
                author=book["author"],
                lexile_level=book["lexile_level"],
                grade_band=book["grade_band"],
                track=book["track"],
                cover_url=book.get("cover_url"),
                source_library=book.get("source_library"),
            )
            for book in books
        ]

        logger.debug(f"[Books] Retrieved {len(items)} books (total: {total})")
        return BookListResponse(books=items, total=total)

    except Exception as e:
        logger.error(f"[Books] List failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve books")


@router.get(
    "/{book_id}",
    response_model=BookDetailResponse,
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))],
)
async def get_book(book_id: str) -> BookDetailResponse:
    """
    Get full book metadata by ID.

    URL Parameters:
    - book_id: UUID of the book

    Returns:
    - Full BookDetailResponse with description, source_url, and page count

    Errors:
    - 404: Book not found
    - 500: Database error
    """
    logger.info(f"[Books] Fetching book: {book_id}")

    try:
        book = await bookshelf_search.get_book_by_id(book_id)

        if not book:
            logger.warning(f"[Books] Book not found: {book_id}")
            raise HTTPException(
                status_code=404,
                detail="Book not found",
            )

        response = BookDetailResponse(
            id=book["id"],
            title=book["title"],
            author=book["author"],
            description=book.get("description"),
            lexile_level=book["lexile_level"],
            grade_band=book["grade_band"],
            track=book["track"],
            cover_url=book.get("cover_url"),
            source_url=book.get("source_url"),
            source_library=book.get("source_library"),
            total_pages=book.get("total_pages"),
        )

        logger.debug(f"[Books] Retrieved book: {book['title']}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Books] Fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve book details")
