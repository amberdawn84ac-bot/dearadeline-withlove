"""Durable, server-paced unit Spaces built from saved canonical experiences."""
from __future__ import annotations

import json
import logging
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.middleware import require_internal_key, verify_student_access
from app.config import get_db_conn
from app.connections.concept_encounter_store import concept_encounter_store
from app.services.mastery_credit import ConceptCredit, record_mastery_credit
from app.services.standards_mapper import _embed

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brain/spaces", tags=["spaces"])


def _decoded(value, fallback):
    """asyncpg returns jsonb columns as raw JSON text here — no codec is
    registered anywhere in this process (see student_experience_store.py's
    identical helper). Every jsonb read must go through this."""
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return fallback
    return value


class SpaceMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class OffPlanTopic(BaseModel):
    concept_name: str = Field(min_length=1, max_length=200)
    track: str | None = None
    tier: Literal["encountered", "demonstrated"]


class SpaceEvaluation(BaseModel):
    adeline_message: str = Field(min_length=1, max_length=4000)
    evaluation: Literal["correct", "partial", "incorrect", "not_answered"]
    recommended_action: Literal["stay", "advance", "complete_unit"]
    is_waiting_for_user: bool
    resource_triggers: list[Literal["show_microscope_diagram", "display_breakout_tracks"]] = Field(default_factory=list)
    off_plan_topic: OffPlanTopic | None = None
    user_message: str = Field(min_length=1, max_length=4000)
    expected_version: int = Field(ge=0)


def _lesson_for_block(metadata: dict, block_id: str, block_index: int) -> dict:
    lessons = ((metadata or {}).get("unit_plan") or {}).get("lessons") or []
    for lesson_index, lesson in enumerate(lessons):
        if block_id in (lesson.get("block_ids") or []):
            return {"index": lesson_index, "count": len(lessons), **lesson}
    return {"index": block_index, "count": max(len(lessons), 1), "lesson_id": block_id,
            "title": f"Activity {block_index + 1}", "block_ids": [block_id]}


def _grade_from_metadata(metadata: dict) -> int:
    grade_text = str((metadata or {}).get("grade_level") or "8")
    return next((int(part) for part in grade_text.replace("-", " ").split() if part.isdigit()), 8)


def _learner_depth(metadata: dict, block: dict | None) -> dict:
    grade = _grade_from_metadata(metadata)
    band = "elementary" if grade <= 5 else "middle" if grade <= 8 else "high_school"
    tier = "foundation" if band == "elementary" else "analysis" if band == "middle" else "synthesis"
    roles = (block or {}).get("family_roles") or {}
    return {"grade": grade, "band": band, "tier": tier, "assignment": roles.get(band) or ""}


def _state(session: dict, experience: dict) -> dict:
    blocks = experience.get("blocks") or []
    index = min(session["currentBlockIndex"], max(len(blocks) - 1, 0))
    block = blocks[index] if blocks else None
    lesson = _lesson_for_block(experience.get("metadata") or {}, block.get("block_id", "") if block else "", index)
    return {
        "session_id": str(session["id"]), "student_id": session["studentId"],
        "plan_item_id": session["planItemId"], "experience_id": session["experienceId"],
        "title": experience.get("title") or "Learning Space", "status": session["status"],
        "version": session["version"], "current_block_index": index,
        "total_blocks": len(blocks), "completed_block_ids": session["completedBlockIds"] or [],
        "current_block": block, "current_lesson": lesson,
        "learner_depth": _learner_depth(experience.get("metadata") or {}, block),
        "messages": session["messagesJson"] or [], "metadata": experience.get("metadata") or {},
    }


# ── Lesson-boundary mastery credit ──────────────────────────────────────────
# A Space's activities are grouped into lessons (unit_plan.lessons[].block_ids).
# Each lesson names the concepts it demonstrates (concept_ids[], resolved
# against unit_plan.essential_concepts[]). When every block belonging to a
# lesson has been completed, that lesson's concepts have been demonstrated —
# this is the credit boundary, not "the whole unit finished."

def _blocks_for_lesson(lesson: dict) -> list[str]:
    return list(lesson.get("block_ids") or [])


