"""Durable, server-paced unit Spaces built from saved canonical experiences."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.persona import SCRIPTURE_TRANSLATION_POLICY
from app.api.middleware import require_internal_key, verify_student_access
from app.api.realtime import connection_manager
from app.config import GEMINI_MODEL, create_llm, get_db_conn
from app.connections.concept_encounter_store import concept_encounter_store
from app.connections.journal_store import journal_store
from app.services.mastery_credit import ConceptCredit, record_mastery_credit
from app.services.standards_mapper import _embed
from app.services.storage import evidence_upload_slot, read_upload_limited, upload_mastery_evidence

_ALLOWED_EVIDENCE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "video/mp4", "video/webm", "video/quicktime"}

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


class SpaceTurnRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=4000)
    expected_version: int = Field(ge=0)


class _TurnEvaluation(BaseModel):
    """What the LLM itself decides, before user_message/expected_version (already
    known server-side) are attached to build a full SpaceEvaluation for _apply_transition."""
    adeline_message: str = Field(min_length=1, max_length=4000)
    evaluation: Literal["correct", "partial", "incorrect", "not_answered"]
    recommended_action: Literal["stay", "advance", "complete_unit"]
    is_waiting_for_user: bool
    resource_triggers: list[Literal["show_microscope_diagram", "display_breakout_tracks"]] = Field(default_factory=list)
    off_plan_topic: OffPlanTopic | None = None
    suggested_replies: list[str] = Field(default_factory=list)
    log_fields: list[str] = Field(default_factory=list)
    offered_resource_ids: list[str] = Field(default_factory=list)


_TURN_SYSTEM_PROMPT = """You are Adeline, a warm but rigorous learning companion guiding one family through a unit Space.
Never claim credit, mastery, completion, or standards proficiency directly to the family — that is handled separately
from what you say. Ask no more than one question.
Offer zero to four suggested_replies. Use them for natural short answers such as yes/no, ready/not yet, or a small
set of genuine choices. Do not offer them when the learner needs to explain reasoning, show evidence, or write freely.
Use display_breakout_tracks only when subject-specific work is useful now, and show_microscope_diagram only when microscopy is relevant.
Write adeline_message as spoken prose. Do not use markdown (no **bold**, no * bullets).

""" + SCRIPTURE_TRANSLATION_POLICY + """

{activity_mode}

LOG FIELDS: only when the current activity asks the family to record observations or progress repeatedly over time —
a log kept across sessions, not a one-time answer. Set "log_fields" to 2-5 short labels for what THIS activity (and
your own adeline_message) still needs recorded. If they just submitted those observations, do not put the same fields
back in the question; leave log_fields matching tomorrow's entry. Leave "log_fields" empty for a one-time answer.

RABBIT HOLES: if the family's question or discussion genuinely goes beyond the activity above — a real tangent, not a
passing mention — set "off_plan_topic" to name that concept. Use tier "demonstrated" only when the family's answer
meets the same correctness bar you'd require to advance a planned activity. Use tier "encountered" when a real
question got a real, substantive answer but was not demonstrated to that same correctness bar. Leave "off_plan_topic"
null for every ordinary turn that stayed on the current activity.

Respond with ONLY a JSON object (no markdown fences, no commentary) matching exactly this shape:
{{"adeline_message": string, "evaluation": "correct"|"partial"|"incorrect"|"not_answered",
  "recommended_action": "stay"|"advance"|"complete_unit", "is_waiting_for_user": boolean,
  "resource_triggers": ["show_microscope_diagram"|"display_breakout_tracks", ...] (0-2 items),
  "off_plan_topic": null | {{"concept_name": string, "track": string|null, "tier": "encountered"|"demonstrated"}},
  "suggested_replies": [string, ...] (0-4 items), "log_fields": [string, ...] (0-5 items),
  "offered_resource_ids": [string, ...] (0-2 ids from the approved list, else empty)}}"""


def _turn_activity_mode(state: dict) -> str:
    teaching = _teaching_context(state)
    resources = _approved_resources_prompt(state)
    if state["status"] == "completed":
        return (
            f"{teaching}\n\n{resources}\n\n"
            "This unit's planned activities are already finished — you're in open conversation mode now. The family may "
            "ask follow-up questions, revisit something, or wander into a new question entirely. Answer genuinely and "
            "substantively; there is no \"next activity\" to advance to, so \"recommended_action\" should stay \"stay\" "
            "unless the family is clearly done, in which case \"complete_unit\" is fine (it is a safe no-op once already "
            f"complete).\n\nLAST ACTIVITY DISCUSSED: {(state.get('current_lesson') or {}).get('title') or 'Current lesson'}\n"
            f"{json.dumps(state.get('current_block'))}"
        )
    return (
        f"{teaching}\n\n{resources}\n\n"
        "The server has selected exactly one current activity. Teach that activity and evaluate only evidence in the "
        "learner's newest message. Never skip ahead. Recommend \"advance\" only when the learner has supplied the "
        "evidence or answer this current activity explicitly requires — a filled log is evidence, not by itself the "
        "understanding the activity is for. Use \"complete_unit\" only under that same rule "
        f"when this is the final activity. Otherwise recommend \"stay\".\n\nUNIT: {state.get('title')}\n"
        f"LESSON: {(state.get('current_lesson') or {}).get('title') or 'Current lesson'}\n"
        f"ACTIVITY {state['current_block_index'] + 1} OF {state['total_blocks']}:\n{json.dumps(state.get('current_block'))}"
    )


def _message_text(content) -> str:
    """LangChain/Gemini may return a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if value:
                    parts.append(str(value))
            else:
                value = getattr(item, "text", None) or getattr(item, "content", None)
                if value:
                    parts.append(str(value))
        return "\n".join(parts)
    return str(content or "")


