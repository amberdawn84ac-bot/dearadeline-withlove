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
from app.api.middleware import require_role, get_current_user_id
from app.connections.bookshelf_search import bookshelf_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/books", tags=["books"])

# OpenAI configuration
EMBED_MODEL = "text-embedding-3-small"
from app.config import POSTGRES_DSN as _DSN

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
    """Response wrapper for book recommendations with adaptive level information."""
    recommendations: List[BookRecommendation]
    adaptive_lexile_min: Optional[int] = None
    adaptive_lexile_max: Optional[int] = None
    confidence_score: Optional[float] = None
    based_on_completed_books: Optional[int] = None


# ── Helper Functions ───────────────────────────────────────────────────────

async def _get_conn():
    """Get an asyncpg connection for database queries."""
    from app.config import get_db_conn
    return await get_db_conn()


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


async def _calculate_adaptive_reading_level(student_id: str, grade_level: str) -> tuple:
    """
    Calculate adaptive reading level based on student's actual reading history.
    
    Args:
        student_id: UUID of the student
        grade_level: Official grade level from profile
        
    Returns:
        Tuple of (adaptive_lexile_min, adaptive_lexile_max, confidence_level)
    """
    conn = await _get_conn()
    try:
        # Get completed books with their lexile levels
        completed_books = await conn.fetch(
            """
            SELECT b.lexile_level, rs."pagesRead", rs."totalPages", rs."readingMinutes"
            FROM "ReadingSession" rs
            JOIN "Book" b ON rs."bookId" = b.id
            WHERE rs."studentId" = $1 AND rs.status = 'finished'
            AND b.lexile_level IS NOT NULL
            ORDER BY rs."completedAt" DESC
            LIMIT 10
            """,
            student_id,
        )
        
        if not completed_books:
            # No reading history - use grade level defaults
            base_min, base_max = _get_lexile_range(grade_level)
            return base_min, base_max, 0.0
        
        # Calculate weighted average based on completion rate and time spent
        weighted_lexiles = []
        total_weight = 0
        
        for book in completed_books:
            lexile = book["lexile_level"]
            pages_read = book["pagesRead"] or 0
            total_pages = book["totalPages"] or 1
            reading_minutes = book["readingMinutes"] or 1
            
            # Weight by completion rate and reading engagement
            completion_rate = min(pages_read / total_pages, 1.0)
            engagement_weight = min(reading_minutes / 60.0, 2.0)  # Cap at 2 hours
            weight = completion_rate * engagement_weight
            
            weighted_lexiles.append(lexile * weight)
            total_weight += weight
        
        if total_weight == 0:
            base_min, base_max = _get_lexile_range(grade_level)
            return base_min, base_max, 0.0
        
        # Calculate actual reading level
        actual_lexile = sum(weighted_lexiles) / total_weight
        
        # Calculate confidence based on sample size
        confidence = min(len(completed_books) / 5.0, 1.0)  # Max confidence after 5 books
        
        # Create adaptive range (±200 points around actual level, narrower if high confidence)
        if confidence >= 0.8:
            range_width = 150  # Narrow range for high confidence
        elif confidence >= 0.5:
            range_width = 200  # Medium range
        else:
            range_width = 300  # Wide range for low confidence
        
        adaptive_min = max(200, actual_lexile - range_width)
        adaptive_max = min(1500, actual_lexile + range_width)
        
        logger.info(
            f"[Books] Adaptive reading level for {student_id}: "
            f"actual={actual_lexile:.0f}, range={adaptive_min}-{adaptive_max}, "
            f"confidence={confidence:.2f} (based on {len(completed_books)} books)"
        )
        
        return adaptive_min, adaptive_max, confidence
        
    except Exception as e:
        logger.error(f"[Books] Failed to calculate adaptive reading level: {e}")
        # Fallback to grade level
        base_min, base_max = _get_lexile_range(grade_level)
        return base_min, base_max, 0.0
    finally:
        await conn.close()