def _lesson_fully_completed(lesson: dict, completed_block_ids: list[str]) -> bool:
    block_ids = _blocks_for_lesson(lesson)
    return bool(block_ids) and all(block_id in completed_block_ids for block_id in block_ids)


def _newly_completed_lesson(
    metadata: dict, current_block_id: str,
    completed_before: list[str], completed_after: list[str], credited_lesson_ids: list[str],
) -> dict | None:
    """Return the lesson that just became fully completed by this transition, or None.

    "Just" means it was not already fully completed before this turn's
    advancement, and it has not already been credited — so a retried or
    replayed transition never re-triggers credit for the same lesson.
    """
    lessons = ((metadata or {}).get("unit_plan") or {}).get("lessons") or []
    for lesson in lessons:
        if current_block_id not in _blocks_for_lesson(lesson):
            continue
        lesson_id = str(lesson.get("lesson_id") or "")
        if lesson_id in (credited_lesson_ids or []):
            return None
        if _lesson_fully_completed(lesson, completed_after) and not _lesson_fully_completed(lesson, completed_before):
            return lesson
        return None
    return None


def _proficiency_from_evaluations(evaluations: list[str]) -> str:
    """Same DEVELOPING->APPROACHING->UNDERSTANDING->EXTENDING ladder
    journal.py::_evidence_proficiency uses for quiz ratios, driven here by the
    correct/partial ratio of a lesson's Space evaluations instead."""
    if not evaluations:
        return "DEVELOPING"
    correct = sum(1 for item in evaluations if item == "correct")
    partial = sum(1 for item in evaluations if item == "partial")
    ratio = (correct + 0.5 * partial) / len(evaluations)
    if ratio >= 0.9:
        return "EXTENDING"
    if ratio >= 0.75:
        return "UNDERSTANDING"
    if ratio >= 0.5:
        return "APPROACHING"
    return "DEVELOPING"


def _concept_credits_for_lesson(unit_plan: dict, lesson: dict) -> list[ConceptCredit]:
    concepts = {
        str(concept.get("concept_id")): concept
        for concept in (unit_plan.get("essential_concepts") or [])
        if isinstance(concept, dict)
    }
    credits: list[ConceptCredit] = []
    for concept_id in lesson.get("concept_ids") or []:
        concept = concepts.get(str(concept_id))
        if not concept:
            continue
        credits.append(ConceptCredit(concept_id=str(concept_id), concept_name=concept.get("concept") or ""))
    return credits


async def _topic_oas_standards(track: str, grade: int, topic_text: str) -> list[dict]:
    """Live OAS standards match (same pgvector pattern as breakout_standards
    below) for arbitrary topic text, instead of the unit-wide
    CanonicalLesson.oasStandards column — which is authored at the
    whole-unit level (often empty) and would credit every lesson in a unit
    with the same, usually-irrelevant, standards.

    Used both for a completed lesson's own block content, and for a
    rabbit-hole topic that has no pre-authored block at all.
    """
    content = topic_text.strip()
    if not content:
        return []
    embedding = await _embed(content[:8000])
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            '''SELECT replace(source_title, 'OAS Standard ', '') AS code, chunk AS description,
                      1 - (embedding <=> $1::vector) AS similarity
                 FROM hippocampus_documents
                WHERE track = $2 AND source_title LIKE 'OAS Standard%'
                ORDER BY embedding <=> $1::vector LIMIT 3''',
            str(embedding), track,
        )
    finally:
        await conn.close()
    # No "subject" key: record_standard_mastery falls back to _subject_from_code,
    # which derives a short subject code (MATH/ELA/SCI/...) from the standard's
    # own text — the ten-track constitution name (e.g. "CREATION_SCIENCE") is
    # not a valid StandardMastery.subject value and would break that convention.
    return [
        {"standard_id": row["code"], "code": row["code"], "text": row["description"], "grade": grade}
        for row in rows if float(row["similarity"]) > 0.5
    ]