def _parse_json_response(content) -> dict:
    """Decode a turn-evaluation JSON object from Gemini/LangChain output.

    Space turns used to `str(response.content)` and `json.loads` after a
    fence strip. That failed live in three distinct ways: a fence with
    nothing inside (`"```"`), JSON wrapped in LangChain content blocks,
    and prose around a valid object. Daily Bread already solved this;
    reuse the same extraction here.
    """
    raw = _message_text(content)
    raw_len = len(raw)
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if not text:
        raise ValueError(f"Empty JSON after fence-stripping (raw response was {raw_len} chars)")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"Gemini response did not contain a JSON object (raw response was {raw_len} chars)")
    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response JSON was not an object")
    return parsed


_ALLOWED_RESOURCE_TRIGGERS = {"show_microscope_diagram", "display_breakout_tracks"}


def _normalize_turn_payload(payload: dict) -> dict:
    """Coerce slightly-off Gemini JSON so a real evaluation isn't thrown away."""
    data = dict(payload)
    for key in ("evaluation", "recommended_action"):
        if isinstance(data.get(key), str):
            data[key] = data[key].strip().lower()
    if isinstance(data.get("is_waiting_for_user"), str):
        data["is_waiting_for_user"] = data["is_waiting_for_user"].strip().lower() in {"true", "1", "yes"}
    for key in ("resource_triggers", "suggested_replies", "log_fields", "offered_resource_ids"):
        if data.get(key) is None:
            data[key] = []
    if isinstance(data.get("resource_triggers"), str):
        data["resource_triggers"] = [data["resource_triggers"]]
    if isinstance(data.get("resource_triggers"), list):
        data["resource_triggers"] = [
            trigger for trigger in data["resource_triggers"] if trigger in _ALLOWED_RESOURCE_TRIGGERS
        ]
    if isinstance(data.get("offered_resource_ids"), str):
        data["offered_resource_ids"] = [data["offered_resource_ids"]]
    if isinstance(data.get("offered_resource_ids"), list):
        data["offered_resource_ids"] = [
            str(item).strip() for item in data["offered_resource_ids"] if str(item).strip()
        ][:2]
    off_plan = data.get("off_plan_topic")
    if not isinstance(off_plan, dict) or not str(off_plan.get("concept_name") or "").strip():
        data["off_plan_topic"] = None
    message = data.get("adeline_message")
    if isinstance(message, str) and len(message) > 4000:
        data["adeline_message"] = message[:4000]
    return data


def _salvage_spoken_turn(raw_text: str) -> _TurnEvaluation | None:
    """Keep a real spoken lesson if Gemini ignored the JSON contract.

    Confirmed live 2026-09-09 on the sourdough Space: gemini-2.5-flash
    taught ("when yeast eats sugar, what do you think it produces...")
    as prose. We logged a parse miss, retried, and the family waited
    ~18s for a JSON rewrite of a lesson we already had.
    """
    text = (raw_text or "").strip()
    if len(text) < 40:
        return None
    if text.startswith("{") or text.startswith("```"):
        return None
    if not re.search(r"[A-Za-z]", text):
        return None
    return _TurnEvaluation(
        adeline_message=text[:4000],
        evaluation="partial",
        recommended_action="stay",
        is_waiting_for_user=True,
    )


def _space_turn_llm():
    # Known-good constructor: this is how Space turns worked before JSON-mode
    # and thinking_budget=0. Those extra Gemini kwargs are not used by Daily
    # Bread or activities, and they 500 the whole turn if Railway's
    # langchain-google-genai rejects them (create_llm used to sit outside the
    # retry try/except). Keep the Daily Bread parser below; do not change the
    # request shape that was already working for this family.
    model = os.getenv("ADELINE_SPACE_MODEL", GEMINI_MODEL)
    return create_llm(model=model, max_tokens=4096)


