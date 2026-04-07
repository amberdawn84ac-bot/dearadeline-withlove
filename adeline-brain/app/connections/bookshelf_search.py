"""
Bookshelf Search — pgvector semantic book search
Semantic similarity search + filtering over the Book catalog using pgvector.
Configure via DATABASE_URL / POSTGRES_DSN environment variable.
"""
import os
import logging
from typing import Optional, List, Dict, Tuple
import json

import asyncpg

logger = logging.getLogger(__name__)

from app.config import POSTGRES_DSN as DATABASE_URL

EMBEDDING_DIM = 1536  # text-embedding-3-small


class BookshelfSearch:
    """Async book search client using pgvector cosine similarity."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize asyncpg connection pool."""
        try:
            import ssl as _ssl
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            self._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=10,
                ssl=ctx,
            )
            # Verify pgvector extension exists
            async with self._pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                logger.info("[Bookshelf Search] Connected — pgvector ready")
        except Exception as e:
            logger.error(f"[Bookshelf Search] Connection failed: {e}")
            raise

    async def disconnect(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("[Bookshelf Search] Disconnected")

    async def search_books_by_embedding(
        self,
        embedding: List[float],
        lexile_min: Optional[int] = None,
        lexile_max: Optional[int] = None,
        track: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict]:
        """
        Search books by semantic similarity using pgvector cosine similarity.

        Args:
            embedding: Query embedding vector (1536 dims from text-embedding-3-small)
            lexile_min: Minimum lexile level (inclusive)
            lexile_max: Maximum lexile level (inclusive)
            track: Filter by curriculum track (e.g., "ENGLISH_LITERATURE")
            limit: Maximum number of results to return

        Returns:
            List of books ranked by relevance_score (descending).
            Format: {
                "id": "uuid",
                "title": "...",
                "author": "...",
                "lexile_level": 600,
                "grade_band": "3-5",
                "track": "ENGLISH_LITERATURE",
                "cover_url": "...",
                "relevance_score": 0.92
            }
        """
        if not self._pool:
            logger.error("[Bookshelf Search] Pool not connected")
            return []

        try:
            async with self._pool.acquire() as conn:
                # Convert embedding to pgvector format: "[1.0, 2.0, ...]"
                embedding_str = json.dumps(embedding)

                # Build dynamic WHERE clause
                where_clauses = ["embedding IS NOT NULL"]
                params = [embedding_str]

                if lexile_min is not None:
                    where_clauses.append(f"lexile_level >= ${len(params) + 1}")
                    params.append(lexile_min)

                if lexile_max is not None:
                    where_clauses.append(f"lexile_level <= ${len(params) + 1}")
                    params.append(lexile_max)

                if track is not None:
                    where_clauses.append(f"track = ${len(params) + 1}")
                    params.append(track)

                where_clause = " AND ".join(where_clauses)
                limit_param_idx = len(params) + 1

                query = f"""
                    SELECT
                        id,
                        title,
                        author,
                        lexile_level,
                        grade_band,
                        track,
                        cover_url,
                        source_url,
                        source_library,
                        (1 - (embedding <-> $1::vector)) AS relevance_score
                    FROM "Book"
                    WHERE {where_clause}
                    ORDER BY embedding <-> $1::vector
                    LIMIT ${limit_param_idx}
                """

                params.append(limit)

                rows = await conn.fetch(query, *params)

                # Convert asyncpg Record objects to dicts
                books = []
                for row in rows:
                    book = {
                        "id": row["id"],
                        "title": row["title"],
                        "author": row["author"],
                        "lexile_level": row["lexile_level"],
                        "grade_band": row["grade_band"],
                        "track": row["track"],
                        "cover_url": row["cover_url"],
                        "source_url": row["source_url"],
                        "source_library": row["source_library"],
                        "relevance_score": float(row["relevance_score"]),
                    }
                    books.append(book)

                logger.debug(f"[Bookshelf Search] Found {len(books)} books for query")
                return books

        except Exception as e:
            logger.error(f"[Bookshelf Search] Semantic search failed: {e}")
            return []

    async def get_book_by_id(self, book_id: str) -> Optional[Dict]:
        """
        Fetch a single book by ID.

        Args:
            book_id: Book UUID

        Returns:
            Book details dict or None if not found.
            Format: {
                "id": "uuid",
                "title": "...",
                "author": "...",
                "description": "...",
                "lexile_level": 600,
                "grade_band": "3-5",
                "track": "ENGLISH_LITERATURE",
                "cover_url": "...",
                "source_url": "...",
                "source_library": "Standard Ebooks",
                "total_pages": 320
            }
        """
        if not self._pool:
            logger.error("[Bookshelf Search] Pool not connected")
            return None

        try:
            async with self._pool.acquire() as conn:
                query = """
                    SELECT
                        id,
                        title,
                        author,
                        description,
                        lexile_level,
                        grade_band,
                        track,
                        cover_url,
                        source_url,
                        source_library,
                        total_pages
                    FROM "Book"
                    WHERE id = $1
                    LIMIT 1
                """

                row = await conn.fetchrow(query, book_id)

                if not row:
                    logger.debug(f"[Bookshelf Search] Book not found: {book_id}")
                    return None

                book = {
                    "id": row["id"],
                    "title": row["title"],
                    "author": row["author"],
                    "description": row["description"],
                    "lexile_level": row["lexile_level"],
                    "grade_band": row["grade_band"],
                    "track": row["track"],
                    "cover_url": row["cover_url"],
                    "source_url": row["source_url"],
                    "source_library": row["source_library"],
                    "total_pages": row["total_pages"],
                }

                logger.debug(f"[Bookshelf Search] Retrieved book: {book['title']}")
                return book

        except Exception as e:
            logger.error(f"[Bookshelf Search] Fetch book failed: {e}")
            return None

    async def list_books(
        self,
        track: Optional[str] = None,
        lexile_min: Optional[int] = None,
        lexile_max: Optional[int] = None,
        source_library: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict], int]:
        """
        Paginated list of books (no semantic search).

        Args:
            track: Filter by curriculum track (e.g., "ENGLISH_LITERATURE")
            lexile_min: Minimum lexile level (inclusive)
            lexile_max: Maximum lexile level (inclusive)
            source_library: Filter by source library (e.g., "Standard Ebooks")
            limit: Number of results per page
            offset: Number of results to skip

        Returns:
            Tuple of (books list, total count)
            Each book: {
                "id": "uuid",
                "title": "...",
                "author": "...",
                "lexile_level": 600,
                "grade_band": "3-5",
                "track": "ENGLISH_LITERATURE",
                "cover_url": "...",
                "source_url": "...",
                "source_library": "Standard Ebooks"
            }
        """
        if not self._pool:
            logger.error("[Bookshelf Search] Pool not connected")
            return [], 0

        try:
            async with self._pool.acquire() as conn:
                # Build dynamic WHERE clause
                where_clauses = []
                params: List = []

                if track is not None:
                    where_clauses.append(f"track = ${len(params) + 1}")
                    params.append(track)

                if lexile_min is not None:
                    where_clauses.append(f"lexile_level >= ${len(params) + 1}")
                    params.append(lexile_min)

                if lexile_max is not None:
                    where_clauses.append(f"lexile_level <= ${len(params) + 1}")
                    params.append(lexile_max)

                if source_library is not None:
                    where_clauses.append(f"source_library = ${len(params) + 1}")
                    params.append(source_library)

                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

                # Get total count
                count_query = f'SELECT COUNT(*) FROM "Book" WHERE {where_clause}'
                count_result = await conn.fetchval(count_query, *params)
                total_count = int(count_result) if count_result else 0

                # Fetch paginated results
                limit_param_idx = len(params) + 1
                offset_param_idx = len(params) + 2

                list_query = f"""
                    SELECT
                        id,
                        title,
                        author,
                        lexile_level,
                        grade_band,
                        track,
                        cover_url,
                        source_url,
                        source_library
                    FROM "Book"
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${limit_param_idx} OFFSET ${offset_param_idx}
                """

                rows = await conn.fetch(list_query, *params, limit, offset)

                # Convert asyncpg Record objects to dicts
                books = []
                for row in rows:
                    book = {
                        "id": row["id"],
                        "title": row["title"],
                        "author": row["author"],
                        "lexile_level": row["lexile_level"],
                        "grade_band": row["grade_band"],
                        "track": row["track"],
                        "cover_url": row["cover_url"],
                        "source_url": row["source_url"],
                        "source_library": row["source_library"],
                    }
                    books.append(book)

                logger.debug(
                    f"[Bookshelf Search] Listed {len(books)} books (total: {total_count})"
                )
                return books, total_count

        except Exception as e:
            logger.error(f"[Bookshelf Search] List books failed: {e}")
            return [], 0


# Singleton instance
bookshelf_search = BookshelfSearch()