def _lesson_content(blocks: list[dict], lesson: dict) -> str:
    block_ids = set(_blocks_for_lesson(lesson))
    parts = [
        " ".join(filter(None, [block.get("title"), block.get("content")]))
        for block in blocks if block.get("block_id") in block_ids
    ]
    return " ".join(filter(None, parts))[:8000]


async def _credit_newly_completed_lesson(
    *, student_id: str, plan_item_id: str, track: str, metadata: dict, blocks: list[dict],
    lesson: dict, block_evaluations: dict, session_id: str,
) -> list[str]:
    """Best-effort. A failure here must never strand the family behind a
    stuck turn — the block/lesson advancement has already committed."""
    lesson_id = str(lesson.get("lesson_id") or "")
    try:
        unit_plan = (metadata or {}).get("unit_plan") or {}
        concept_credits = _concept_credits_for_lesson(unit_plan, lesson)
        evaluations = [
            str(block_evaluations.get(block_id))
            for block_id in _blocks_for_lesson(lesson)
            if block_evaluations.get(block_id)
        ]
        proficiency = _proficiency_from_evaluations(evaluations)
        grade = _grade_from_metadata(metadata)
        oas_standards = await _topic_oas_standards(track, grade, _lesson_content(blocks, lesson))

        await record_mastery_credit(
            student_id=student_id,
            track=track,
            lesson_id=lesson_id,
            completed_blocks=len(_blocks_for_lesson(lesson)),
            proficiency=proficiency,
            evidence_sources=[{
                "type": "space_conversation_transcript",
                "lesson_id": lesson_id,
                "lesson_title": lesson.get("title") or "",
                "evaluations": evaluations,
            }],
            plan_item_id=plan_item_id,
            oas_standards=oas_standards,
            concept_credits=concept_credits,
        )

        conn = await get_db_conn()
        try:
            await conn.execute(
                'UPDATE "SpaceSession" SET "creditedLessonIds" = '
                'array_append("creditedLessonIds", $1) '
                'WHERE id = $2 AND NOT ($1 = ANY("creditedLessonIds"))',
                lesson_id, session_id,
            )
        finally:
            await conn.close()

        return [credit.concept_name for credit in concept_credits if credit.concept_name]
    except Exception:
        logger.exception(
            "[Spaces] Lesson-boundary mastery credit failed student=%s plan_item=%s lesson=%s "
            "— block advancement already committed; safe to retry on next lesson completion",
            student_id, plan_item_id, lesson_id,
        )
        return []


def _concept_slug(concept_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", concept_name.strip().lower()).strip("-") or "topic"


async def _credit_off_plan_topic(
    *, student_id: str, plan_item_id: str, session_id: str, fallback_track: str,
    fallback_grade: int, topic: "OffPlanTopic",
) -> str | None:
    """A conversation went beyond the planned activity. Best-effort, entirely
    independent of lesson-boundary crediting — a failure here must never
    strand the family behind a stuck turn.

    Returns the concept name if it was credited as mastery (for the
    frontend's "credited this session" summary), or None otherwise —
    "encountered" topics are logged but deliberately never surfaced as credit.
    """
    track = topic.track or fallback_track
    try:
        if topic.tier == "encountered":
            await concept_encounter_store.record(student_id, topic.concept_name, track, session_id)
            return None

        standards = await _topic_oas_standards(track, fallback_grade, topic.concept_name)
        slug = _concept_slug(topic.concept_name)
        await record_mastery_credit(
            student_id=student_id,
            track=track,
            lesson_id=f"rabbit-hole-{slug}-{student_id}",
            completed_blocks=1,
            proficiency="APPROACHING",
            evidence_sources=[{
                "type": "rabbit_hole_conversation",
                "concept": topic.concept_name,
            }],
            plan_item_id=plan_item_id,
            oas_standards=standards,
            concept_credits=[ConceptCredit(
                concept_id=f"rabbit-hole:{slug}", concept_name=topic.concept_name, quality=4,
            )],
        )
        return topic.concept_name
    except Exception:
        logger.exception(
            "[Spaces] Off-plan topic handling failed student=%s plan_item=%s concept=%s tier=%s",
            student_id, plan_item_id, topic.concept_name, topic.tier,
        )
        return None


async def _load_or_create(student_id: str, plan_item_id: str) -> tuple[dict, dict]:
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            'SELECT id::text, status, title, "blocksJson", "metadataJson" FROM "StudentExperience" '
            'WHERE "studentId"=$1 AND "planItemId"=$2', student_id, plan_item_id,
        )
        if not row or row["status"] != "ready":
            raise HTTPException(status_code=409, detail="The unit must finish preparing before its Space can open.")
        experience = {"id": row["id"], "title": row["title"],
                      "blocks": _decoded(row["blocksJson"], []), "metadata": _decoded(row["metadataJson"], {})}
        session_row = await conn.fetchrow(
            'INSERT INTO "SpaceSession" ("studentId","planItemId","experienceId") VALUES ($1,$2,$3::text) '
            'ON CONFLICT ("studentId","planItemId") DO UPDATE SET "experienceId"=EXCLUDED."experienceId" '
            'RETURNING id::text, "studentId", "planItemId", "experienceId", "currentBlockIndex", '
            '"completedBlockIds", "messagesJson", status, version', student_id, plan_item_id, row["id"],
        )
        session = dict(session_row)
        session["messagesJson"] = _decoded(session["messagesJson"], [])
        return session, experience
    finally:
        await conn.close()