async def _evaluate_turn(state: dict, user_message: str) -> _TurnEvaluation:
    lc_messages: list = [SystemMessage(content=_TURN_SYSTEM_PROMPT.format(activity_mode=_turn_activity_mode(state)))]
    for item in (state.get("messages") or [])[-12:]:
        content = str(item.get("content") or "")
        if not content:
            continue
        lc_messages.append(HumanMessage(content=content) if item.get("role") == "user" else AIMessage(content=content))
    lc_messages.append(HumanMessage(content=user_message))

    # adeline_message alone allows up to 4000 chars; the previous 1024-token
    # ceiling routinely truncated mid-string on a longer reply (confirmed live:
    # "Unterminated string starting at..." from json.loads), which surfaced to
    # families as an intermittent "could not reach the service" -- it wasn't
    # network flakiness, just not enough room to finish the JSON object.
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            llm = _space_turn_llm()
            response = await llm.ainvoke(lc_messages)
        except Exception as exc:
            # Confirmed live: the Gemini API key is on the free tier (20
            # requests/minute) and genuinely runs out of budget under real
            # multi-kid usage -- this was previously uncaught here, so a rate
            # limit or any other transport error crashed straight through to
            # a hard 502 instead of ever reaching the graceful fallback below.
            last_error = exc
            logger.warning("[Spaces] Turn evaluation call failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                await asyncio.sleep(2.0)
            continue
        content = response.content
        raw_text = _message_text(content)
        if not raw_text.strip():
            # Confirmed live: Gemini occasionally returns a fully empty
            # response (not truncated -- nothing at all). response_metadata
            # usually carries why (a finish_reason like SAFETY/RECITATION);
            # logging it is the only way to tell a content-filter block from
            # a transient blip without a family ever seeing the difference.
            last_error = ValueError("Empty LLM response")
            logger.warning(
                "[Spaces] Turn evaluation got an empty response (attempt %d/3), metadata=%s",
                attempt + 1, getattr(response, "response_metadata", None),
            )
            if attempt < 2:
                await asyncio.sleep(0.8)
            continue
        try:
            return _TurnEvaluation.model_validate(_normalize_turn_payload(_parse_json_response(content)))
        except Exception as exc:  # malformed/truncated JSON is rare but not impossible even with headroom
            last_error = exc
            logger.warning(
                "[Spaces] Turn evaluation parse failed (attempt %d/3): %s | raw_content=%r | metadata=%s",
                attempt + 1, exc, raw_text[:500], getattr(response, "response_metadata", None),
            )
            salvaged = _salvage_spoken_turn(raw_text)
            if salvaged is not None:
                logger.info("[Spaces] Salvaged spoken turn after JSON miss (attempt %d/3)", attempt + 1)
                return salvaged
            if attempt < 2:
                await asyncio.sleep(0.8)

    # Never leave the family stuck behind a dead end -- a genuine, honest
    # in-character fallback beats a scary "could not reach the service" error
    # the LLM flaked on every attempt. Nothing is credited or advanced; the
    # family can just try again, same as if they'd re-typed their message.
    logger.error("[Spaces] Turn evaluation exhausted all retries: %s", last_error)
    return _TurnEvaluation(
        adeline_message="I want to make sure I understand you correctly — could you say that again, maybe a little differently?",
        evaluation="not_answered", recommended_action="stay", is_waiting_for_user=True,
    )


def _lesson_for_block(metadata: dict, block_id: str, block_index: int) -> dict:
    lessons = ((metadata or {}).get("unit_plan") or {}).get("lessons") or []
    for lesson_index, lesson in enumerate(lessons):
        if block_id in (lesson.get("block_ids") or []):
            return {"index": lesson_index, "count": len(lessons), **lesson}
    return {"index": block_index, "count": max(len(lessons), 1), "lesson_id": block_id,
            "title": f"Activity {block_index + 1}", "block_ids": [block_id]}


def _grade_from_text(value) -> int:
    text = str(value or "").strip()
    if not text:
        return 8
    upper = text.upper()
    if upper in {"K", "KG", "KINDERGARTEN"} or upper.startswith("K-") or upper.startswith("K "):
        return 0
    return next((int(part) for part in text.replace("-", " ").split() if part.isdigit()), 8)


def _grade_from_metadata(metadata: dict) -> int:
    return _grade_from_text((metadata or {}).get("grade_level"))


def _band_for_grade(grade: int) -> str:
    return "elementary" if grade <= 5 else "middle" if grade <= 8 else "high_school"


def _tier_for_band(band: str) -> str:
    return "foundation" if band == "elementary" else "analysis" if band == "middle" else "synthesis"


def _first_name(name: str | None) -> str:
    token = str(name or "").strip().split()[0] if str(name or "").strip() else "this learner"
    return token[:40]


def _assignment_for_band(block: dict | None, band: str) -> str:
    roles = (block or {}).get("family_roles") or {}
    return str(roles.get(band) or "").strip()


def _learner_depth(metadata: dict, block: dict | None, student_grade: int | None = None) -> dict:
    """THIS speaker's depth. Prefer the child's User.gradeLevel over the unit's."""
    grade = student_grade if student_grade is not None else _grade_from_metadata(metadata)
    band = _band_for_grade(grade)
    return {
        "grade": grade,
        "band": band,
        "tier": _tier_for_band(band),
        "assignment": _assignment_for_band(block, band),
    }


def _learner_profile(row, block: dict | None, speaker_id: str | None = None) -> dict:
    data = dict(row)
    grade = _grade_from_text(data.get("gradeLevel"))
    band = _band_for_grade(grade)
    student_id = str(data.get("id") or "")
    return {
        "id": student_id,
        "name": _first_name(data.get("name")),
        "grade": grade,
        "band": band,
        "tier": _tier_for_band(band),
        "assignment": _assignment_for_band(block, band),
        "is_speaker": bool(speaker_id) and student_id == speaker_id,
    }

def _evaluation_to_bkt_correct(evaluation: str) -> bool | None:
    """Map a Space-turn evaluation onto BKT's boolean evidence.

    A filled log with no conceptual engagement is scored "partial" by the
    prompt; that still counts as positive evidence that they did the work.
    "not_answered" is a skip — no BKT update.
    """
    if evaluation in {"correct", "partial"}:
        return True
    if evaluation == "incorrect":
        return False
    return None


def _block_concept_ids(metadata: dict, lesson: dict | None, block: dict | None) -> list[str]:
    """Prefer the block's own concept_ids; fall back to the lesson's."""
    ids: list[str] = []
    for source in ((block or {}).get("concept_ids") or []):
        value = str(source or "").strip()
        if value and value not in ids:
            ids.append(value)
    if ids:
        return ids
    for source in ((lesson or {}).get("concept_ids") or []):
        value = str(source or "").strip()
        if value and value not in ids:
            ids.append(value)
    return ids


def _concept_names(metadata: dict, concept_ids: list[str]) -> list[str]:
    concepts = {
        str(item.get("concept_id")): (item.get("concept") or str(item.get("concept_id")))
        for item in ((metadata or {}).get("unit_plan") or {}).get("essential_concepts") or []
        if isinstance(item, dict) and item.get("concept_id")
    }
    return [concepts.get(cid) or cid for cid in concept_ids]


def _teaching_context(state: dict) -> str:
    """Grade, role, concepts, and the teach-from-evidence rule for the turn prompt.

    learner_depth is already computed on state; without this block the LLM
    only saw the activity JSON and collapsed into log-clerking. Family Spaces
    must teach THIS kid, not the unit's authored grade.
    """
    depth = state.get("learner_depth") or {}
    grade = depth.get("grade")
    band = depth.get("band") or ""
    tier = depth.get("tier") or ""
    assignment = str(depth.get("assignment") or "").strip()
    metadata = state.get("metadata") or {}
    lesson = state.get("current_lesson") or {}
    block = state.get("current_block") or {}
    names = _concept_names(metadata, _block_concept_ids(metadata, lesson, block))
    mastery = state.get("track_mastery") or {}
    household = [item for item in (state.get("household_learners") or []) if isinstance(item, dict)]

    lines = [
        "TEACH — do not clerk. A log is evidence for a science lesson (and math where the observations "
        "support a measurement or ratio), not the lesson itself.",
        "If the family just submitted observations: acknowledge them in one short sentence, interpret "
        "what they mean, then ask exactly ONE new question at THIS learner's level. Never re-ask fields "
        "they already answered this turn.",
        "Grade bands: elementary = concrete count, measure, simple why; middle = ratio, comparison, "
        "mechanism, prediction; high school = competing explanations, tradeoffs, quantitative reasoning.",
        "Adapt to THIS speaker's grade. Siblings sharing the investigation get different asks at their "
        "own bands — never clone the same question for every child.",
        "Filling a log without engaging the concept is at most \"partial\" and \"stay\". Use \"correct\" "
        "only when the newest message shows the understanding or evidence this activity actually requires.",
        "Drop an approved outside resource when it genuinely helps THIS turn — a sim to test a prediction, "
        "a game that models the concept, a video of the process, a primary source. Not on every log entry.",
        "NAMES: His name is not God. Use the original name the source writes (YHWH, Elohim, Yeshua), plus "
        "meaning and context. When English hid a name, or someone purposefully changed one, say so. One "
        "accurate note — do not turn a science turn into a sermon, and do not say God's design.",
    ]
    learner_bits = []
    if grade is not None and grade != "":
        learner_bits.append(f"grade {grade}")
    if band:
        learner_bits.append(band)
    if tier:
        learner_bits.append(f"tier={tier}")
    if mastery.get("band"):
        learner_bits.append(f"track mastery {mastery['band']}")
    if learner_bits:
        lines.append("LEARNER: " + ", ".join(learner_bits) + ".")
    if assignment:
        lines.append(f"THIS LEARNER'S ROLE ON THIS ACTIVITY: {assignment}")
    if household:
        lines.append("FAMILY LEARNERS (shared investigation — different asks, not cloned work):")
        for item in household:
            role = str(item.get("assignment") or "").strip()
            label = (
                f"- {item.get('name')}, grade {item.get('grade')}, {item.get('band')} "
                f"({item.get('tier')})"
            )
            lines.append(f"{label}: {role}" if role else label)
        speaker = next((item for item in household if item.get("is_speaker")), None)
        if speaker:
            lines.append(
                f"THIS SPEAKER: {speaker.get('name')} (grade {speaker.get('grade')}, {speaker.get('band')}). "
                "Pitch the one question at THEIR level. You may name another sibling only with a different "
                "ask at that sibling's band."
            )
        else:
            lines.append(
                "THIS SPEAKER: the family. Address the kids by name at their own levels. One spoken turn "
                "may hold two different asks. Never give every child the same worksheet."
            )
    if names:
        lines.append("CONCEPTS THIS ACTIVITY MUST TEACH: " + "; ".join(names) + ".")
    else:
        lines.append(
            "CONCEPTS THIS ACTIVITY MUST TEACH: derive them from the activity content "
            "(mechanism, measurement, prediction) — do not reduce the turn to data entry."
        )
    return "\n".join(lines)


_QUANTITATIVE_TERMS = frozenset({
    "ratio", "percent", "percentage", "graph", "measure", "measurement", "height",
    "hydration", "doubling", "algebra", "geometry", "angle", "statistics",
})


def _space_resource_topic(state: dict) -> str:
    lesson = state.get("current_lesson") or {}
    block = state.get("current_block") or {}
    names = _concept_names(
        state.get("metadata") or {},
        _block_concept_ids(state.get("metadata") or {}, lesson, block),
    )
    parts = [
        str(state.get("title") or ""),
        str(lesson.get("title") or ""),
        str(block.get("title") or ""),
        " ".join(names),
    ]
    return " ".join(part for part in parts if part).strip()[:240] or "family investigation"


def _authored_block_resources(state: dict) -> list[dict]:
    metadata = (state.get("current_block") or {}).get("metadata") or {}
    resources = metadata.get("resources") if isinstance(metadata, dict) else None
    if not isinstance(resources, list):
        return []
    return [item for item in resources if isinstance(item, dict) and item.get("id")]


def _merge_resources(*groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            rid = str(item.get("id") or "").strip()
            if not rid or rid in seen:
                continue
            seen.add(rid)
            merged.append(item)
    return merged


def _wants_math_tools(state: dict) -> bool:
    depth = state.get("learner_depth") or {}
    haystack = " ".join([
        _space_resource_topic(state),
        str(depth.get("assignment") or ""),
        str((state.get("current_block") or {}).get("content") or ""),
    ])
    words = {word.strip(".,:;!?()[]{}\"'").lower() for word in haystack.split() if word}
    return bool(words & _QUANTITATIVE_TERMS)


def _approved_resources_prompt(state: dict) -> str:
    items = state.get("approved_resources") or []
    if not items:
        return (
            "OUTSIDE RESOURCES: none approved for this activity right now. "
            "Do not invent a URL or tool. Leave offered_resource_ids empty."
        )
    lines = [
        "OUTSIDE RESOURCES: you teach; these approved tools are the lab, game, video, or archive. "
        "Offer 0-2 by id only when THIS turn the learner should actually open, play, watch, measure, or build. "
        "Empty list on a routine log acknowledgment. Never invent a URL. Opening a link is not mastery.",
        "Set offered_resource_ids to ids from this list only:",
    ]
    for item in items[:8]:
        rid = item.get("id") or ""
        provider = item.get("provider") or ""
        rtype = str(item.get("resource_type") or "").replace("_", " ")
        title = item.get("title") or ""
        lines.append(f"- {rid} — {provider} ({rtype}): {title}")
    return "\n".join(lines)


def _hydrate_offered_resources(catalog: list[dict], offered_ids: list[str]) -> list[dict]:
    by_id = {str(item.get("id")): item for item in catalog if item.get("id")}
    chosen: list[dict] = []
    seen: set[str] = set()
    for rid in offered_ids:
        key = str(rid).strip()
        item = by_id.get(key)
        if not item or key in seen:
            continue
        seen.add(key)
        chosen.append(item)
        if len(chosen) == 2:
            break
    return chosen


def _resource_block_for_offered(catalog: list[dict], offered_ids: list[str], track: str) -> dict | None:
    chosen = _hydrate_offered_resources(catalog, offered_ids)
    if not chosen:
        return None
    is_math = track == "APPLIED_MATHEMATICS"
    return {
        "block_type": "RESOURCE_COLLECTION",
        "experience_stage": "RESOURCE",
        "title": "Play with the idea, then prove it" if is_math else "Try this",
        "content": (
            "Choose the game, puzzle, or model matched to this idea. Change something, notice the pattern, then explain why. Time played is not mastery."
            if is_math else
            "Adeline remains the teacher. Open the resource, then come back and explain what you noticed, built, tested, or understood. Opening the link is not mastery."
        ),
        "metadata": {"resources": chosen, "requires_evidence": is_math},
        "family_style": True,
    }


async def _search_approved_resources(topic: str, track: str, grade_level: str, limit: int = 6) -> list[dict]:
    from app.services.resource_router import ResourceQuery, resource_router
    packet = await resource_router.search(ResourceQuery(
        topic=topic, track=track, grade_level=grade_level,
        interactive_preferred=True, limit=limit,
    ))
    return [item for item in (packet.get("resources") or []) if isinstance(item, dict)]


async def _attach_approved_resources(state: dict) -> dict:
    """Best-effort approved catalog for this activity. Never fails the turn."""
    topic = _space_resource_topic(state)
    grade = str((state.get("learner_depth") or {}).get("grade") or 8)
    track = state.get("track") or ""
    catalog = _authored_block_resources(state)
    try:
        catalog = _merge_resources(catalog, await _search_approved_resources(topic, track, grade))
        if _wants_math_tools(state) and track != "APPLIED_MATHEMATICS":
            catalog = _merge_resources(
                catalog,
                await _search_approved_resources(topic, "APPLIED_MATHEMATICS", grade, limit=4),
            )
    except Exception:
        logger.warning("[Spaces] resource catalog skipped (non-fatal) student=%s", state.get("student_id"), exc_info=True)
    return {**state, "approved_resources": catalog[:8]}


async def _update_space_bkt(
    *, student_id: str, track: str, metadata: dict, lesson: dict | None,
    block: dict | None, evaluation: str,
) -> None:
    """Per-turn BKT for the concepts this activity is actually teaching.

    Lesson-boundary record_mastery_credit still owns credit/journal. This
    updates P(L) on every real answer so the next turn's ZPD is not stale.
    Never raises — a tracker hiccup must not strand the family.
    """
    correct = _evaluation_to_bkt_correct(evaluation)
    if correct is None or not track:
        return
    concept_ids = _block_concept_ids(metadata, lesson, block)
    if not concept_ids:
        return
    from app.algorithms.bkt_tracker import update_bkt
    for concept_id in concept_ids:
        try:
            await update_bkt(student_id, concept_id, track, correct)
        except Exception:
            logger.warning(
                "[Spaces] BKT update failed student=%s concept=%s (non-fatal)",
                student_id, concept_id, exc_info=True,
            )


async def _attach_mastery_context(state: dict) -> dict:
    """Best-effort track mastery band for the prompt. Never fails the turn."""
    student_id = state.get("student_id")
    track = state.get("track") or ""
    if not student_id:
        return state
    try:
        from app.models.student import load_student_state
        student_state = await load_student_state(student_id)
        tm = student_state.get(track) if track else None
        if tm:
            return {**state, "track_mastery": {"band": tm.mastery_band.value, "score": tm.mastery_score}}
    except Exception:
        logger.warning("[Spaces] mastery context skipped (non-fatal) student=%s", student_id, exc_info=True)
    return state


async def _attach_household_learners(state: dict) -> dict:
    """Load this child and siblings so the turn teaches each kid's grade.

    Family Spaces used the unit's grade_level, so siblings got the same
    question. User.gradeLevel is the child's actual grade. A lookup miss
    must never 500 the family — fall back to unit depth.
    """
    student_id = str(state.get("student_id") or "")
    if not student_id:
        return state
    role = ""
    members: list = []
    try:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT id, name, role, "gradeLevel", "parentId" FROM "User" WHERE id = $1',
                student_id,
            )
            if not row:
                return state
            role = str(row["role"] or "").upper()
            parent_id = student_id if role == "PARENT" else row["parentId"]
            members = []
            if parent_id:
                members = await conn.fetch(
                    '''SELECT id, name, role, "gradeLevel" FROM "User"
                       WHERE (id = $1 OR "parentId" = $1) AND role = 'STUDENT'
                       ORDER BY name''',
                    parent_id,
                )
            if not members and role == "STUDENT":
                members = [row]
        finally:
            await conn.close()
    except Exception:
        logger.warning("[Spaces] household learners skipped (non-fatal) student=%s", student_id, exc_info=True)
        return state

    block = state.get("current_block")
    speaker_id = student_id if role == "STUDENT" else None
    learners = [_learner_profile(member, block, speaker_id) for member in members]
    learners = [item for item in learners if item.get("id")]
    if not learners:
        return state

    speaker = next((item for item in learners if item.get("is_speaker")), None)
    depth = dict(state.get("learner_depth") or {})
    if speaker:
        depth = {
            "grade": speaker["grade"],
            "band": speaker["band"],
            "tier": speaker["tier"],
            "assignment": speaker["assignment"],
            "name": speaker["name"],
        }
    return {**state, "household_learners": learners, "learner_depth": depth}


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
        "track": experience.get("track") or (experience.get("metadata") or {}).get("track") or "",
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
                "concepts": [credit.concept_name for credit in concept_credits if credit.concept_name],
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

        credited_names = [credit.concept_name for credit in concept_credits if credit.concept_name]
        await connection_manager.emit_to_student_channels(student_id, "space_insight", {
            "kind": "credited", "track": track, "concept_names": credited_names,
            "context": lesson.get("title") or None,
        })
        return credited_names
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
            await connection_manager.emit_to_student_channels(student_id, "space_insight", {
                "kind": "encountered", "track": track, "concept_names": [topic.concept_name],
                "context": "a rabbit hole in a Space",
            })
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
        await connection_manager.emit_to_student_channels(student_id, "space_insight", {
            "kind": "credited", "track": track, "concept_names": [topic.concept_name],
            "context": "a rabbit hole in a Space",
        })
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
            'SELECT id::text, status, title, track, "blocksJson", "metadataJson" FROM "StudentExperience" '
            'WHERE "studentId"=$1 AND "planItemId"=$2', student_id, plan_item_id,
        )
        if not row or row["status"] != "ready":
            raise HTTPException(status_code=409, detail="The unit must finish preparing before its Space can open.")
        experience = {"id": row["id"], "title": row["title"], "track": row["track"] or "",
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


def _space_list_item(row) -> dict:
    return {
        "plan_item_id": row["planItemId"], "title": row["title"], "track": row["track"],
        "status": row["status"], "completed_blocks": len(row["completedBlockIds"] or []),
        "total_blocks": row["total_blocks"] or 0,
        "updated_at": row["updatedAt"].isoformat() if row["updatedAt"] else None,
    }


@router.get("/{student_id}")
async def list_spaces(student_id: str, response: Response,
                      _user_id: str = Depends(verify_student_access)):
    """Every Space this student has actually opened — active and completed —
    most-recently-active first. Does not include queued-but-not-yet-started
    investigations; those are previewed via the learning plan instead, since
    they have no StudentExperience/SpaceSession until they actually begin."""
    response.headers["Cache-Control"] = "private, no-store"
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            '''SELECT s."planItemId", s.status, s."completedBlockIds", s."updatedAt",
                      e.title, e.track, jsonb_array_length(e."blocksJson") AS total_blocks
                 FROM "SpaceSession" s
                 JOIN "StudentExperience" e ON e.id = s."experienceId"
                WHERE s."studentId" = $1
                ORDER BY s."updatedAt" DESC''',
            student_id,
        )
    finally:
        await conn.close()
    return [_space_list_item(row) for row in rows]


