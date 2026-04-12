"""
Memory Service — Unified interface for Adeline's long-term memory.

Combines:
  - Conversation history (conversation_store)
  - Sealed lesson progress (journal_store)
  - Mastery state (student model)
  - ZPD trends (pedagogical analysis)

This is the "memory layer" that makes Adeline a lifelong mentor,
not a goldfish with a 10-second attention span.

Usage:
    from app.services.memory import memory_service
    
    # Before generating a response
    context = await memory_service.get_full_context(student_id)
    
    # After generating a response
    await memory_service.save_interaction(
        student_id, user_message, adeline_response,
        zpd_zone="IN_ZPD", lesson_id="lesson-123"
    )
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.connections.conversation_store import conversation_store
from app.connections.journal_store import journal_store
from app.models.student import StudentState, MasteryBand

logger = logging.getLogger(__name__)


@dataclass
class StudentMemoryContext:
    """Complete memory context for a student, ready for prompt injection."""
    student_id: str
    # Conversation history
    chat_history: str
    recent_messages: list[dict]
    # Learning progress
    track_progress: dict[str, int]
    total_lessons_sealed: int
    recent_lessons: list[dict]
    # Pedagogical state
    zpd_trend: dict
    dominant_zpd_zone: str
    needs_intervention: bool
    # Mastery
    mastery_band: MasteryBand
    mastery_score: float
    
    def to_prompt_block(self) -> str:
        """Format the full context as a prompt block for LLM injection."""
        lines = [
            "\n╔══════════════════════════════════════════════════════════════╗",
            "║                    STUDENT MEMORY CONTEXT                     ║",
            "╚══════════════════════════════════════════════════════════════╝",
        ]
        
        # Learning progress summary
        if self.track_progress:
            lines.append(f"\nLEARNING PROGRESS ({self.total_lessons_sealed} lessons sealed):")
            for track, count in sorted(self.track_progress.items()):
                lines.append(f"  • {track.replace('_', ' ').title()}: {count} lessons")
        
        # Recent lessons
        if self.recent_lessons:
            lines.append("\nRECENT LESSONS:")
            for lesson in self.recent_lessons[:3]:
                lines.append(f"  • {lesson.get('track', 'Unknown')}: {lesson.get('lesson_id', 'Unknown')}")
        
        # ZPD trend
        lines.append(f"\nPEDAGOGICAL STATE:")
        lines.append(f"  • Dominant ZPD Zone: {self.dominant_zpd_zone}")
        lines.append(f"  • Mastery Band: {self.mastery_band.value}")
        lines.append(f"  • Mastery Score: {self.mastery_score*100:.0f}%")
        if self.needs_intervention:
            lines.append("  ⚠️ INTERVENTION NEEDED: Student shows high frustration ratio")
        
        # Conversation history
        if self.chat_history and self.chat_history != "No previous conversation history with this student.":
            lines.append("\n--- RECENT CONVERSATION ---")
            lines.append(self.chat_history)
            lines.append("---------------------------")
        
        lines.append("────────────────────────────────────────────────────────────────\n")
        
        return "\n".join(lines)


class MemoryService:
    """
    Unified memory service for Adeline.
    
    Aggregates data from multiple stores to provide complete student context.
    """
    
    async def connect(self):
        """Initialize all underlying stores."""
        await conversation_store.connect()
        await journal_store.connect()
        logger.info("[MemoryService] All stores connected")
    
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
        Save a complete interaction (user message + Adeline response).
        Returns (user_msg_id, assistant_msg_id).
        """
        return await conversation_store.save_interaction(
            student_id=student_id,
            user_message=user_message,
            assistant_response=assistant_response,
            session_id=session_id,
            zpd_zone=zpd_zone,
            mastery_band=mastery_band,
            lesson_id=lesson_id,
            track=track,
        )
    
    async def get_recent_history(
        self,
        student_id: str,
        limit: int = 6,
        session_id: str | None = None,
    ) -> str:
        """
        Get formatted conversation history for prompt injection.
        """
        return await conversation_store.format_history_for_prompt(
            student_id=student_id,
            limit=limit,
            session_id=session_id,
        )
    
    async def get_full_context(
        self,
        student_id: str,
        session_id: str | None = None,
        history_limit: int = 6,
        mastery_band: MasteryBand = MasteryBand.DEVELOPING,
        mastery_score: float = 0.5,
    ) -> StudentMemoryContext:
        """
        Fetch complete memory context for a student.
        
        This aggregates:
          - Recent conversation history
          - Sealed lesson progress
          - ZPD trend analysis
          - Current mastery state
        
        Returns a StudentMemoryContext ready for prompt injection.
        """
        import asyncio
        
        # Parallel fetch from all stores
        chat_history, recent_messages, track_progress, recent_lessons, zpd_trend = await asyncio.gather(
            conversation_store.format_history_for_prompt(student_id, limit=history_limit, session_id=session_id),
            conversation_store.get_recent_history(student_id, limit=history_limit, session_id=session_id),
            journal_store.get_track_progress(student_id),
            journal_store.get_recent(student_id, limit=5),
            conversation_store.get_zpd_trend(student_id, limit=20),
        )
        
        total_lessons = sum(track_progress.values())
        
        return StudentMemoryContext(
            student_id=student_id,
            chat_history=chat_history,
            recent_messages=recent_messages,
            track_progress=track_progress,
            total_lessons_sealed=total_lessons,
            recent_lessons=recent_lessons,
            zpd_trend=zpd_trend,
            dominant_zpd_zone=zpd_trend.get("dominant_zone", "IN_ZPD"),
            needs_intervention=zpd_trend.get("needs_intervention", False),
            mastery_band=mastery_band,
            mastery_score=mastery_score,
        )
    
    async def get_prompt_context(
        self,
        student_id: str,
        session_id: str | None = None,
        history_limit: int = 6,
        mastery_band: MasteryBand = MasteryBand.DEVELOPING,
        mastery_score: float = 0.5,
    ) -> str:
        """
        Get a formatted prompt block with full student context.
        
        This is the main entry point for injecting memory into Adeline's prompts.
        """
        context = await self.get_full_context(
            student_id=student_id,
            session_id=session_id,
            history_limit=history_limit,
            mastery_band=mastery_band,
            mastery_score=mastery_score,
        )
        return context.to_prompt_block()
    
    async def should_simplify_response(self, student_id: str) -> bool:
        """
        Quick check: should Adeline simplify her response based on recent frustration?
        """
        trend = await conversation_store.get_zpd_trend(student_id, limit=10)
        return trend.get("needs_intervention", False)
    
    async def get_learning_summary(self, student_id: str) -> dict:
        """
        Get a summary of the student's learning journey.
        Useful for parent dashboards or progress reports.
        """
        import asyncio
        
        track_progress, recent_lessons, zpd_trend = await asyncio.gather(
            journal_store.get_track_progress(student_id),
            journal_store.get_recent(student_id, limit=10),
            conversation_store.get_zpd_trend(student_id, limit=50),
        )
        
        total_lessons = sum(track_progress.values())
        
        return {
            "student_id": student_id,
            "total_lessons_sealed": total_lessons,
            "track_progress": track_progress,
            "recent_lessons": recent_lessons,
            "zpd_analysis": {
                "zones": zpd_trend.get("zones", {}),
                "dominant_zone": zpd_trend.get("dominant_zone", "IN_ZPD"),
                "frustration_ratio": zpd_trend.get("frustration_ratio", 0.0),
                "needs_intervention": zpd_trend.get("needs_intervention", False),
            },
        }


# Singleton instance
memory_service = MemoryService()