@router.get("/{student_id}/{plan_item_id}")
async def read_space(student_id: str, plan_item_id: str, response: Response,
                     _user_id: str = Depends(verify_student_access)):
    response.headers["Cache-Control"] = "private, no-store"
    session, experience = await _load_or_create(student_id, plan_item_id)
    return _state(session, experience)


@router.post("/{student_id}/{plan_item_id}/transition", dependencies=[Depends(require_internal_key)])
async def transition_space(student_id: str, plan_item_id: str, body: SpaceEvaluation,
                           _user_id: str = Depends(verify_student_access)):
    conn = await get_db_conn()
    try:
        async with conn.transaction():
            experience_row = await conn.fetchrow(
                'SELECT id::text, title, track, "blocksJson", "metadataJson" FROM "StudentExperience" '
                'WHERE "studentId"=$1 AND "planItemId"=$2 AND status=\'ready\'', student_id, plan_item_id,
            )
            session_row = await conn.fetchrow(
                'SELECT id::text, "studentId", "planItemId", "experienceId", "currentBlockIndex", '
                '"completedBlockIds", "blockEvaluations", "creditedLessonIds", "messagesJson", status, version '
                'FROM "SpaceSession" WHERE "studentId"=$1 AND "planItemId"=$2 FOR UPDATE', student_id, plan_item_id,
            )
            if not experience_row or not session_row:
                raise HTTPException(status_code=404, detail="Space not found")
            if session_row["version"] != body.expected_version:
                raise HTTPException(status_code=409, detail="Space changed in another window. Refresh and continue.")

            blocks = _decoded(experience_row["blocksJson"], [])
            metadata = _decoded(experience_row["metadataJson"], {})
            index = min(session_row["currentBlockIndex"], max(len(blocks) - 1, 0))
            completed_before = list(session_row["completedBlockIds"] or [])
            completed = list(completed_before)
            current_id = blocks[index].get("block_id") if blocks else None
            may_advance = body.evaluation == "correct" and body.recommended_action in {"advance", "complete_unit"}
            if may_advance and blocks:
                if current_id and current_id not in completed:
                    completed.append(current_id)
                if index < len(blocks) - 1:
                    index += 1
            status = "completed" if blocks and len(completed) >= len(blocks) else "active"
            messages = _decoded(session_row["messagesJson"], [])[-38:]
            messages.extend([{"role": "user", "content": body.user_message},
                             {"role": "assistant", "content": body.adeline_message}])
            block_evaluations = _decoded(session_row["blockEvaluations"], {})
            if current_id:
                block_evaluations[current_id] = body.evaluation
            updated = await conn.fetchrow(
                'UPDATE "SpaceSession" SET "currentBlockIndex"=$1, "completedBlockIds"=$2, '
                '"messagesJson"=$3::jsonb, "blockEvaluations"=$4::jsonb, status=$5, version=version+1, '
                '"updatedAt"=NOW() WHERE id=$6 RETURNING id, "studentId", "planItemId", "experienceId", '
                '"currentBlockIndex", "completedBlockIds", "messagesJson", status, version',
                index, completed, json.dumps(messages), json.dumps(block_evaluations), status, session_row["id"],
            )
        updated_session = dict(updated)
        updated_session["messagesJson"] = _decoded(updated_session["messagesJson"], [])
        experience = {"id": experience_row["id"], "title": experience_row["title"],
                      "blocks": blocks, "metadata": metadata}
        result = _state(updated_session, experience)
        result["resource_triggers"] = body.resource_triggers

        credited_this_session: list[str] = []
        if current_id:
            newly_completed = _newly_completed_lesson(
                metadata, current_id, completed_before, completed, session_row["creditedLessonIds"] or [],
            )
            if newly_completed:
                credited_this_session = await _credit_newly_completed_lesson(
                    student_id=student_id, plan_item_id=plan_item_id,
                    track=experience_row["track"] or "", metadata=metadata,
                    blocks=blocks, lesson=newly_completed, block_evaluations=block_evaluations,
                    session_id=session_row["id"],
                )

        # Independent of lesson-boundary credit above — a conversation can go
        # off-plan on any turn, whether mid-unit or after everything's done.
        if body.off_plan_topic:
            off_plan_credit = await _credit_off_plan_topic(
                student_id=student_id, plan_item_id=plan_item_id, session_id=session_row["id"],
                fallback_track=experience_row["track"] or "", fallback_grade=_grade_from_metadata(metadata),
                topic=body.off_plan_topic,
            )
            if off_plan_credit:
                credited_this_session = [*credited_this_session, off_plan_credit]

        result["credited_this_session"] = credited_this_session
        return result
    finally:
        await conn.close()


