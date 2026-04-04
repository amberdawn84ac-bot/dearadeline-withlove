"""
Books API — /api/books/* endpoints for Bookshelf v1
Provides list and detail views of the book catalog with filtering, pagination, and metadata.
"""
import logging
import os
from typing import List, Optional

import asyncpg
import openai
from fastapi import APIRouter, HTTPException, Query, Depends, Header
from pydantic import BaseModel

from app.schemas.api_models import UserRole
from app.api.middleware import require_role
from app.connections.bookshelf_search import bookshelf_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/books", tags=["books"])

# OpenAI configuration
EMBED_MODEL = "text-embedding-3-small"
_DSN = os.getenv("POSTGRES_DSN", "postgresql://adeline:adeline_local_dev@postgres:5432/hippocampus")

# Grade to Lexile mapping for grade-appropriate filtering
GRADE_TO_LEXILE = {
    "K": (250, 350),
    "1": (300, 400),
    "2": (400, 500),
    "3": (500, 600),
    "4": (600, 700),
    "5": (650, 750),
    "6": (700, 800),
    "7": (750, 850),
    "8": (800, 900),
    "9": (850, 950),
    "10": (900, 1000),
    "11": (950, 1050),
    "12": (1000, 1100),
}


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


class BookRecommendation(BaseModel):
    """Book recommendation with relevance score."""
    id: str
    title: str
    author: str
    lexile_level: int
    grade_band: str
    track: str
    cover_url: Optional[str] = None
    relevance_score: float


class RecommendationsResponse(BaseModel):
    """Response wrapper for book recommendations."""
    recommendations: List[BookRecommendation]


# ── Helper Functions ───────────────────────────────────────────────────────

async def _get_conn():
    """Get an asyncpg connection for database queries."""
    return await asyncpg.connect(_DSN)


async def _embed(text: str) -> List[float]:
    """
    Create an embedding vector using OpenAI's text-embedding-3-small model.

    Args:
        text: Text to embed

    Returns:
        1536-dimensional embedding vector

    Raises:
        HTTPException: If embedding fails
    """
    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
        return resp.data[0].embedding
    except openai.APIConnectionError as e:
        logger.error(f"[Books] OpenAI connection failed: {e}")
        raise HTTPException(status_code=500, detail="OpenAI connection error")
    except openai.RateLimitError as e:
        logger.error(f"[Books] OpenAI rate limit: {e}")
        raise HTTPException(status_code=429, detail="OpenAI rate limit exceeded")
    except Exception as e:
        logger.error(f"[Books] Embedding failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create embedding")


async def _fetch_student_profile(user_id: str) -> Optional[dict]:
    """
    Fetch student profile from User table.

    Args:
        user_id: UUID of the student

    Returns:
        Dict with gradeLevel and interests, or None if not found
    """
    conn = await _get_conn()
    try:
        row = await conn.fetchrow(
            'SELECT "gradeLevel", interests FROM "User" WHERE id = $1',
            user_id,
        )
        if not row:
            logger.warning(f"[Books] Student profile not found: {user_id}")
            return None

        return {
            "gradeLevel": row["gradeLevel"],
            "interests": row["interests"] or [],
        }
    except Exception as e:
        logger.error(f"[Books] Failed to fetch student profile: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        await conn.close()


def _format_embedding_query(grade_level: Optional[str], interests: List[str]) -> str:
    """
    Format student profile into a query string for embedding.

    Args:
        grade_level: Student's grade level (e.g., "5")
        interests: List of student interests (e.g., ["Science", "Gardening"])

    Returns:
        Formatted query string for embedding
    """
    # Build a descriptive query based on profile
    parts = []

    if grade_level:
        parts.append(f"Grade {grade_level} student")

    if interests:
        interests_str = ", ".join(interests)
        parts.append(f"interested in {interests_str}")

    # Fallback if no data
    if not parts:
        parts.append("student interested in learning")

    query = " ".join(parts)
    logger.debug(f"[Books] Embedding query: {query}")
    return query


def _get_lexile_range(grade_level: Optional[str]) -> tuple:
    """
    Get lexile range for grade-appropriate filtering.

    Args:
        grade_level: Student's grade level (e.g., "5")

    Returns:
        Tuple of (min_lexile, max_lexile)
    """
    if not grade_level:
        return (250, 1200)  # Broad default range

    # Normalize grade level (handle "K", "1", "10", etc.)
    grade_level = grade_level.strip().upper()

    if grade_level in GRADE_TO_LEXILE:
        return GRADE_TO_LEXILE[grade_level]

    # If grade not found, return broad range
    logger.warning(f"[Books] Unknown grade level: {grade_level}")
    return (250, 1200)


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


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))],
)
async def get_recommendations(
    limit: int = Query(12, ge=1, le=12, description="Number of recommendations (max 12)"),
    x_user_id: str = Header(..., description="User ID from Authorization header"),
) -> RecommendationsResponse:
    """
    Get AI-recommended books based on student profile using pgvector semantic search.

    Query Parameters:
    - limit: Number of recommendations (1-12, default 12)

    Request Headers:
    - X-User-Id: Student UUID (required)

    Returns:
    - List of recommended books ranked by relevance_score (highest first)

    Errors:
    - 404: Student profile not found
    - 500: OpenAI or database error
    - 200 with empty list if no books match
    """
    logger.info(f"[Books/Recommendations] Fetching recommendations for student: {x_user_id}, limit={limit}")

    try:
        # Step 1: Fetch student profile
        profile = await _fetch_student_profile(x_user_id)
        if not profile:
            logger.warning(f"[Books/Recommendations] Student not found: {x_user_id}")
            raise HTTPException(status_code=404, detail="Student profile not found")

        grade_level = profile.get("gradeLevel")
        interests = profile.get("interests", [])

        logger.debug(
            f"[Books/Recommendations] Student profile: grade={grade_level}, "
            f"interests={interests}"
        )

        # Step 2: Format embedding query text
        query_text = _format_embedding_query(grade_level, interests)

        # Step 3: Create embedding via OpenAI
        logger.info(f"[Books/Recommendations] Creating embedding for query")
        embedding = await _embed(query_text)
        logger.debug(f"[Books/Recommendations] Embedding created (dims: {len(embedding)})")

        # Step 4: Get grade-appropriate lexile range
        lexile_min, lexile_max = _get_lexile_range(grade_level)
        logger.debug(
            f"[Books/Recommendations] Lexile range for grade {grade_level}: "
            f"{lexile_min}-{lexile_max}"
        )

        # Step 5: Search books by embedding with lexile filtering
        logger.info(
            f"[Books/Recommendations] Searching books by embedding "
            f"(limit={limit}, lexile={lexile_min}-{lexile_max})"
        )
        books = await bookshelf_search.search_books_by_embedding(
            embedding=embedding,
            lexile_min=lexile_min,
            lexile_max=lexile_max,
            limit=limit,
        )

        logger.info(
            f"[Books/Recommendations] Found {len(books)} recommendations for {x_user_id}"
        )

        # Step 6: Convert to BookRecommendation response
        recommendations = [
            BookRecommendation(
                id=book["id"],
                title=book["title"],
                author=book["author"],
                lexile_level=book["lexile_level"],
                grade_band=book["grade_band"],
                track=book["track"],
                cover_url=book.get("cover_url"),
                relevance_score=book.get("relevance_score", 0.0),
            )
            for book in books
        ]

        logger.debug(
            f"[Books/Recommendations] Returning {len(recommendations)} recommendations"
        )
        return RecommendationsResponse(recommendations=recommendations)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Books/Recommendations] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")
