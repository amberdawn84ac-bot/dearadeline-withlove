"""
Shared mastery/credit writer.

Used by both the manual journal-seal flow (POST /journal/seal) and automatic
Space lesson-boundary crediting (app/api/spaces.py::transition_space). Never
awards credit for mere exposure — every call here must be backed by an
evaluated demonstration: a scored quiz, a Space chat turn the LLM judged
"correct", or an explicit reflection/artifact/parent-attestation.

Every underlying write (student_journal upsert, StandardMastery upsert,
SpacedRepetitionCard upsert) is idempotent, so calling this more than once for
the same lesson_id is always safe — a retried or replayed lesson-completion
event never double-credits.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.connections.journal_store import journal_store
from app.connections.curriculum_graph import curriculum_graph
from app.models.student import invalidate_student_state_cache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConceptCredit:
    concept_id: str
    concept_name: str = ""
    quality: int = 3  # SM-2 scale, 0-5. 3 = "correct with difficulty", the same
    # default seal_journal has always used for lesson-derived (non-quiz) evidence.


async def record_mastery_credit(
    *,
    student_id: str,
    track: str,
    lesson_id: str,
    completed_blocks: int,
    proficiency: str,
    evidence_sources: list[dict] | None,
    plan_item_id: str | None = None,
    oas_standards: list[dict] | None = None,
    concept_credits: list[ConceptCredit] | None = None,
) -> dict:
    """Write journal + standards mastery + BKT/SM-2 updates for a demonstrated lesson.

    Returns the updated track_progress map (same shape /journal/seal returns).
    Raises if the durable journal/standards writes fail — callers decide
    whether that should surface to the user (seal_journal, a synchronous
    human action) or just be logged (Space lesson-boundary crediting, an
    automatic background event that must never block the learner's turn).
    """
    track_progress = await journal_store.seal(
        student_id=student_id,
        lesson_id=lesson_id,
        track=track,
        completed_blocks=completed_blocks,
        sources=evidence_sources or None,
    )

    await invalidate_student_state_cache(student_id)

    if oas_standards:
        await curriculum_graph.record_standard_mastery(
            student_id, track, oas_standards, proficiency=proficiency,
        )

    for credit in concept_credits or []:
        if not credit.concept_id:
            continue
        asyncio.create_task(_update_bkt_safe(student_id, track, credit))

    try:
        from app.api.learning_plan import pop_completed_lesson
        await pop_completed_lesson(student_id, plan_item_id or lesson_id)
    except Exception as exc:
        logger.warning("[MasteryCredit] Learning plan invalidation failed: %s", exc)

    return track_progress


async def _update_bkt_safe(student_id: str, track: str, credit: ConceptCredit) -> None:
    """Fire-and-forget BKT + SM-2 update. Non-fatal — a scheduling hiccup here
    must never undo the journal/standards credit that already landed."""
    try:
        from app.algorithms.bkt_tracker import update_card_after_lesson
        await update_card_after_lesson(
            student_id=student_id,
            concept_id=credit.concept_id,
            concept_name=credit.concept_name,
            track=track,
            quality=credit.quality,
        )
    except Exception as exc:
        logger.warning("[MasteryCredit] BKT update failed (non-fatal): %s", exc)
