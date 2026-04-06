"""
pgvector Client — The Hippocampus
Semantic similarity search over the verified source document corpus.
Configure via POSTGRES_DSN environment variable.
"""
import os
import logging
import uuid
from typing import Optional

from sqlalchemy import text, Column, String, Float, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector

logger = logging.getLogger(__name__)

from app.config import ASYNC_POSTGRES_DSN as ASYNC_DSN

EMBEDDING_DIM = 1536  # text-embedding-3-small


class Base(DeclarativeBase):
    pass


class HippocampusDocument(Base):
    """
    A verified source document chunk stored with its embedding vector.
    This is what the Witness Protocol searches against.

    Unique constraint on (source_url, track) prevents duplicate seeding
    of the same source URL for the same curriculum track.
    """
    __tablename__ = "hippocampus_documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_title  = Column(String, nullable=False)
    source_url    = Column(String, nullable=False, default="")
    track         = Column(String, nullable=False)
    chunk         = Column(String, nullable=False)
    embedding     = Column(Vector(EMBEDDING_DIM), nullable=False)
    source_type   = Column(String, nullable=False, default="PRIMARY_SOURCE")
    # WitnessCitation fields
    citation_author       = Column(String, nullable=False, default="")
    citation_year         = Column(Integer, nullable=True)
    citation_archive_name = Column(String, nullable=False, default="")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint: (source_url, track) pair must be unique
    __table_args__ = (
        UniqueConstraint("source_url", "track", name="hippocampus_document_source_url_track_key"),
    )

    def __init__(self, **kwargs):
        # Apply Python-level defaults for columns before calling super().__init__
        kwargs.setdefault("source_type", "PRIMARY_SOURCE")
        super().__init__(**kwargs)


class HippocampusClient:
    def __init__(self):
        self._engine = None
        self._session_factory: Optional[async_sessionmaker] = None

    async def connect(self):
        self._engine = create_async_engine(ASYNC_DSN, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

        async with self._engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

        logger.info("[Hippocampus] Connected — pgvector table ready")

    async def upsert_document(
        self,
        source_title: str,
        track: str,
        chunk: str,
        embedding: list[float],
        citation_author: str = "",
        citation_year: Optional[int] = None,
        citation_archive_name: str = "",
        source_url: str = "",
        source_type: str = "PRIMARY_SOURCE",
    ) -> str:
        """
        Insert a verified source document chunk with its embedding.

        Skips insertion if (source_url, track) pair already exists.
        Returns the document ID (existing or newly created).
        """
        async with self._session_factory() as session:
            # Check for duplicate (source_url, track) pair
            existing = await session.execute(
                text("""
                    SELECT id FROM hippocampus_documents
                    WHERE source_url = :source_url AND track = :track
                    LIMIT 1
                """),
                {"source_url": source_url, "track": track},
            )
            result = existing.scalar()

            if result:
                logger.debug(
                    f"[Duplicate] Skipping {source_url} for track {track} — already exists (id={result})"
                )
                return str(result)

            # Insert new document
            doc = HippocampusDocument(
                source_title=source_title,
                source_url=source_url,
                track=track,
                chunk=chunk,
                embedding=embedding,
                source_type=source_type,
                citation_author=citation_author,
                citation_year=citation_year,
                citation_archive_name=citation_archive_name,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            logger.debug(f"[Hippocampus] Inserted document id={doc.id} for {source_url}")
            return str(doc.id)

    async def similarity_search(
        self, query_embedding: list[float], track: str, top_k: int = 5
    ) -> list[dict]:
        """
        Cosine similarity search against the Hippocampus corpus.
        Returns chunks sorted by similarity (highest first).
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT
                        id::text,
                        source_title,
                        source_url,
                        source_type,
                        chunk,
                        citation_author,
                        citation_year,
                        citation_archive_name,
                        1 - (embedding <=> CAST(:embedding AS vector)) AS similarity_score
                    FROM hippocampus_documents
                    WHERE track = :track
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(query_embedding),
                    "track": track,
                    "top_k": top_k,
                },
            )
            rows = result.mappings().all()
            return [dict(r) for r in rows]

    async def count_documents(self, track: Optional[str] = None) -> int:
        async with self._session_factory() as session:
            if track:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM hippocampus_documents WHERE track = :track"),
                    {"track": track},
                )
            else:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM hippocampus_documents")
                )
            return result.scalar()


hippocampus = HippocampusClient()