@router.get("/{student_id}/{plan_item_id}/breakout-standards")
async def breakout_standards(student_id: str, plan_item_id: str,
                             _user_id: str = Depends(verify_student_access)):
    session, experience = await _load_or_create(student_id, plan_item_id)
    state = _state(session, experience)
    block = state.get("current_block") or {}
    concept = " ".join(filter(None, [block.get("title"), block.get("content")]))[:8000]
    # Keep all ten constitutional tracks visible. A track may legitimately
    # return no strong OAS match; absence is more truthful than forced alignment.
    tracks = {
        "God's Creation & Science": "CREATION_SCIENCE",
        "Health & Naturopathy": "HEALTH_NATUROPATHY",
        "Homesteading & Stewardship": "HOMESTEADING",
        "Government & Economics": "GOVERNMENT_ECONOMICS",
        "Justice & Change-making": "JUSTICE_CHANGEMAKING",
        "Discipleship & Discernment": "DISCIPLESHIP",
        "Truth-Based History": "TRUTH_HISTORY",
        "English Language & Literature": "ENGLISH_LITERATURE",
        "Applied Mathematics": "APPLIED_MATHEMATICS",
        "Creative Economy": "CREATIVE_ECONOMY",
    }
    embedding = await _embed(concept)
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            '''WITH ranked AS (
                 SELECT track, replace(source_title, 'OAS Standard ', '') AS code,
                        chunk AS description,
                        1 - (embedding <=> $1::vector) AS similarity,
                        row_number() OVER (PARTITION BY track ORDER BY embedding <=> $1::vector) AS rank
                   FROM hippocampus_documents
                  WHERE track = ANY($2::text[]) AND source_title LIKE 'OAS Standard%'
               ) SELECT track, code, description, similarity FROM ranked
                  WHERE rank <= 2 AND similarity > 0.5 ORDER BY track, similarity DESC''',
            str(embedding), list(tracks.values()),
        )
    finally:
        await conn.close()
    reverse_tracks = {track: name for name, track in tracks.items()}
    result = {name: [] for name in tracks}
    for row in rows:
        result[reverse_tracks[row["track"]]].append({
            "code": row["code"], "description": row["description"],
            "grade_band": (experience.get("metadata") or {}).get("grade_level") or "mixed",
            "similarity": float(row["similarity"]),
        })
    return result