@router.get("/{student_id}/{plan_item_id}")
async def read_space(student_id: str, plan_item_id: str, response: Response,
                     _user_id: str = Depends(verify_student_access)):
    response.headers["Cache-Control"] = "private, no-store"
    session, experience = await _load_or_create(student_id, plan_item_id)
    return _state(session, experience)


async def _apply_transition(student_id: str, plan_item_id: str, body: SpaceEvaluation) -> dict:
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
            evaluated_block = blocks[index] if blocks else None
            current_id = evaluated_block.get("block_id") if evaluated_block else None
            evaluated_lesson = _lesson_for_block(metadata, current_id or "", index)
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
                      "track": experience_row["track"] or "", "blocks": blocks, "metadata": metadata}
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

        asyncio.create_task(_update_space_bkt(
            student_id=student_id, track=experience_row["track"] or "",
            metadata=metadata, lesson=evaluated_lesson, block=evaluated_block,
            evaluation=body.evaluation,
        ))

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


@router.post("/{student_id}/{plan_item_id}/photo")
async def upload_space_photo(
    student_id: str, plan_item_id: str,
    description: str = Form(""),
    file: UploadFile = File(...),
    _user_id: str = Depends(verify_student_access),
):
    """Attach a photo of the finished project to this Space's portfolio entry.

    Only meaningful once at least one lesson from this Space has already been
    credited (see _credit_newly_completed_lesson) -- that's what creates the
    student_journal row this photo attaches to. A family photographing a
    still-in-progress unit before any lesson has been demonstrated gets a
    clear 409 rather than a silently discarded upload.
    """
    content_type = file.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(status_code=400, detail="Use a JPG, PNG, GIF, MP4, WebM, or MOV file")

    # Confirms the Space exists and belongs to this student before spending
    # upload effort on it -- _load_or_create raises 409 if not yet ready.
    await _load_or_create(student_id, plan_item_id)

    try:
        async with evidence_upload_slot():
            file_bytes = await read_upload_limited(file)
            storage_key = await upload_mastery_evidence(
                student_id=student_id, standard_id=plan_item_id,
                file_bytes=file_bytes, content_type=content_type, original_filename=file.filename,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=413 if isinstance(exc, ValueError) else 503, detail=str(exc)) from exc

    attached = await journal_store.attach_evidence_by_plan_item(student_id, plan_item_id, {
        "type": "artifact", "url": f"evidence-key://{storage_key}",
        "title": description or file.filename or "Finished project photo",
    })
    if not attached:
        raise HTTPException(
            status_code=409,
            detail="Adeline hasn't recorded any mastery for this unit yet, so there's no portfolio entry to attach "
                   "this photo to. Finish a bit more of the Space first, then add the photo.",
        )
    return {"evidence_id": str(uuid.uuid4()), "attached": True}


