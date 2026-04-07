"""
Journal Store — Postgres-backed persistence for sealed student lessons.
Uses SQLAlchemy (same driver as Hippocampus) to avoid a second ORM.

Tables:
  student_journal  — one row per (student_id, lesson_id); upserted on seal
Track progress is derived dynamically: COUNT(*) GROUP BY track.
"""
import json
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text, Column, String, Integer, Text, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

from app.config import ASYNC_POSTGRES_DSN as ASYNC_DSN


class JournalBase(DeclarativeBase):
    pass


class StudentJournalEntry(JournalBase):
    """One sealed lesson per student. (student_id, lesson_id) is the PK."""
    __tablename__ = "student_journal"

    student_id       = Column(String, primary_key=True)
    lesson_id        = Column(String, primary_key=True)
    track            = Column(String, nullable=False)
    completed_blocks = Column(Integer, default=0, nullable=False)
    # JSON array of {title, url, author, year} for the Evidence Appendix
    sources_json     = Column(Text, nullable=True, default="[]")
    sealed_at        = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class JournalStore:
    def __init__(self):
        self._engine = None
        self._session_factory: Optional[async_sessionmaker] = None

    async def connect(self, retries: int = 5, delay: float = 2.0):
        """Connect with exponential back-off so Docker start-order doesn't matter."""
        import asyncio
        last_exc: Exception = RuntimeError("never connected")
        for attempt in range(1, retries + 1):
            try:
                import ssl as _ssl
                ctx = _ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _ssl.CERT_NONE
                self._engine = create_async_engine(
                    ASYNC_DSN,
                    echo=False,
                    pool_pre_ping=True,   # validate connections before use
                    pool_recycle=300,     # recycle stale connections every 5 min
                    connect_args={"ssl": ctx},
                )
                self._session_factory = async_sessionmaker(
                    self._engine, expire_on_commit=False
                )
                async with self._engine.begin() as conn:
                    await conn.run_sync(JournalBase.metadata.create_all)
                logger.info("[JournalStore] Connected — student_journal table ready")
                return
            except Exception as exc:
                last_exc = exc
                wait = delay * (2 ** (attempt - 1))
                logger.warning(
                    f"[JournalStore] Connection attempt {attempt}/{retries} failed: {exc}. "
                    f"Retrying in {wait:.1f}s…"
                )
                await asyncio.sleep(wait)
        raise RuntimeError(f"[JournalStore] Could not connect after {retries} attempts") from last_exc

    async def seal(
        self,
        student_id: str,
        lesson_id: str,
        track: str,
        completed_blocks: int,
        sources: list[dict] | None = None,
    ) -> dict:
        """
        Upsert a sealed lesson entry.
        Returns the updated track_progress map for this student.
        """
        sources_str = json.dumps(sources or [])

        async with self._session_factory() as session:
            # Upsert via raw SQL for portability across Postgres versions
            await session.execute(
                text("""
                    INSERT INTO student_journal
                        (student_id, lesson_id, track, completed_blocks, sources_json, sealed_at)
                    VALUES
                        (:student_id, :lesson_id, :track, :completed_blocks, :sources_json, NOW())
                    ON CONFLICT (student_id, lesson_id)
                    DO UPDATE SET
                        track            = EXCLUDED.track,
                        completed_blocks = EXCLUDED.completed_blocks,
                        sources_json     = EXCLUDED.sources_json,
                        sealed_at        = NOW()
                """),
                {
                    "student_id": student_id,
                    "lesson_id": lesson_id,
                    "track": track,
                    "completed_blocks": completed_blocks,
                    "sources_json": sources_str,
                },
            )
            await session.commit()

        return await self.get_track_progress(student_id)

    async def get_all_sources(self, student_id: str) -> list[dict]:
        """Return a deduplicated list of all primary sources used by this student."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT track, sources_json
                    FROM student_journal
                    WHERE student_id = :student_id AND sources_json IS NOT NULL
                """),
                {"student_id": student_id},
            )
            rows = result.mappings().all()

        # Merge all sources, deduplicate by source title
        seen: set[str] = set()
        merged: list[dict] = []
        for row in rows:
            try:
                sources = json.loads(row["sources_json"] or "[]")
            except json.JSONDecodeError:
                sources = []
            for s in sources:
                title = s.get("title", "")
                if title and title not in seen:
                    seen.add(title)
                    merged.append({**s, "track": row["track"]})
        return merged

    async def get_recent(self, student_id: str, limit: int = 10) -> list[dict]:
        """Return the most recently sealed lessons for a student."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT lesson_id, track, completed_blocks, sealed_at
                    FROM student_journal
                    WHERE student_id = :student_id
                    ORDER BY sealed_at DESC
                    LIMIT :limit
                """),
                {"student_id": student_id, "limit": limit},
            )
            rows = result.mappings().all()
            return [
                {
                    "lesson_id": row["lesson_id"],
                    "track": row["track"],
                    "completed_blocks": row["completed_blocks"],
                    "sealed_at": row["sealed_at"].isoformat() if row["sealed_at"] else None,
                }
                for row in rows
            ]

    async def get_track_progress(self, student_id: str) -> dict[str, int]:
        """
        Return a map of { track: lesson_count } for all sealed lessons
        belonging to this student.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT track, COUNT(*) AS lesson_count
                    FROM student_journal
                    WHERE student_id = :student_id
                    GROUP BY track
                """),
                {"student_id": student_id},
            )
            rows = result.mappings().all()
            return {row["track"]: int(row["lesson_count"]) for row in rows}


journal_store = JournalStore()
