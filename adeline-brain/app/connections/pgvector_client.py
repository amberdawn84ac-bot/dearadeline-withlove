"""
pgvector Client — The Hippocampus
Semantic similarity search over the verified source document corpus.
Configure via POSTGRES_DSN environment variable.
"""
import os
import logging
import uuid
from typing import Optional

from sqlalchemy import text, Column, String, Float, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector

logger = logging.getLogger(__name__)

_pg_password = os.getenv("POSTGRES_PASSWORD", "adeline_local_dev")
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    f"postgresql://adeline:{_pg_password}@postgres:5432/hippocampus"
)
# SQLAlchemy async requires the asyncpg driver
ASYNC_DSN = POSTGRES_DSN.replace("postgresql://", "postgresql+asyncpg://")

EMBEDDING_DIM = 1536  # text-embedding-3-small


class Base(DeclarativeBase):
    pass


class HippocampusDocument(Base):
    """
    A verified source document chunk stored with its embedding vector.
    This is what the Witness Protocol searches against.
    """
    __tablename__ = "hippocampus_documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_title  = Column(String, nullable=False)
    source_url    = Column(String, nullable=False, default="")
    track         = Column(String, nullable=False)
    chunk         = Column(String, nullable=False)
    embedding     = Column(Vector(EMBEDDING_DIM), nullable=False)
    # WitnessCitation fields
    citation_author       = Column(String, nullable=False, default="")
    citation_year         = Column(Integer, nullable=True)
    citation_archive_name = Column(String, nullable=False, default="")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


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
    ) -> str:
        """Insert a verified source document chunk with its embedding."""
        async with self._session_factory() as session:
            doc = HippocampusDocument(
                source_title=source_title,
                source_url=source_url,
                track=track,
                chunk=chunk,
                embedding=embedding,
                citation_author=citation_author,
                citation_year=citation_year,
                citation_archive_name=citation_archive_name,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
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
