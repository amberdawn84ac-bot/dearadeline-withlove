"""Sole production author for learner experiences.

The living planner chooses the mission. This endpoint resolves or directly
authors one semantic canonical experience, adapts it, and streams it. It does
not route through the retired specialist/orchestrator lesson pipeline.
"""
import asyncio
import json
import logging
import re
import uuid

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.api.middleware import verify_student_access
from app.config import GEMINI_API_KEY, GOOGLE_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL
from app.schemas.api_models import LessonRequest
from app.curriculum.canonical_author import CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT
from app.curriculum.family_style import finalize_family_lesson, is_current_family_canonical
from app.connections.canonical_store import canonical_store, canonical_slug
from app.connections.student_experience_store import student_experience_store
from app.agents.adapter import adapt_canonical_for_student
from app.services.resource_router import resource_router, ResourceQuery, resource_block_from_packet
from app.services.learner_context import adaptation_for, learner_contribution
from app.services.rate_limit import enforce_rate_limit

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


async def _author(request: LessonRequest, resources: list[dict]) -> dict:
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
                parsed["blocks"] = blocks
                return parsed
            last_error = ValueError("author output failed semantic experience validation")
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(1)
    logger.error("[ExperienceAuthor] failed topic=%r: %s", request.topic, last_error)
    raise HTTPException(status_code=503, detail="Adeline could not author a valid experience yet. Nothing generic was substituted.")


async def _stream(request: LessonRequest):
    slug = shared_family_canonical_slug(request)
    plan_item_id = request.plan_item_id or f"canonical:{slug}"
    yield _sse({"type": "status", "message": "Opening today's planned experience…"})

    claim = await student_experience_store.claim(request.student_id, plan_item_id, slug)
    if claim.state == "ready" and claim.record:
        async for event in _emit_persisted(request, claim.record):
            yield event
        return
    if not claim.claimed:
        # Another request or instance owns generation. Wait for the durable row;
        # a reconnect may also discover the completed record here.
        for _ in range(240):
            await asyncio.sleep(0.25)
            record = await student_experience_store.get(request.student_id, plan_item_id)
            if record and record["status"] == "ready":
                async for event in _emit_persisted(request, record):
                    yield event
                return
            if record and record["status"] == "failed":
                yield _sse({"type": "error", "message": "That experience did not finish. Please retry."})
                return
        yield _sse({"type": "error", "message": "That experience is still being prepared. Reopen it in a moment."})
        return

    try:
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
            authored = await _author(request, packet["resources"])
            blocks = authored["blocks"]
        # Durable contracts live with the canonical blocks so the current DB schema
        # can preserve one source of truth without introducing a parallel lesson table.
            blocks[0].setdefault("metadata", {})["canonical_contract"] = {
                key: authored.get(key) for key in ("big_question", "learning_goal", "shared_experience", "investigation_scope_contract", "real_world_task", "portfolio_task", "printable_contract", "demonstration_contract", "family_roles")
            }
            canonical = {"id": str(uuid.uuid4()), "topic": request.topic, "track": request.track.value, "title": authored.get("title") or request.topic, "blocks": blocks, "oas_standards": [], "researcher_activated": False, "agent_name": "Canonical Experience Author"}
            await canonical_store.save(slug, canonical, pending=False)
        adaptation = await adaptation_for(request.student_id, request.grade_level, request.track.value)
        blocks = await adapt_canonical_for_student(
            {"topic": request.topic, "blocks": canonical.get("blocks") or []}, adaptation,
        )
        resource_block = resource_block_from_packet(packet)
        if resource_block:
            blocks.append(resource_block)
        experience_id = claim.record["id"]
        for index, block in enumerate(blocks):
            block.setdefault("block_id", f"{experience_id}-{index}")
        contract = ((canonical.get("blocks") or [{}])[0].get("metadata") or {}).get("canonical_contract") or {}
        metadata = {
            "canonical_slug": slug, "topic": request.topic, "grade_level": request.grade_level,
            "required_standard_codes": request.required_standard_codes,
            "investigation_scope_contract": contract.get("investigation_scope_contract") or {},
            "demonstration_contract": contract.get("demonstration_contract") or {},
            "learner_contribution": learner_contribution(contract, adaptation),
            "portfolio_task": contract.get("portfolio_task") or {},
        }
        record = await student_experience_store.save_ready(
            request.student_id, plan_item_id, title=canonical.get("title") or request.topic,
            track=request.track.value, blocks=blocks, metadata=metadata,
        )
        async for event in _emit_persisted(request, record):
            yield event
    except Exception as exc:
        await student_experience_store.mark_failed(request.student_id, plan_item_id, str(exc))
        logger.exception("[ExperienceAuthor] learner experience failed student=%s item=%s", request.student_id, plan_item_id)
        detail = exc.detail if isinstance(exc, HTTPException) else "Adeline could not finish that experience. Your Today plan is safe; please retry."
        yield _sse({"type": "error", "message": str(detail)})


