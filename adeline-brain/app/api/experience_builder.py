"""Sole production author for learner experiences.

The living planner chooses the mission. This endpoint resolves or directly
authors one semantic canonical experience, adapts it, and streams it. It does
not route through the retired specialist/orchestrator lesson pipeline.
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.api.middleware import verify_student_access
from app.config import GEMINI_API_KEY, GOOGLE_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL
from app.schemas.api_models import LessonRequest
from app.curriculum.canonical_author import CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT
from app.curriculum.family_style import finalize_family_lesson, is_current_family_canonical
from app.connections.canonical_store import canonical_store, canonical_slug
from app.agents.adapter import AdaptationRequest, adapt_canonical_for_student
from app.services.resource_router import resource_router, ResourceQuery, resource_block_from_packet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experience", tags=["canonical-experience"])


def shared_family_canonical_slug(request: LessonRequest) -> str:
    return canonical_slug(request.topic, request.track.value)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _json_object(raw: str) -> dict:
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1]) if start >= 0 and end > start else {}


async def _author(request: LessonRequest, resources: list[dict]) -> list[dict]:
    import openai
    key = GEMINI_API_KEY or GOOGLE_API_KEY
    if not key:
        raise HTTPException(status_code=503, detail="The Canonical Experience Author is not configured.")
    client = openai.AsyncOpenAI(api_key=key, base_url=GEMINI_BASE_URL)
    prompt = (
        f"Author the canonical shared family experience. Topic: {request.topic}. Track: {request.track.value}. "
        "This is the actual lesson, not an outline, article, sequence of narrative boxes, worksheet, or sketchnote. "
        "Use the routed resources only when useful and obey their use_mode and license. "
        "Return the exact JSON contract. Every block must directly declare experience_stage.\n\n"
        f"ROUTED OUTSIDE TOOLS AND SOURCES:\n{json.dumps(resources[:6], ensure_ascii=False)}"
    )
    last_error = None
    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=GEMINI_MODEL, max_tokens=8000,
                messages=[{"role": "system", "content": CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            )
            parsed = _json_object(response.choices[0].message.content or "")
            blocks = finalize_family_lesson(parsed.get("blocks") or [], request.topic, track=request.track.value)
            if blocks:
                return blocks
            last_error = ValueError("author output failed semantic experience validation")
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(1)
    logger.error("[ExperienceAuthor] failed topic=%r: %s", request.topic, last_error)
    raise HTTPException(status_code=503, detail="Adeline could not author a valid experience yet. Nothing generic was substituted.")


async def _stream(request: LessonRequest):
    lesson_id = str(uuid.uuid4())
    slug = shared_family_canonical_slug(request)
    yield _sse({"type": "status", "message": "Opening today's planned experience…"})
    canonical = await canonical_store.get(slug)
    packet = await resource_router.search(ResourceQuery(topic=request.topic, track=request.track.value, grade_level=request.grade_level))
    if canonical:
        stored_blocks = canonical.get("blocks") or []
        if isinstance(stored_blocks, str):
            stored_blocks = json.loads(stored_blocks)
            canonical["blocks"] = stored_blocks
        if not is_current_family_canonical(stored_blocks):
            await canonical_store.archive(slug, reason="retired_lesson_pipeline_format")
            canonical = None
    if not canonical or canonical.get("pending_approval"):
        yield _sse({"type": "status", "message": "Adeline is authoring the experience from the living plan…"})
        blocks = await _author(request, packet["resources"])
        canonical = {"id": str(uuid.uuid4()), "topic": request.topic, "track": request.track.value, "title": request.topic, "blocks": blocks, "oas_standards": []}
        await canonical_store.save(slug, canonical, pending=False)
    blocks = await adapt_canonical_for_student(
        {"topic": request.topic, "blocks": canonical.get("blocks") or []},
        AdaptationRequest(grade_level=request.grade_level, track=request.track.value),
    )
    resource_block = resource_block_from_packet(packet)
    if resource_block:
        blocks.append(resource_block)
    for index, block in enumerate(blocks):
        block.setdefault("block_id", f"{lesson_id}-{index}")
        yield _sse({"type": "block", "block": block})
    standards = [{"standard_id": code, "text": "Internal learning-plan target", "grade": 0, "source_type": "required_plan"} for code in request.required_standard_codes]
    yield _sse({"type": "done", "lesson_id": lesson_id, "title": canonical.get("title") or request.topic, "agent_name": "Canonical Experience Author", "oas_standards": standards, "credits_awarded": [], "researcher_activated": False})


@router.post("/build")
async def build_experience(request: LessonRequest, authorization: str | None = Header(default=None)):
    await verify_student_access(request.student_id, authorization)
    return StreamingResponse(_stream(request), media_type="text/event-stream")
