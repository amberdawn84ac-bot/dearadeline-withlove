"""
Conversation Store — Postgres-backed persistence for chat history.

Stores student-Adeline conversations for:
  1. Context injection into LLM prompts (short-term memory)
  2. Long-term learning pattern analysis
  3. ZPD zone tracking over time

Tables:
  conversation_messages — one row per message (student or assistant)
  conversation_sessions — groups messages into sessions (optional)
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

from sqlalchemy import text, Column, String, Integer, Text, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

from app.config import ASYNC_POSTGRES_DSN as ASYNC_DSN


class ConversationBase(DeclarativeBase):
    pass


class ConversationMessage(ConversationBase):
    """One message in a conversation. Role is USER or ASSISTANT."""
    __tablename__ = "conversation_messages"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    student_id    = Column(String, nullable=False, index=True)
    session_id    = Column(String, nullable=True, index=True)  # Optional grouping
    role          = Column(String, nullable=False)  # USER | ASSISTANT
    content       = Column(Text, nullable=False)
    # Pedagogical state at time of message
    zpd_zone      = Column(String, nullable=True)   # FRUSTRATED | IN_ZPD | BORED
    mastery_band  = Column(String, nullable=True)   # NOVICE | DEVELOPING | PROFICIENT | ADVANCED
    # Metadata
    lesson_id     = Column(String, nullable=True)   # Context: which lesson was active
    track         = Column(String, nullable=True)   # Context: which track
    created_at    = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class ConversationStore:
    """
    Async Postgres store for conversation history.
    
    Usage:
        await conversation_store.connect()
        await conversation_store.save_message(student_id, "USER", "I don't understand")
        history = await conversation_store.get_recent_history(student_id, limit=10)
    """
    
    def __init__(self):
        self._engine = None
        self._session_factory: Optional[async_sessionmaker] = None

    async def connect(self, retries: int = 5, delay: float = 2.0):
        """Connect with exponential back-off."""
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
                    pool_pre_ping=True,
                    pool_recycle=300,
                    connect_args={"ssl": ctx, "statement_cache_size": 0},
                )
                self._session_factory = async_sessionmaker(
                    self._engine, expire_on_commit=False
                )
                async with self._engine.begin() as conn:
                    await conn.run_sync(ConversationBase.metadata.create_all)
                logger.info("[ConversationStore] Connected — conversation_messages table ready")
                return
            except Exception as exc:
                last_exc = exc
                wait = delay * (2 ** (attempt - 1))
                logger.warning(
                    f"[ConversationStore] Connection attempt {attempt}/{retries} failed: {exc}. "
                    f"Retrying in {wait:.1f}s…"
                )
                await asyncio.sleep(wait)
        raise RuntimeError(f"[ConversationStore] Could not connect after {retries} attempts") from last_exc

    async def save_message(
        self,
        student_id: str,
        role: Literal["USER", "ASSISTANT"],
        content: str,
        *,
        session_id: str | None = None,
        zpd_zone: str | None = None,
        mastery_band: str | None = None,
        lesson_id: str | None = None,
        track: str | None = None,
    ) -> int:
        """
        Save a single message to the conversation history.
        Returns the message ID.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO conversation_messages
                        (student_id, session_id, role, content, zpd_zone, mastery_band, lesson_id, track, created_at)
                    VALUES
                        (:student_id, :session_id, :role, :content, :zpd_zone, :mastery_band, :lesson_id, :track, NOW())
                    RETURNING id
                """),
                {
                    "student_id": student_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "zpd_zone": zpd_zone,
                    "mastery_band": mastery_band,
                    "lesson_id": lesson_id,
                    "track": track,
                },
            )
            await session.commit()
            row = result.fetchone()
            msg_id = row[0] if row else 0
            logger.debug(f"[ConversationStore] Saved {role} message #{msg_id} for {student_id}")
            return msg_id

    async def save_interaction(
        self,
        student_id: str,
        user_message: str,
        assistant_response: str,
        *,
        session_id: str | None = None,
        zpd_zone: str | None = None,
        mastery_band: str | None = None,
        lesson_id: str | None = None,
        track: str | None = None,
    ) -> tuple[int, int]:
        """
        Save both user message and assistant response in one call.
        Returns (user_msg_id, assistant_msg_id).
        """
        user_id = await self.save_message(
            student_id, "USER", user_message,
            session_id=session_id, zpd_zone=zpd_zone, mastery_band=mastery_band,
            lesson_id=lesson_id, track=track,
        )
        assistant_id = await self.save_message(
            student_id, "ASSISTANT", assistant_response,
            session_id=session_id, zpd_zone=zpd_zone, mastery_band=mastery_band,
            lesson_id=lesson_id, track=track,
        )
        logger.info(f"[ConversationStore] Saved interaction for {student_id}: user#{user_id}, assistant#{assistant_id}")
        return (user_id, assistant_id)

    async def get_recent_history(
        self,
        student_id: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[dict]:
        """
        Fetch the most recent messages for a student.
        Returns messages in chronological order (oldest first).
        """
        async with self._session_factory() as session:
            if session_id:
                result = await session.execute(
                    text("""
                        SELECT id, role, content, zpd_zone, mastery_band, lesson_id, track, created_at
                        FROM conversation_messages
                        WHERE student_id = :student_id AND session_id = :session_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"student_id": student_id, "session_id": session_id, "limit": limit},
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT id, role, content, zpd_zone, mastery_band, lesson_id, track, created_at
                        FROM conversation_messages
                        WHERE student_id = :student_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"student_id": student_id, "limit": limit},
                )
            rows = result.mappings().all()

        # Reverse to chronological order (oldest first)
        messages = [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "zpd_zone": row["zpd_zone"],
                "mastery_band": row["mastery_band"],
                "lesson_id": row["lesson_id"],
                "track": row["track"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in reversed(rows)
        ]
        return messages

    async def format_history_for_prompt(
        self,
        student_id: str,
        limit: int = 6,
        session_id: str | None = None,
    ) -> str:
        """
        Fetch recent history and format it for LLM prompt injection.
        Returns a formatted string ready for the system prompt.
        """
        messages = await self.get_recent_history(student_id, limit=limit, session_id=session_id)
        
        if not messages:
            return "No previous conversation history with this student."
        
        lines = []
        for msg in messages:
            role_label = "Student" if msg["role"] == "USER" else "Adeline"
            lines.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(lines)

    async def get_zpd_trend(
        self,
        student_id: str,
        limit: int = 20,
    ) -> dict:
        """
        Analyze recent ZPD zones to detect learning patterns.
        Returns counts and trend direction.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT zpd_zone, COUNT(*) as count
                    FROM conversation_messages
                    WHERE student_id = :student_id 
                      AND zpd_zone IS NOT NULL
                      AND role = 'USER'
                    GROUP BY zpd_zone
                    ORDER BY count DESC
                """),
                {"student_id": student_id},
            )
            rows = result.mappings().all()

        zones = {row["zpd_zone"]: int(row["count"]) for row in rows}
        total = sum(zones.values())
        
        # Determine dominant zone
        dominant = max(zones, key=zones.get) if zones else "IN_ZPD"
        
        # Calculate frustration ratio
        frustrated_count = zones.get("FRUSTRATED", 0)
        frustration_ratio = frustrated_count / total if total > 0 else 0.0
        
        return {
            "zones": zones,
            "total_messages": total,
            "dominant_zone": dominant,
            "frustration_ratio": frustration_ratio,
            "needs_intervention": frustration_ratio > 0.4,  # >40% frustrated = flag
        }

    async def clear_session(self, student_id: str, session_id: str) -> int:
        """
        Clear all messages for a specific session.
        Returns the number of deleted messages.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    DELETE FROM conversation_messages
                    WHERE student_id = :student_id AND session_id = :session_id
                    RETURNING id
                """),
                {"student_id": student_id, "session_id": session_id},
            )
            await session.commit()
            deleted = len(result.fetchall())
            logger.info(f"[ConversationStore] Cleared {deleted} messages for session {session_id}")
            return deleted


# Singleton instance
conversation_store = ConversationStore()
