"""
Reading Session API — /api/reading-session endpoints for Bookshelf v1
Manages reading sessions: start books, update progress, mark complete, view shelf.

Endpoints:
  POST /api/reading-session               — Start a new reading session
  PATCH /api/reading-session/{id}        — Update session progress/status
  GET /api/reading-session                — Get student's bookshelf (grouped by status)

All endpoints require Authorization header with student_id or X-User-Id header.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from app.api.middleware import get_current_user_id


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reading-session", tags=["reading-session"])


# ── Request / Response Models ───────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    """Request to start a new reading session."""
    book_id: str = Field(..., description="UUID of the book")
    status: str = Field(default="reading", description="Status: 'reading', 'finished', or 'wishlist'")


class SessionResponse(BaseModel):
    """Response from POST (create) and PATCH (update)."""
    id: str
    student_id: str
    book_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    pages_read: int = 0
    total_pages: Optional[int] = None
    current_location: Optional[str] = None
    student_reflection: Optional[str] = None
    reading_minutes: int = 0


class BookInShelf(BaseModel):
    """Book metadata included in shelf response."""
    id: str
    title: str
    author: str
    lexile_level: Optional[int] = None
    track: Optional[str] = None
    cover_url: Optional[str] = None


class SessionDetailResponse(BaseModel):
    """Session with embedded book details for shelf view."""
    id: str
    book_id: str
    book: BookInShelf
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    pages_read: int = 0
    total_pages: Optional[int] = None
    current_location: Optional[str] = None
    student_reflection: Optional[str] = None
    reading_minutes: int = 0


class ShelfResponse(BaseModel):
    """Grouped reading sessions by status."""
    reading: List[SessionDetailResponse] = []
    finished: List[SessionDetailResponse] = []
    wishlist: List[SessionDetailResponse] = []


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


from contextlib import asynccontextmanager

@asynccontextmanager
async def _get_conn():
    """Get an asyncpg connection for reading session queries."""
    from app.config import get_db_conn
    conn = await get_db_conn()
    try:
        yield conn
    finally:
        await conn.close()


# ── POST /api/reading-session ────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=SessionResponse)
async def create_reading_session(
    payload: SessionCreateRequest,
    student_id: str = Depends(get_current_user_id),
) -> SessionResponse:
    """
    Start a new reading session for a book.

    Request Body:
    - book_id: UUID of the book to start reading
    - status: 'reading', 'finished', or 'wishlist' (default: 'reading')

    Returns:
    - 201 Created with new session details
    - 409 Conflict if session already exists (with existing session_id in detail)

    Errors:
    - 401: Missing/invalid Authorization
    - 404: Book not found
    - 500: Database error
    """

    # Validate status
    valid_statuses = {"reading", "finished", "wishlist"}
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {valid_statuses}",
        )

    now = _now_iso()
    session_id = str(uuid.uuid4())

    async with _get_conn() as conn:
        # Check if book exists
        book_row = await conn.fetchrow(
            'SELECT id FROM "Book" WHERE id = $1',
            payload.book_id,
        )
        if not book_row:
            logger.warning(f"[ReadingSession] Book not found: {payload.book_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Book not found: {payload.book_id}",
            )

        # Try to insert new session with ON CONFLICT DO NOTHING
        result = await conn.fetchrow(
            """
            INSERT INTO "ReadingSession" (
                id, "studentId", "bookId", status, "startedAt", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5::timestamp, $6::timestamp, $7::timestamp)
            ON CONFLICT ("studentId", "bookId") DO NOTHING
            RETURNING id, "studentId", "bookId", status, "startedAt",
                      "completedAt", "pagesRead", "totalPages",
                      "currentLocation", "studentReflection", "readingMinutes"
            """,
            session_id, student_id, payload.book_id, payload.status, now, now, now,
        )

        # If no rows returned, session already exists — fetch it
        if not result:
            existing = await conn.fetchrow(
                """
                SELECT id, "studentId", "bookId", status, "startedAt",
                       "completedAt", "pagesRead", "totalPages",
                       "currentLocation", "studentReflection", "readingMinutes"
                FROM "ReadingSession"
                WHERE "studentId" = $1 AND "bookId" = $2
                """,
                student_id, payload.book_id,
            )

            if existing:
                logger.info(
                    f"[ReadingSession] Session already exists: "
                    f"student={student_id}, book={payload.book_id}, session={existing['id']}"
                )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Reading session already exists for this book",
                        "session_id": existing["id"],
                    },
                )
            else:
                # Should not happen, but handle gracefully
                logger.error(
                    f"[ReadingSession] Unexpected state: "
                    f"insert returned no rows but select also returned no rows"
                )
                raise HTTPException(status_code=500, detail="Database error")

    logger.info(
        f"[ReadingSession] Created session: "
        f"id={session_id}, student={student_id}, book={payload.book_id}, status={payload.status}"
    )

    return SessionResponse(
        id=result["id"],
        student_id=result["studentId"],
        book_id=result["bookId"],
        status=result["status"],
        started_at=result["startedAt"].isoformat() if result["startedAt"] else None,
        completed_at=result["completedAt"].isoformat() if result["completedAt"] else None,
        pages_read=result["pagesRead"] or 0,
        total_pages=result["totalPages"],
        current_location=result["currentLocation"],
        student_reflection=result["studentReflection"],
        reading_minutes=result["readingMinutes"] or 0,
    )


# ── PATCH /api/reading-session/{id} ──────────────────────────────────────────────

class SessionUpdateRequest(BaseModel):
    """Request to update a reading session (all fields optional)."""
    status: Optional[str] = None
    current_location: Optional[str] = None
    pages_read: Optional[int] = None
    reading_minutes: Optional[int] = None
    student_reflection: Optional[str] = None
    total_pages: Optional[int] = None


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_reading_session(
    session_id: str,
    payload: SessionUpdateRequest,
    student_id: str = Depends(get_current_user_id),
) -> SessionResponse:
    """
    Update a reading session's progress or mark it complete.

    URL Parameters:
    - session_id: UUID of the session to update

    Request Body (all optional):
    - status: New status ('reading', 'finished', 'wishlist')
    - current_location: EPUB CFI or page reference
    - pages_read: Pages read so far
    - total_pages: Total pages in book (can be set on first update)
    - reading_minutes: Cumulative reading time
    - student_reflection: Student's note/rating

    Returns:
    - 200 OK with updated session
    - Auto-sets completed_at when status='finished' (if not already set)

    Errors:
    - 401: Missing/invalid Authorization
    - 403: Session doesn't belong to this student
    - 404: Session not found
    - 422: Invalid status value
    - 500: Database error
    """

    # Validate status if provided
    if payload.status is not None:
        valid_statuses = {"reading", "finished", "wishlist"}
        if payload.status not in valid_statuses:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {valid_statuses}",
            )

    now = _now_iso()

    async with _get_conn() as conn:
        # Verify session exists and belongs to student (security check)
        existing = await conn.fetchrow(
            """
            SELECT "studentId", status, "completedAt"
            FROM "ReadingSession"
            WHERE id = $1
            """,
            session_id,
        )

        if not existing:
            logger.warning(f"[ReadingSession] Session not found: {session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Reading session not found: {session_id}",
            )

        if existing["studentId"] != student_id:
            logger.warning(
                f"[ReadingSession] Unauthorized update attempt: "
                f"session={session_id}, requester={student_id}, owner={existing['studentId']}"
            )
            raise HTTPException(
                status_code=403,
                detail="This reading session does not belong to you",
            )

        # Build dynamic UPDATE with only non-null fields
        # Auto-set completed_at if transitioning to finished
        update_cols = ["\"updatedAt\" = $11::timestamp"]
        params = [now]  # param 11
        param_idx = 1

        if payload.status is not None:
            update_cols.append(f"status = ${param_idx}::text")
            params.insert(0, payload.status)
            param_idx += 1

        if payload.current_location is not None:
            update_cols.append(f'"currentLocation" = ${param_idx}::text')
            params.insert(param_idx - 1, payload.current_location)
            param_idx += 1

        if payload.pages_read is not None:
            update_cols.append(f'"pagesRead" = ${param_idx}::int')
            params.insert(param_idx - 1, payload.pages_read)
            param_idx += 1

        if payload.reading_minutes is not None:
            update_cols.append(f'"readingMinutes" = ${param_idx}::int')
            params.insert(param_idx - 1, payload.reading_minutes)
            param_idx += 1

        if payload.student_reflection is not None:
            update_cols.append(f'"studentReflection" = ${param_idx}::text')
            params.insert(param_idx - 1, payload.student_reflection)
            param_idx += 1

        if payload.total_pages is not None:
            update_cols.append(f'"totalPages" = ${param_idx}::int')
            params.insert(param_idx - 1, payload.total_pages)
            param_idx += 1

        # Auto-set completed_at if status is 'finished' and not already set
        if payload.status == "finished" and not existing["completedAt"]:
            update_cols.append(f'"completedAt" = ${param_idx}::timestamp')
            params.insert(param_idx - 1, now)
            param_idx += 1

        # Build final query
        update_clause = ", ".join(update_cols)
        params.append(session_id)  # final WHERE clause
        params.append(student_id)   # WHERE "studentId" = $N

        query = f"""
            UPDATE "ReadingSession"
            SET {update_clause}
            WHERE id = ${param_idx}::uuid AND "studentId" = ${param_idx + 1}::uuid
            RETURNING id, "studentId", "bookId", status, "startedAt",
                      "completedAt", "pagesRead", "totalPages",
                      "currentLocation", "studentReflection", "readingMinutes"
        """

        result = await conn.fetchrow(query, *params)

        if not result:
            logger.error(
                f"[ReadingSession] Update returned no rows: "
                f"session={session_id}, student={student_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to update session")

        # ── Award reading credit if finished with reflection ─────────
        if (
            result["status"] == "finished"
            and result["studentReflection"]
            and result["studentReflection"].strip()
        ):
            try:
                from app.services.reading_credit import award_reading_credit
                book_row = await conn.fetchrow(
                    'SELECT title, track, lexile_level FROM "Book" WHERE id = $1',
                    result["bookId"],
                )
                if book_row:
                    student_row = await conn.fetchrow(
                        'SELECT "gradeLevel" FROM "User" WHERE id = $1',
                        student_id,
                    )
                    grade_level = int(student_row["gradeLevel"]) if student_row and student_row["gradeLevel"] else 8

                    credit_result = await award_reading_credit(
                        session_id=session_id,
                        student_id=student_id,
                        book_id=str(result["bookId"]),
                        book_title=book_row["title"],
                        book_track=book_row["track"] or "ELECTIVES",
                        book_lexile=book_row["lexile_level"] or 0,
                        reading_minutes=result["readingMinutes"] or 0,
                        student_reflection=result["studentReflection"],
                        grade_level=grade_level,
                        completed_at=result["completedAt"],
                    )
                    logger.info(f"[ReadingSession] Credit awarded: {credit_result}")
            except Exception as e:
                logger.error(f"[ReadingSession] Credit award failed: {e}")

    logger.info(
        f"[ReadingSession] Updated session: "
        f"id={session_id}, student={student_id}, "
        f"status={result['status']}, pages={result['pagesRead']}"
    )

    return SessionResponse(
        id=result["id"],
        student_id=result["studentId"],
        book_id=result["bookId"],
        status=result["status"],
        started_at=result["startedAt"].isoformat() if result["startedAt"] else None,
        completed_at=result["completedAt"].isoformat() if result["completedAt"] else None,
        pages_read=result["pagesRead"] or 0,
        total_pages=result["totalPages"],
        current_location=result["currentLocation"],
        student_reflection=result["studentReflection"],
        reading_minutes=result["readingMinutes"] or 0,
    )


# ── GET /api/reading-session ─────────────────────────────────────────────────────

@router.get("", response_model=ShelfResponse)
async def get_reading_shelf(
    status: Optional[str] = Query(None, description="Filter by status: 'reading', 'finished', 'wishlist', or None for all"),
    student_id: str = Depends(get_current_user_id),
) -> ShelfResponse:
    """
    Get student's bookshelf: all reading sessions grouped by status.

    Query Parameters:
    - status: Optional filter ('reading', 'finished', 'wishlist', or None for all)

    Returns:
    - ShelfResponse with reading/finished/wishlist arrays
    - Each session includes book details (title, author, lexile, track, cover)

    Errors:
    - 401: Missing/invalid Authorization
    - 500: Database error
    """

    if status is not None:
        valid_statuses = {"reading", "finished", "wishlist"}
        if status not in valid_statuses:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {valid_statuses}",
            )

    try:
        async with _get_conn() as conn:
            # Query all sessions for this student (optionally filtered by status)
            if status:
                rows = await conn.fetch(
                    """
                    SELECT
                        rs.id, rs."studentId", rs."bookId", rs.status,
                        rs."startedAt", rs."completedAt", rs."pagesRead", rs."totalPages",
                        rs."currentLocation", rs."studentReflection", rs."readingMinutes",
                        b.id as book_id, b.title, b.author, b."gutenbergId",
                        b."lexileLevel", b.track, b."coverUrl"
                    FROM "ReadingSession" rs
                    JOIN "Book" b ON rs."bookId" = b.id
                    WHERE rs."studentId" = $1 AND rs.status = $2
                    ORDER BY rs."startedAt" DESC
                    """,
                    student_id, status,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT
                        rs.id, rs."studentId", rs."bookId", rs.status,
                        rs."startedAt", rs."completedAt", rs."pagesRead", rs."totalPages",
                        rs."currentLocation", rs."studentReflection", rs."readingMinutes",
                        b.id as book_id, b.title, b.author, b."gutenbergId",
                        b."lexileLevel", b.track, b."coverUrl"
                    FROM "ReadingSession" rs
                    JOIN "Book" b ON rs."bookId" = b.id
                    WHERE rs."studentId" = $1
                    ORDER BY rs."startedAt" DESC
                    """,
                    student_id,
                )

        # Group by status
        reading_sessions = []
        finished_sessions = []
        wishlist_sessions = []

        for row in rows:
            session = SessionDetailResponse(
                id=row["id"],
                book_id=row["bookId"],
                book=BookInShelf(
                    id=row["book_id"],
                    title=row["title"],
                    author=row["author"],
                    lexile_level=row.get("lexileLevel"),
                    track=row.get("track"),
                    cover_url=row.get("coverUrl"),
                ),
                started_at=row["startedAt"].isoformat() if row["startedAt"] else None,
                completed_at=row["completedAt"].isoformat() if row["completedAt"] else None,
                pages_read=row["pagesRead"] or 0,
                total_pages=row["totalPages"],
                current_location=row["currentLocation"],
                student_reflection=row["studentReflection"],
                reading_minutes=row["readingMinutes"] or 0,
            )

            if row["status"] == "reading":
                reading_sessions.append(session)
            elif row["status"] == "finished":
                finished_sessions.append(session)
            elif row["status"] == "wishlist":
                wishlist_sessions.append(session)

        logger.info(
            f"[ReadingSession/Shelf] Retrieved shelf for student={student_id}: "
            f"reading={len(reading_sessions)}, finished={len(finished_sessions)}, "
            f"wishlist={len(wishlist_sessions)}"
        )

        return ShelfResponse(
            reading=reading_sessions,
            finished=finished_sessions,
            wishlist=wishlist_sessions,
        )
    
    except Exception as e:
        logger.error(f"[ReadingSession/Shelf] Failed to fetch shelf for student={student_id}: {e}")
        # Return empty shelf instead of 500 error
        return ShelfResponse(
            reading=[],
            finished=[],
            wishlist=[],
        )