@router.post("/{student_id}/{plan_item_id}/transition", dependencies=[Depends(require_internal_key)])
async def transition_space(student_id: str, plan_item_id: str, body: SpaceEvaluation,
                           _user_id: str = Depends(verify_student_access)):
    return await _apply_transition(student_id, plan_item_id, body)


@router.post("/{student_id}/{plan_item_id}/turn")
async def space_turn(student_id: str, plan_item_id: str, body: SpaceTurnRequest,
                     _user_id: str = Depends(verify_student_access)):
    """Single round trip for a Space conversation turn: evaluate the learner's
    message with the LLM in-process (no separate AI-gateway hop from the
    frontend), then apply the resulting transition. Consolidates what used to
    be a Next.js route calling out to Vercel's AI Gateway plus two more HTTP
    calls back into this same backend."""
    session, experience = await _load_or_create(student_id, plan_item_id)
    state = await _attach_approved_resources(
        await _attach_mastery_context(await _attach_household_learners(_state(session, experience)))
    )

    try:
        evaluation = await _evaluate_turn(state, body.user_message)
    except Exception:
        logger.exception("[Spaces] Turn evaluation failed student=%s plan_item=%s", student_id, plan_item_id)
        raise HTTPException(status_code=502, detail="Adeline could not continue this Space just now.")

    result = await _apply_transition(student_id, plan_item_id, SpaceEvaluation(
        adeline_message=evaluation.adeline_message,
        evaluation=evaluation.evaluation,
        recommended_action=evaluation.recommended_action,
        is_waiting_for_user=evaluation.is_waiting_for_user,
        resource_triggers=evaluation.resource_triggers,
        off_plan_topic=evaluation.off_plan_topic,
        user_message=body.user_message,
        expected_version=body.expected_version,
    ))

    try:
        result["breakout_data"] = (
            await _breakout_data(student_id, plan_item_id)
            if "display_breakout_tracks" in evaluation.resource_triggers else None
        )
    except Exception:
        logger.exception(
            "[Spaces] breakout_data failed after committed turn student=%s plan_item=%s",
            student_id, plan_item_id,
        )
        result["breakout_data"] = None
    result["suggested_replies"] = evaluation.suggested_replies
    result["log_fields"] = evaluation.log_fields
    try:
        result["resource_block"] = _resource_block_for_offered(
            state.get("approved_resources") or [],
            evaluation.offered_resource_ids,
            state.get("track") or "",
        )
    except Exception:
        logger.warning("[Spaces] resource block skipped (non-fatal) student=%s", student_id, exc_info=True)
        result["resource_block"] = None
    return result


async def _breakout_data(student_id: str, plan_item_id: str) -> dict:
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


@router.get("/{student_id}/{plan_item_id}/breakout-standards")
async def breakout_standards(student_id: str, plan_item_id: str,
                             _user_id: str = Depends(verify_student_access)):
    return await _breakout_data(student_id, plan_item_id)