async def _log_registrar_tracking(student_id: str, recommendations: list, adaptive_range: tuple, confidence: float):
    """
    Log recommendations for registrar tracking and accountability.
    
    Args:
        student_id: UUID of the student
        recommendations: List of recommended book IDs
        adaptive_range: Tuple of (min_lexile, max_lexile)
        confidence: Confidence level in adaptive reading assessment
    """
    import uuid as _uuid
    conn = await _get_conn()
    try:
        # Log to ReadingRecommendationsLog table for registrar tracking
        await conn.execute(
            """
            INSERT INTO "ReadingRecommendationsLog" (
                id, "studentId", "recommendedBookIds", "adaptiveLexileMin",
                "adaptiveLexileMax", "confidenceScore", "recommendationDate"
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """,
            str(_uuid.uuid4()),
            student_id,
            recommendations,
            int(adaptive_range[0]),
            int(adaptive_range[1]),
            confidence,
        )
        
        logger.info(f"[Books] Logged {len(recommendations)} recommendations for registrar tracking")
        
    except Exception as e:
        # Don't fail the recommendation if logging fails
        logger.warning(f"[Books] Failed to log registrar tracking: {e}")
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
    "/recommendations",
    response_model=RecommendationsResponse,
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))],
)
async def get_recommendations(
    limit: int = Query(12, ge=1, le=12, description="Number of recommendations (max 12)"),
    user_id: str = Depends(get_current_user_id),
) -> RecommendationsResponse:
    """
    Get AI-recommended books based on student profile using pgvector semantic search.

    Query Parameters:
    - limit: Number of recommendations (1-12, default 12)

    Returns:
    - List of recommended books ranked by relevance_score (highest first)

    Errors:
    - 404: Student profile not found
    - 500: OpenAI or database error
    - 200 with empty list if no books match
    """
    x_user_id = user_id
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

        # Step 4: Calculate adaptive reading level based on actual reading history
        adaptive_lexile_min, adaptive_lexile_max, confidence = await _calculate_adaptive_reading_level(
            x_user_id, grade_level or ""
        )
        
        logger.info(
            f"[Books/Recommendations] Adaptive lexile range for {x_user_id}: "
            f"{adaptive_lexile_min}-{adaptive_lexile_max} (confidence: {confidence:.2f})"
        )

        # Step 5: Search books by embedding with adaptive lexile filtering
        logger.info(
            f"[Books/Recommendations] Searching books by embedding "
            f"(limit={limit}, adaptive_lexile={adaptive_lexile_min}-{adaptive_lexile_max})"
        )
        books = await bookshelf_search.search_books_by_embedding(
            embedding=embedding,
            lexile_min=adaptive_lexile_min,
            lexile_max=adaptive_lexile_max,
            limit=limit,
        )

        logger.info(
            f"[Books/Recommendations] Found {len(books)} recommendations for {x_user_id}"
        )

        # Step 6: Convert to BookRecommendation response with adaptive level info
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

        # Step 7: Log for registrar tracking
        recommended_book_ids = [book.id for book in recommendations]
        await _log_registrar_tracking(
            x_user_id, 
            recommended_book_ids, 
            (adaptive_lexile_min, adaptive_lexile_max), 
            confidence
        )

        # Get count of completed books for this student's adaptive level
        conn_count = await _get_conn()
        completed_books_count = await conn_count.fetchval(
            'SELECT COUNT(*) FROM "ReadingSession" WHERE "studentId" = $1 AND status = \'finished\'',
            x_user_id
        )
        await conn_count.close()
        
        logger.debug(
            f"[Books/Recommendations] Returning {len(recommendations)} recommendations"
        )
        return RecommendationsResponse(
            recommendations=recommendations,
            adaptive_lexile_min=adaptive_lexile_min,
            adaptive_lexile_max=adaptive_lexile_max,
            confidence_score=confidence,
            based_on_completed_books=completed_books_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Books/Recommendations] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


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


# ── Helper: gap-weighted book recommendations for learning plan ───────────────


async def get_gap_weighted_recommendations(
    student_id: str,
    grade_level: str,
    interests: list,
    credit_gaps: list,
    weakest_track: str | None,
    is_high_school: bool,
    limit: int = 4,
) -> list:
    """
    Return gap-weighted book recommendations for the learning plan.

    For 9-12 students, books matching tracks with outstanding credit gaps
    are boosted proportionally to the gap remaining.
    For K-8 students, books matching the weakest track get a 1.3x boost.

    Returns list of dicts with keys: id, title, author, track, lexile_level,
    grade_band, cover_url, relevance_score.
    """
    # 1. Build embedding query from grade + interests
    query_text = _format_embedding_query(grade_level, interests)

    # 2. Create embedding
    embedding = await _embed(query_text)
    if not embedding:
        logger.warning("[Books] Empty embedding for gap-weighted recommendations")
        return []

    # 3. Get adaptive lexile range (fall back to static range on error)
    try:
        lexile_min, lexile_max, _ = await _calculate_adaptive_reading_level(
            student_id, grade_level
        )
    except Exception as e:
        logger.warning(f"[Books] Adaptive lexile failed, using static: {e}")
        lexile_min, lexile_max = _get_lexile_range(grade_level)

    # 4. Fetch more candidates than needed for re-ranking
    candidates = await bookshelf_search.search_books_by_embedding(
        embedding, lexile_min, lexile_max, limit=limit * 3
    )
    if not candidates:
        return []

    # 5. Build gap_boost dict
    gap_boost: dict[str, float] = {}

    if is_high_school and credit_gaps:
        # Reverse mapping: bucket → list of tracks
        from app.api.learning_plan import TRACK_TO_BUCKET

        bucket_to_tracks: dict[str, list[str]] = {}
        for track, buckets in TRACK_TO_BUCKET.items():
            if isinstance(buckets, list):
                for b in buckets:
                    bucket_to_tracks.setdefault(b, []).append(track)
            else:
                bucket_to_tracks.setdefault(buckets, []).append(track)

        for gap in credit_gaps:
            bucket = gap.get("bucket", "") if isinstance(gap, dict) else getattr(gap, "bucket", "")
            remaining = gap.get("remaining", 0) if isinstance(gap, dict) else getattr(gap, "remaining", 0)
            if remaining > 0:
                tracks_for_bucket = bucket_to_tracks.get(bucket, [])
                for t in tracks_for_bucket:
                    # Boost proportional to gap: 1.0 base + 0.2 per credit remaining
                    gap_boost[t] = 1.0 + (0.2 * remaining)
    else:
        # K-8: boost weakest track
        if weakest_track:
            gap_boost[weakest_track] = 1.3

    # 6. Re-rank by multiplying relevance_score by boost
    for book in candidates:
        track = book.get("track", "")
        boost = gap_boost.get(track, 1.0)
        book["relevance_score"] = book.get("relevance_score", 0.0) * boost

    candidates.sort(key=lambda b: b.get("relevance_score", 0.0), reverse=True)

    # 7. Deduplicate: max 2 books per track
    track_counts: dict[str, int] = {}
    result: list[dict] = []
    for book in candidates:
        track = book.get("track", "")
        if track_counts.get(track, 0) >= 2:
            continue
        track_counts[track] = track_counts.get(track, 0) + 1
        result.append(book)
        if len(result) >= limit:
            break

    logger.info(
        f"[Books] Gap-weighted recommendations: {len(result)} books for student={student_id}, "
        f"boosts={gap_boost}"
    )
    return result
