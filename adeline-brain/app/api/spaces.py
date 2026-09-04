"""Durable, server-paced unit Spaces built from saved canonical experiences."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.middleware import require_internal_key, verify_student_access
from app.config import get_db_conn
from app.services.standards_mapper import _embed

router = APIRouter(prefix="/brain/spaces", tags=["spaces"])


class SpaceMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class SpaceEvaluation(BaseModel):
    adeline_message: str = Field(min_length=1, max_length=4000)
    evaluation: Literal["correct", "partial", "incorrect", "not_answered"]
    recommended_action: Literal["stay", "advance", "complete_unit"]
    is_waiting_for_user: bool
    resource_triggers: list[Literal["show_microscope_diagram", "display_breakout_tracks"]] = Field(default_factory=list)
    user_message: str = Field(min_length=1, max_length=4000)
    expected_version: int = Field(ge=0)


def _lesson_for_block(metadata: dict, block_id: str, block_index: int) -> dict:
    lessons = ((metadata or {}).get("unit_plan") or {}).get("lessons") or []
    for lesson_index, lesson in enumerate(lessons):
        if block_id in (lesson.get("block_ids") or []):
            return {"index": lesson_index, "count": len(lessons), **lesson}
    return {"index": block_index, "count": max(len(lessons), 1), "lesson_id": block_id,
            "title": f"Activity {block_index + 1}", "block_ids": [block_id]}


def _learner_depth(metadata: dict, block: dict | None) -> dict:
    grade_text = str((metadata or {}).get("grade_level") or "8")
    grade = next((int(part) for part in grade_text.replace("-", " ").split() if part.isdigit()), 8)
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


async def _load_or_create(student_id: str, plan_item_id: str) -> tuple[dict, dict]:
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow(
            'SELECT id::text, status, title, "blocksJson", "metadataJson" FROM "StudentExperience" '
            'WHERE "studentId"=$1 AND "planItemId"=$2', student_id, plan_item_id,
        )
        if not row or row["status"] != "ready":
            raise HTTPException(status_code=409, detail="The unit must finish preparing before its Space can open.")
        experience = {"id": row["id"], "title": row["title"], "blocks": row["blocksJson"], "metadata": row["metadataJson"]}
        session = await conn.fetchrow(
            'INSERT INTO "SpaceSession" ("studentId","planItemId","experienceId") VALUES ($1,$2,$3::text) '
            'ON CONFLICT ("studentId","planItemId") DO UPDATE SET "experienceId"=EXCLUDED."experienceId" '
            'RETURNING id::text, "studentId", "planItemId", "experienceId", "currentBlockIndex", '
            '"completedBlockIds", "messagesJson", status, version', student_id, plan_item_id, row["id"],
        )
        return dict(session), experience
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
                'SELECT id::text, title, "blocksJson", "metadataJson" FROM "StudentExperience" '
                'WHERE "studentId"=$1 AND "planItemId"=$2 AND status=\'ready\'', student_id, plan_item_id,
            )
            session_row = await conn.fetchrow(
                'SELECT id::text, "studentId", "planItemId", "experienceId", "currentBlockIndex", '
                '"completedBlockIds", "messagesJson", status, version FROM "SpaceSession" '
                'WHERE "studentId"=$1 AND "planItemId"=$2 FOR UPDATE', student_id, plan_item_id,
            )
            if not experience_row or not session_row:
                raise HTTPException(status_code=404, detail="Space not found")
            if session_row["version"] != body.expected_version:
                raise HTTPException(status_code=409, detail="Space changed in another window. Refresh and continue.")

            blocks = experience_row["blocksJson"] or []
            index = min(session_row["currentBlockIndex"], max(len(blocks) - 1, 0))
            completed = list(session_row["completedBlockIds"] or [])
            may_advance = body.evaluation == "correct" and body.recommended_action in {"advance", "complete_unit"}
            if may_advance and blocks:
                current_id = blocks[index].get("block_id")
                if current_id and current_id not in completed:
                    completed.append(current_id)
                if index < len(blocks) - 1:
                    index += 1
            status = "completed" if blocks and len(completed) >= len(blocks) else "active"
            messages = list(session_row["messagesJson"] or [])[-38:]
            messages.extend([{"role": "user", "content": body.user_message},
                             {"role": "assistant", "content": body.adeline_message}])
            updated = await conn.fetchrow(
                'UPDATE "SpaceSession" SET "currentBlockIndex"=$1, "completedBlockIds"=$2, '
                '"messagesJson"=$3::jsonb, status=$4, version=version+1, "updatedAt"=NOW() '
                'WHERE id=$5 RETURNING id, "studentId", "planItemId", "experienceId", '
                '"currentBlockIndex", "completedBlockIds", "messagesJson", status, version',
                index, completed, messages, status, session_row["id"],
            )
        experience = {"id": experience_row["id"], "title": experience_row["title"],
                      "blocks": experience_row["blocksJson"], "metadata": experience_row["metadataJson"]}
        result = _state(dict(updated), experience)
        result["resource_triggers"] = body.resource_triggers
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
