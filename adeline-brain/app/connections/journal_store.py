"""
Journal Store — Postgres-backed persistence for sealed lessons and daily notes.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text, Column, String, Integer, Text, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)
from app.config import ASYNC_POSTGRES_DSN as ASYNC_DSN  # noqa: E402


class JournalBase(DeclarativeBase):
    pass


class StudentJournalEntry(JournalBase):
    __tablename__ = "student_journal"
    student_id = Column(String, primary_key=True)
    lesson_id = Column(String, primary_key=True)
    track = Column(String, nullable=False)
    completed_blocks = Column(Integer, default=0, nullable=False)
    sources_json = Column(Text, nullable=True, default="[]")
    sealed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class DailyJournalNote(JournalBase):
    __tablename__ = "daily_journal_notes"
    id = Column(String, primary_key=True)
    student_id = Column(String, nullable=False, index=True)
    topic = Column(String, nullable=False)
    track = Column(String, nullable=False, default="ENGLISH_LITERATURE")
    learned = Column(Text, nullable=False)
    action = Column(Text, nullable=True)
    note_json = Column(Text, nullable=True)
    source = Column(String, nullable=False, default="adeline_conversation")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class JournalStore:
    def __init__(self):
        self._engine = None
        self._session_factory: Optional[async_sessionmaker] = None

    async def connect(self, retries: int = 5, delay: float = 2.0):
        import asyncio
        last_exc: Exception = RuntimeError("never connected")
        for attempt in range(1, retries + 1):
            try:
                import ssl as _ssl
                ctx = _ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _ssl.CERT_NONE
                self._engine = create_async_engine(ASYNC_DSN, echo=False, pool_pre_ping=True, pool_recycle=300, connect_args={"ssl": ctx, "statement_cache_size": 0})
                self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
                async with self._engine.begin() as conn:
                    await conn.run_sync(JournalBase.metadata.create_all)
                logger.info("[JournalStore] Connected — journal tables ready")
                return
            except Exception as exc:
                last_exc = exc
                wait = delay * (2 ** (attempt - 1))
                logger.warning(f"[JournalStore] Connection attempt {attempt}/{retries} failed: {exc}. Retrying in {wait:.1f}s…")
                await asyncio.sleep(wait)
        raise RuntimeError(f"[JournalStore] Could not connect after {retries} attempts") from last_exc

    async def seal(self, student_id: str, lesson_id: str, track: str, completed_blocks: int, sources: list[dict] | None = None) -> dict:
        sources_str = json.dumps(sources or [])
        async with self._session_factory() as session:
            await session.execute(text("""
                INSERT INTO student_journal (student_id, lesson_id, track, completed_blocks, sources_json, sealed_at)
                VALUES (:student_id, :lesson_id, :track, :completed_blocks, :sources_json, NOW())
                ON CONFLICT (student_id, lesson_id)
                DO UPDATE SET track = EXCLUDED.track, completed_blocks = EXCLUDED.completed_blocks, sources_json = EXCLUDED.sources_json, sealed_at = NOW()
            """), {"student_id": student_id, "lesson_id": lesson_id, "track": track, "completed_blocks": completed_blocks, "sources_json": sources_str})
            await session.commit()
        return await self.get_track_progress(student_id)

    async def add_daily_note(self, student_id: str, topic: str, track: str, learned: str, action: str | None = None, note: dict | None = None, source: str = "adeline_conversation") -> dict:
        note_id = str(uuid.uuid4())
        async with self._session_factory() as session:
            await session.execute(text("""
                INSERT INTO daily_journal_notes (id, student_id, topic, track, learned, action, note_json, source, created_at)
                VALUES (:id, :student_id, :topic, :track, :learned, :action, :note_json, :source, NOW())
            """), {
                "id": note_id,
                "student_id": student_id,
                "topic": topic,
                "track": track,
                "learned": learned,
                "action": action,
                "note_json": json.dumps(note) if note else None,
                "source": source,
            })
            await session.commit()
        return {"id": note_id, "student_id": student_id, "topic": topic, "track": track, "created_at": datetime.now(timezone.utc).isoformat()}

    async def get_daily_notes(self, student_id: str, limit: int = 50) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(text("""
                SELECT id, topic, track, learned, action, note_json, source, created_at
                FROM daily_journal_notes
                WHERE student_id = :student_id
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"student_id": student_id, "limit": limit})
            rows = result.mappings().all()
        notes = []
        for row in rows:
            try:
                parsed_note = json.loads(row["note_json"]) if row["note_json"] else None
            except json.JSONDecodeError:
                parsed_note = None
            notes.append({
                "id": row["id"],
                "topic": row["topic"],
                "track": row["track"],
                "learned": row["learned"],
                "action": row["action"],
                "note": parsed_note,
                "source": row["source"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
        return notes

    async def get_all_sources(self, student_id: str) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(text("SELECT track, sources_json FROM student_journal WHERE student_id = :student_id AND sources_json IS NOT NULL"), {"student_id": student_id})
            rows = result.mappings().all()
        seen: set[str] = set()
        merged: list[dict] = []
        for row in rows:
            try:
                sources = json.loads(row["sources_json"] or "[]")
            except json.JSONDecodeError:
                sources = []
            for source in sources:
                title = source.get("title", "")
                if title and title not in seen:
                    seen.add(title)
                    merged.append({**source, "track": row["track"]})
        return merged

    async def get_recent(self, student_id: str, limit: int = 10) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(text("""
                SELECT lesson_id, track, completed_blocks, sealed_at
                FROM student_journal
                WHERE student_id = :student_id
                ORDER BY sealed_at DESC
                LIMIT :limit
            """), {"student_id": student_id, "limit": limit})
            rows = result.mappings().all()
            return [{"lesson_id": row["lesson_id"], "track": row["track"], "completed_blocks": row["completed_blocks"], "sealed_at": row["sealed_at"].isoformat() if row["sealed_at"] else None} for row in rows]

    async def get_track_progress(self, student_id: str) -> dict[str, int]:
        async with self._session_factory() as session:
            result = await session.execute(text("""
                SELECT track, COUNT(*) AS lesson_count
                FROM student_journal
                WHERE student_id = :student_id
                GROUP BY track
            """), {"student_id": student_id})
            rows = result.mappings().all()
            return {row["track"]: int(row["lesson_count"]) for row in rows}


journal_store = JournalStore()