async def _emit_persisted(request: LessonRequest, record: dict):
    """Return the exact durable learner record without rerunning any AI work."""
    lesson_id = record["id"]
    for block in record.get("blocks") or []:
        yield _sse({"type": "block", "block": block})
    metadata = record.get("metadata") or {}
    codes = list(metadata.get("required_standard_codes") or request.required_standard_codes)
    standards = [{"standard_id": code, "text": "Internal learning-plan target", "grade": 0, "source_type": "required_plan"} for code in codes]
    title = record.get("title") or request.topic
    credit_draft = {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"credit:{request.student_id}:{lesson_id}")),
        "lesson_id": lesson_id, "student_id": request.student_id, "course_title": title,
        "track": record.get("track") or request.track.value, "oas_standards": codes,
        "activity_description": f"Individual contribution to the family investigation: {title}",
        "credit_hours": 0.02, "credit_type": "CORE", "is_homestead_credit": request.is_homestead,
        "agent_name": "Canonical Experience Author", "researcher_activated": False,
    }
    yield _sse({"type": "done", "lesson_id": lesson_id, "title": title,
                "agent_name": "Canonical Experience Author", "oas_standards": standards,
                "credits_awarded": [credit_draft], "researcher_activated": False,
                "metadata": metadata})


@router.post("/build")
async def build_experience(request: LessonRequest, authorization: str | None = Header(default=None)):
    await verify_student_access(request.student_id, authorization)
    await enforce_rate_limit("experience-build", request.student_id, limit=8)
    return StreamingResponse(_stream(request), media_type="text/event-stream")


@router.post("/printable")
async def printable_experience(request: LessonRequest, authorization: str | None = Header(default=None)):
    """Render the same adapted canonical as a learner-facing printable dossier."""
    await verify_student_access(request.student_id, authorization)
    slug = shared_family_canonical_slug(request)
    plan_item_id = request.plan_item_id or f"canonical:{slug}"
    persisted = await student_experience_store.get(request.student_id, plan_item_id)
    if persisted and persisted["status"] == "ready":
        from app.services.investigation_printable import build_investigation_pdf
        pdf = build_investigation_pdf(
            title=persisted.get("title") or request.topic, topic=request.topic,
            grade_level=request.grade_level, blocks=persisted.get("blocks") or [],
        )
        filename = re.sub(r"[^a-z0-9]+", "-", (persisted.get("title") or request.topic).lower()).strip("-") or "investigation"
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}-field-dossier.pdf"'})
    canonical = await canonical_store.get(slug)
    if not canonical:
        raise HTTPException(status_code=404, detail="Open the investigation once before printing it.")
    adaptation = await adaptation_for(request.student_id, request.grade_level, request.track.value)
    blocks = await adapt_canonical_for_student(
        {"topic": request.topic, "blocks": canonical.get("blocks") or []},
        adaptation,
    )
    contract = ((canonical.get("blocks") or [{}])[0].get("metadata") or {}).get("canonical_contract") or {}
    if blocks:
        blocks[0].setdefault("metadata", {})["learner_contribution"] = learner_contribution(
            contract, adaptation
        )
    from app.services.investigation_printable import build_investigation_pdf
    pdf = build_investigation_pdf(title=canonical.get("title") or request.topic, topic=request.topic,
                                  grade_level=request.grade_level, blocks=blocks)
    filename = re.sub(r"[^a-z0-9]+", "-", (canonical.get("title") or request.topic).lower()).strip("-") or "investigation"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}-field-dossier.pdf"'})
