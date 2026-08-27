"""Sole production author for learner experiences.

The living planner chooses the mission. This endpoint resolves or directly
authors one semantic canonical experience, adapts it, and streams it. It does
not route through the retired specialist/orchestrator lesson pipeline.
"""
import asyncio
import contextlib
import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, AsyncIterator, Sequence
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.api.middleware import verify_student_access
from app.config import GEMINI_API_KEY, GOOGLE_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL
from app.schemas.api_models import LessonRequest
from app.curriculum.canonical_author import (
    CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT,
    CONTRACT_VERSION,
    PROMPT_VERSION,
    enforce_non_exposure_mastery,
    validate_canonical_contract,
    validate_experience_substance,
    validate_flow_composition,
)
from app.curriculum.family_style import finalize_family_lesson, is_current_family_canonical
from app.connections.canonical_store import canonical_store, canonical_slug
from app.connections.student_experience_store import student_experience_store
from app.agents.adapter import adapt_canonical_for_student
from app.services.resource_router import resource_router, ResourceQuery, resource_block_from_packet
from app.services.learner_context import adaptation_for, learner_contribution
from app.services.rate_limit import enforce_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experience", tags=["canonical-experience"])

PROGRESS_INTERVAL_SECONDS = 12.0
AUTHOR_PROGRESS_MESSAGES = (
    "Gathering the strongest records and real-world materials…",
    "Designing one shared investigation for the whole family…",
    "Building meaningful choices, action, and portfolio evidence…",
    "Checking that every task demonstrates real understanding…",
    "Protecting source accuracy and removing busywork…",
)
ADAPTER_PROGRESS_MESSAGES = (
    "Preparing this learner's role in the shared experience…",
    "Making the entry point clear without simplifying the ideas…",
)


def shared_family_canonical_slug(request: LessonRequest) -> str:
    return canonical_slug(request.topic, request.track.value)


def canonical_resource_query(request: LessonRequest) -> ResourceQuery:
    """Ask for item-level primary evidence first when authoring true history."""
    requires_primary = request.track.value in {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"}
    is_history = request.track.value == "TRUTH_HISTORY"
    # Archive APIs search literal metadata. Keep the historical subjects while
    # removing Dear Adeline's framing question, which can otherwise turn a
    # strong topic into a zero-result exact-ish query.
    archive_topic = re.split(r"[:?]", request.topic, maxsplit=1)[0].strip()
    return ResourceQuery(
        topic=archive_topic if is_history and archive_topic else request.topic,
        track=request.track.value,
        grade_level=request.grade_level,
        resource_types=("PRIMARY_SOURCE",) if requires_primary else (),
        interactive_preferred=not requires_primary,
        limit=8 if requires_primary else 5,
    )


def planned_resource_packet(request: LessonRequest) -> dict[str, Any]:
    """Validate the planner's small link-only packet for learner display.

    The packet was selected against the exact progression target. Keeping it
    with the persisted plan avoids a fresh outside search every time a saved
    skill lesson opens.
    """
    packet = request.resource_packet if isinstance(request.resource_packet, dict) else {}
    resources = [item for item in packet.get("resources", []) if isinstance(item, dict)]
    return {
        "topic": str(packet.get("topic") or request.topic),
        "track": str(packet.get("track") or request.track.value),
        "resources": resources[:5],
        "rules": [str(rule) for rule in packet.get("rules", []) if str(rule).strip()],
    }


def merge_resource_packets(*packets: dict[str, Any]) -> dict[str, Any]:
    resources: list[dict] = []
    rules: list[str] = []
    seen: set[str] = set()
    topic = ""
    track = ""
    for packet in packets:
        if not isinstance(packet, dict):
            continue
        topic = topic or str(packet.get("topic") or packet.get("query", {}).get("topic") or "")
        track = track or str(packet.get("track") or packet.get("query", {}).get("track") or "")
        for item in packet.get("resources", []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or item.get("source_url") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            resources.append(item)
        for rule in packet.get("rules", []):
            value = str(rule).strip()
            if value and value not in rules:
                rules.append(value)
    return {"topic": topic, "track": track, "resources": resources[:8], "rules": rules}


def has_verified_history_source(resources: list[dict]) -> bool:
    return any(
        str(item.get("resource_type") or "").upper() == "PRIMARY_SOURCE"
        and str(item.get("availability") or "").upper()
        in {"VERIFIED_API_ITEM", "VERIFIED_ARCHIVE_ITEM"}
        and str(item.get("source_url") or "").startswith(("https://", "http://"))
        and str(item.get("provider") or "").strip()
        for item in resources
        if isinstance(item, dict)
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _json_object(raw: str) -> dict:
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1]) if start >= 0 and end > start else {}


def sequence_bridge_block(request: LessonRequest) -> dict | None:
    """Create a deterministic just-in-time bridge for non-graph-verified work.

    This is part of the real investigation, not a prerequisite worksheet.  It
    keeps curiosity available while preventing the lesson from assuming that
    an unverified foundation is already mastered.
    """
    if request.sequence_policy != "SUPPORTED" or not request.bridge_required:
        return None
    return {
        "block_id": "sequence-readiness-bridge",
        "block_type": "TEXT",
        "title": "Connect before you build",
        "content": (
            f"Begin by explaining, showing, or drawing what you already understand about {request.topic}. "
            "Use the first concrete example or source in this investigation to identify the foundation the "
            "larger work depends on. If that foundation is shaky, ask Adeline to teach it, then try one fresh "
            "example before using it in the real investigation. This is part of the work—not a separate worksheet."
        ),
        "experience_stage": "INVITATION",
        "evidence": [],
        "is_silenced": False,
        "family_roles": {
            "elementary": "Show the idea with objects, a picture, or your own words.",
            "middle": "Explain the foundation and test it with one concrete example.",
            "high_school": "State the foundation, identify uncertainty, and verify it before dependent analysis.",
        },
        "metadata": {
            "sequence_bridge": True,
            "sequence_policy": request.sequence_policy,
            "prerequisite_concept_ids": request.prerequisite_concept_ids,
            "prerequisite_standard_ids": request.prerequisite_standard_ids,
            "not_mastery_evidence": True,
        },
    }


_SKILL_FAMILIES = {
    "math": {
        "number_arithmetic": frozenset({"count", "number", "addition", "subtraction", "multiply", "division", "place value"}),
        "ratio_proportion": frozenset({"ratio", "proportion", "percent", "percentage", "rate", "unit rate", "scale"}),
        "measurement_geometry": frozenset({"measure", "measurement", "length", "area", "volume", "angle", "geometry", "dimension", "scale drawing"}),
        "data_statistics": frozenset({"data", "statistic", "graph", "chart", "average", "median", "sample", "trend", "probability"}),
        "finance": frozenset({"budget", "cost", "price", "interest", "profit", "revenue", "financial"}),
        "advanced_functions": frozenset({"function", "limit", "trigonometry", "polynomial", "logarithm", "calculus"}),
    },
    "literacy": {
        "source_reading": frozenset({"close read", "source analysis", "primary source", "cite", "citation", "text evidence", "corroborate"}),
        "research": frozenset({"research", "question", "source", "bibliography", "note-taking", "inquiry"}),
        "argument": frozenset({"argument", "claim", "reason", "evidence", "persuade", "rhetoric", "counterclaim", "debate"}),
        "writing": frozenset({"write", "writing", "draft", "revise", "edit", "letter", "report", "essay"}),
        "speaking_listening": frozenset({"listen", "discussion", "respond", "verbal", "nonverbal", "interview", "present", "speech", "oral"}),
        "language": frozenset({"grammar", "sentence", "spelling", "vocabulary", "punctuation", "word choice"}),
        "literature": frozenset({"literature", "story", "poem", "poetry", "character", "theme", "symbolism", "narrative"}),
    },
    "history": {
        "chronology_causation": frozenset({"chronology", "timeline", "cause", "consequence", "turning point", "historical context"}),
        "historical_evidence": frozenset({"primary source", "archive", "corroborate", "sourcing", "historical claim", "propaganda"}),
    },
    "science": {
        "scientific_inquiry": frozenset({"observe", "observation", "hypothesis", "experiment", "variable", "evidence", "scientific method"}),
        "life_earth_physical": frozenset({"ecosystem", "organism", "plant", "chemical", "energy", "force", "matter", "climate", "biology"}),
    },
    "homesteading": {
        "land_and_build": frozenset({"garden", "soil", "seed", "grow", "farm", "preserve", "greenhouse", "build", "water", "food"}),
    },
    "discipleship": {
        "scripture_and_theology": frozenset({"scripture", "bible", "hebrew", "greek", "verse", "exegesis", "theology", "stewardship", "discernment"}),
    },
    "justice": {
        "power_and_accountability": frozenset({"justice", "harm", "power", "accountability", "advocacy", "inequality", "recipient", "remedy"}),
    },
    "health": {
        "health_evidence": frozenset({"health", "body", "nutrition", "risk", "exposure", "dose", "prevention", "medical"}),
    },
    "government_economics": {
        "institutions_and_markets": frozenset({"government", "law", "policy", "regulation", "market", "price", "profit", "incentive", "institution", "legislator"}),
    },
    "creative_economy": {
        "design_and_value": frozenset({"design", "create", "make", "art", "visual", "product", "customer", "portfolio", "communicate"}),
    },
}

_DOMAIN_DISCIPLINE_TERMS = {
    "math": frozenset({"math", "mathematics", "arithmetic", "algebra", "geometry", "statistics", "measurement", "finance"}),
    "literacy": frozenset({"literacy", "english", "language arts", "reading", "writing", "rhetoric", "communication", "literature"}),
    "history": frozenset({"history", "historical", "chronology"}),
    "science": frozenset({"science", "biology", "chemistry", "physics", "ecology", "earth science"}),
    "homesteading": frozenset({"homesteading", "agriculture", "gardening", "farm", "food preservation"}),
    "discipleship": frozenset({"discipleship", "scripture", "theology", "biblical studies"}),
    "justice": frozenset({"justice", "advocacy", "changemaking", "accountability"}),
    "health": frozenset({"health", "medicine", "nutrition", "public health"}),
    "government_economics": frozenset({"government", "economics", "civics", "law", "public policy"}),
    "creative_economy": frozenset({"creative economy", "art", "design", "entrepreneurship", "business"}),
}


def _skill_families_for_text(domain: str, text: str) -> set[str]:
    normalized = text.lower()
    return {
        family for family, terms in _SKILL_FAMILIES.get(domain, {}).items()
        if any(term in normalized for term in terms)
    }


def skill_connections_for_contract(contract: dict, targets: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate genuine cross-disciplinary fits from unrelated skill practice.

    The canonical author must already have named and justified a discipline in
    the shared experience. Topic similarity alone cannot turn a math or literacy
    target into themed work.
    """
    design = contract.get("experience_design") or {}
    declared_disciplines = " ".join(
        str(item).lower() for item in design.get("disciplines_integrated") or []
    )
    integration_text = json.dumps({
        "disciplines_integrated": design.get("disciplines_integrated") or [],
        "integration_rationale": design.get("integration_rationale") or "",
        "central_question": design.get("central_question") or "",
        "real_world_task": contract.get("real_world_task") or {},
        "mastery_evidence_map": contract.get("mastery_evidence_map") or [],
    }, ensure_ascii=False).lower()
    integrated: list[dict] = []
    separate: list[dict] = []
    for raw in targets:
        target = dict(raw)
        domain = str(target.get("domain") or "").lower()
        target_text = " ".join([
            str(target.get("title") or ""),
            str(target.get("integration_reason") or ""),
        ])
        target_families = _skill_families_for_text(domain, target_text)
        investigation_families = _skill_families_for_text(domain, integration_text)
        matching_families = sorted(target_families & investigation_families)
        domain_is_declared = any(
            re.search(rf"\b{re.escape(term)}\b", declared_disciplines)
            for term in _DOMAIN_DISCIPLINE_TERMS.get(domain, frozenset())
        )
        fits = bool(domain_is_declared and matching_families)
        if fits:
            target["integration_status"] = "INTEGRATED"
            target["integration_reason"] = (
                f"The investigation genuinely uses this target through {', '.join(item.replace('_', ' ') for item in matching_families)}."
            )
            target["contribution_prompt"] = (
                f"At working level {target.get('working_level') or 'current'}, use “{target.get('title') or f'this {domain} target'}” "
                f"where the shared evidence or outcome actually calls for {domain}; preserve the work so understanding can be reviewed."
            )
            integrated.append(target)
        else:
            target["integration_status"] = "SEPARATE"
            target["integration_reason"] = (
                "The authored investigation does not justify this connection, so it remains in the learner's separate skill path."
            )
            separate.append(target)
    return integrated, separate


def learner_contribution_for_request(contract: dict, adaptation: Any, request: LessonRequest) -> dict:
    """Join the shared theme to this learner's real, current skill path."""
    contribution = learner_contribution(contract, adaptation)
    progression_targets = list(request.learner_progression_targets or request.individual_skill_targets)
    integrated, separate = skill_connections_for_contract(
        contract, progression_targets,
    )
    contribution["delivery_mode"] = request.delivery_mode
    contribution["shared_investigation_id"] = request.shared_investigation_id
    contribution["skill_connections"] = integrated
    contribution["separate_skill_targets"] = separate
    contribution["integration_rule"] = (
        "Use a learner progression target inside this investigation only when the sources, quantities, "
        "communication, making, or real outcome genuinely require it. Otherwise preserve it as brief individual practice; "
        "never manufacture themed busywork."
    )
    return contribution


async def _run_with_progress(
    operation: Awaitable[Any],
    messages: Sequence[str],
    *,
    interval_seconds: float | None = None,
) -> AsyncIterator[tuple[str, Any]]:
    """Keep an SSE request active while one durable generation step runs.

    The operation remains a single high-effort model call. Progress frames make
    that work visible and prevent proxies from treating a quiet connection as
    abandoned; the final tuple carries the exact completed result.
    """
    interval = interval_seconds or PROGRESS_INTERVAL_SECONDS
    task = asyncio.ensure_future(operation)
    index = 0
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval)
            if task in done:
                yield "result", task.result()
                return
            message = messages[index % len(messages)] if messages else "Adeline is still preparing the experience…"
            index += 1
            yield "status", message
    except BaseException:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        raise


async def _author(
    request: LessonRequest,
    resources: list[dict],
    *,
    authoring_brief: str = "",
) -> dict:
    import openai
    key = GEMINI_API_KEY or GOOGLE_API_KEY
    if not key:
        raise HTTPException(status_code=503, detail="The Canonical Experience Author is not configured.")
    if request.track.value in {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"} and not has_verified_history_source(resources):
        raise HTTPException(
            status_code=503,
            detail="Adeline could not verify an item-level primary source for this evidence-led investigation yet.",
        )
    # Disable SDK-level hidden retries. The explicit loop below records and
    # repairs each attempt, so a provider retry can never silently double the
    # longest step.
    client = openai.AsyncOpenAI(api_key=key, base_url=GEMINI_BASE_URL, max_retries=0)
    if not authoring_brief:
        # A foreground recovery for an approved catalog item must retain the
        # same educational premise as background authoring. Custom topics have
        # no catalog brief and continue through the general author contract.
        from app.jobs.canonical_seeding import canonical_seed_for

        seed = canonical_seed_for(request.topic, request.track.value)
        authoring_brief = seed.authoring_brief if seed else ""
    brief_section = (
        "\n\nAPPROVED INVESTIGATION DESIGN BRIEF — PRESERVE THIS PREMISE:\n"
        f"{authoring_brief.strip()}"
        if authoring_brief.strip() else ""
    )
    prompt = (
        f"Author the canonical shared family experience. Topic: {request.topic}. Track: {request.track.value}. "
        "This is the actual lesson, not an outline, article, sequence of narrative boxes, worksheet, or sketchnote. "
        "Use the routed resources only when useful and obey their use_mode and license. "
        "Return the exact JSON contract. Every block must directly declare experience_stage."
        f"{brief_section}\n\n"
        f"ROUTED OUTSIDE TOOLS AND SOURCES:\n{json.dumps(resources[:6], ensure_ascii=False)}"
    )
    last_error = None
    repair_instruction = ""
    for attempt in range(2):
        started = time.perf_counter()
        try:
            attempt_prompt = prompt
            if repair_instruction:
                attempt_prompt += (
                    "\n\nREPAIR THE PRIOR DRAFT:\n"
                    + repair_instruction
                    + "\nReturn the complete corrected JSON object, not a patch or explanation."
                )
            response = await client.chat.completions.create(
                model=GEMINI_MODEL,
                # Canonical experiences contain several substantive blocks and
                # their contracts. 8k tokens could cut otherwise valid JSON in
                # the middle of an object, leaving every retry unparsable.
                max_tokens=16000,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT}, {"role": "user", "content": attempt_prompt}],
            )
            raw = response.choices[0].message.content or ""
            elapsed = time.perf_counter() - started
            choice = response.choices[0]
            usage = getattr(response, "usage", None)
            logger.info(
                "[ExperienceAuthor] model complete topic=%r attempt=%d elapsed=%.2fs "
                "chars=%d finish_reason=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                request.topic,
                attempt + 1,
                elapsed,
                len(raw),
                getattr(choice, "finish_reason", None),
                getattr(usage, "prompt_tokens", None),
                getattr(usage, "completion_tokens", None),
                getattr(usage, "total_tokens", None),
            )
            parsed = enforce_non_exposure_mastery(_json_object(raw))
            contract_errors = (
                validate_canonical_contract(parsed)
                + validate_flow_composition(parsed)
                + validate_experience_substance(parsed)
            )
            if contract_errors:
                logger.warning(
                    "[ExperienceAuthor] contract repair topic=%r attempt=%d errors=%s",
                    request.topic,
                    attempt + 1,
                    contract_errors,
                )
                last_error = ValueError("; ".join(contract_errors))
                repair_instruction = "The draft failed these semantic requirements: " + "; ".join(contract_errors)
                continue
            blocks = finalize_family_lesson(parsed.get("blocks") or [], request.topic, track=request.track.value)
            if blocks:
                parsed["blocks"] = blocks
                # finalize_family_lesson can drop blocks (dedup, obsolete formats,
                # unusable content) after flow composition was already validated
                # against the raw model output — re-check the flow still resolves
                # against what actually survived finalization.
                post_finalize_errors = validate_flow_composition(parsed)
                if post_finalize_errors:
                    logger.warning(
                        "[ExperienceAuthor] flow broke during finalization topic=%r attempt=%d errors=%s",
                        request.topic, attempt + 1, post_finalize_errors,
                    )
                    last_error = ValueError("; ".join(post_finalize_errors))
                    repair_instruction = (
                        "Finalization removed content your flow still references: "
                        + "; ".join(post_finalize_errors)
                        + ". Keep every block used and referenced consistently."
                    )
                    continue
                parsed["contract_version"] = CONTRACT_VERSION
                parsed["prompt_version"] = PROMPT_VERSION
                logger.info(
                    "[ExperienceAuthor] accepted topic=%r attempt=%d blocks=%d elapsed=%.2fs",
                    request.topic,
                    attempt + 1,
                    len(blocks),
                    elapsed,
                )
                return parsed
            last_error = ValueError("author output failed semantic experience validation")
            repair_instruction = (
                "The blocks failed the experience contract. Provide 6–8 concise substantive blocks "
                "with explicit stages, including a meaningful invitation, action or creation, and a "
                "reviewable demonstration. Do not add filler."
            )
        except Exception as exc:
            logger.warning(
                "[ExperienceAuthor] attempt failed topic=%r attempt=%d elapsed=%.2fs error=%s",
                request.topic,
                attempt + 1,
                time.perf_counter() - started,
                type(exc).__name__,
            )
            last_error = exc
            repair_instruction = (
                f"The prior response could not be accepted ({type(exc).__name__}). Keep the complete "
                "response concise and ensure it is one syntactically valid JSON object matching every field."
            )
            if attempt == 0:
                await asyncio.sleep(1)
    logger.error("[ExperienceAuthor] failed topic=%r: %s", request.topic, last_error)
    raise HTTPException(status_code=503, detail="Adeline could not author a valid experience yet. Nothing generic was substituted.")


async def _stream(request: LessonRequest):
    stream_started = time.perf_counter()
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
        for attempt in range(240):
            await asyncio.sleep(0.25)
            if attempt and attempt % 40 == 0:
                yield _sse({"type": "status", "message": "The shared experience is still being prepared safely…"})
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
        lookup_started = time.perf_counter()
        canonical, adaptation = await asyncio.gather(
            canonical_store.get(slug),
            adaptation_for(request.student_id, request.grade_level, request.track.value),
        )
        packet = planned_resource_packet(request)
        logger.info(
            "[ExperienceAuthor] context ready topic=%r canonical_hit=%s resources=%d elapsed=%.2fs",
            request.topic,
            bool(canonical),
            len(packet.get("resources") or []),
            time.perf_counter() - lookup_started,
        )
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
            routed_packet = await resource_router.search(canonical_resource_query(request))
            packet = merge_resource_packets(packet, routed_packet)
            authored = None
            async for kind, value in _run_with_progress(
                _author(request, packet["resources"]), AUTHOR_PROGRESS_MESSAGES,
            ):
                if kind == "status":
                    yield _sse({"type": "status", "message": value})
                else:
                    authored = value
            if authored is None:
                raise RuntimeError("Canonical author completed without a result")
            blocks = authored["blocks"]
            # Durable contracts live with the canonical blocks so the current DB schema
            # can preserve one source of truth without introducing a parallel lesson table.
            blocks[0].setdefault("metadata", {})["canonical_contract"] = {
                key: authored.get(key) for key in ("big_question", "learning_goal", "shared_experience", "experience_design", "investigation_scope_contract", "public_interest_contract", "real_world_task", "portfolio_task", "printable_contract", "demonstration_contract", "mastery_evidence_map", "family_roles", "contract_version", "prompt_version")
            }
            canonical = {"id": str(uuid.uuid4()), "topic": request.topic, "track": request.track.value, "title": authored.get("title") or request.topic, "blocks": blocks, "oas_standards": [], "researcher_activated": False, "agent_name": "Canonical Experience Author"}
            await canonical_store.save(slug, canonical, pending=False)
        yield _sse({"type": "status", "message": "The shared experience is ready. Preparing this learner's entry point…"})
        blocks = None
        async for kind, value in _run_with_progress(
            adapt_canonical_for_student(
                {"topic": request.topic, "blocks": canonical.get("blocks") or []}, adaptation,
            ),
            ADAPTER_PROGRESS_MESSAGES,
        ):
            if kind == "status":
                yield _sse({"type": "status", "message": value})
            else:
                blocks = value
        if blocks is None:
            raise RuntimeError("Learner adaptation completed without a result")
        bridge = sequence_bridge_block(request)
        if bridge:
            blocks.insert(0, bridge)
        resource_block = resource_block_from_packet(packet)
        if resource_block:
            blocks.append(resource_block)
        experience_id = claim.record["id"]
        for index, block in enumerate(blocks):
            block.setdefault("block_id", f"{experience_id}-{index}")
        contract = ((canonical.get("blocks") or [{}])[0].get("metadata") or {}).get("canonical_contract") or {}
        learner_contribution_data = learner_contribution_for_request(contract, adaptation, request)
        integrated_targets = list(learner_contribution_data.get("skill_connections") or [])
        metadata = {
            "canonical_slug": slug, "topic": request.topic, "grade_level": request.grade_level,
            "required_standard_codes": request.required_standard_codes,
            "investigation_scope_contract": contract.get("investigation_scope_contract") or {},
            "demonstration_contract": contract.get("demonstration_contract") or {},
            "experience_design": contract.get("experience_design") or {},
            "public_interest_contract": contract.get("public_interest_contract") or {},
            "mastery_evidence_map": contract.get("mastery_evidence_map") or [],
            "contract_version": contract.get("contract_version"),
            "prompt_version": contract.get("prompt_version"),
            "concept_id": request.concept_id,
            "concept_name": request.concept_name or request.topic,
            "sequence_target_id": request.sequence_target_id,
            "sequence_policy": request.sequence_policy,
            "sequence_state": request.sequence_state,
            "prerequisite_concept_ids": request.prerequisite_concept_ids,
            "prerequisite_standard_ids": request.prerequisite_standard_ids,
            "bridge_required": request.bridge_required,
            "learner_contribution": learner_contribution_data,
            "integrated_standard_codes": list(dict.fromkeys(
                str(target.get("standard_code"))
                for target in integrated_targets
                if target.get("standard_code")
            )),
            "integrated_concept_ids": list(dict.fromkeys(
                str(target.get("concept_id"))
                for target in integrated_targets
                if target.get("concept_id")
            )),
            "portfolio_task": contract.get("portfolio_task") or {},
            "delivery_mode": request.delivery_mode,
            "shared_investigation_id": request.shared_investigation_id,
            "individual_skill_targets": request.individual_skill_targets,
            "learner_progression_targets": request.learner_progression_targets,
        }
        record = await student_experience_store.save_ready(
            request.student_id, plan_item_id, title=canonical.get("title") or request.topic,
            track=request.track.value, blocks=blocks, metadata=metadata,
        )
        logger.info(
            "[ExperienceAuthor] learner experience ready student=%s item=%s blocks=%d total_elapsed=%.2fs",
            request.student_id,
            plan_item_id,
            len(blocks),
            time.perf_counter() - stream_started,
        )
        async for event in _emit_persisted(request, record):
            yield event
    except asyncio.CancelledError:
        # A browser navigation or dropped connection must not strand the durable
        # item in `generating` until the stale-claim timeout expires.
        await student_experience_store.mark_failed(
            request.student_id, plan_item_id, "Generation connection closed before completion"
        )
        raise
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
    codes = list(dict.fromkeys([
        *(metadata.get("required_standard_codes") or request.required_standard_codes),
        *(metadata.get("integrated_standard_codes") or []),
    ]))
    standards = [{"standard_id": code, "text": "Internal learning-plan target", "grade": 0, "source_type": "required_plan"} for code in codes]
    title = record.get("title") or request.topic
    yield _sse({"type": "done", "lesson_id": lesson_id, "title": title,
                "agent_name": "Canonical Experience Author", "oas_standards": standards,
                # Experience construction never awards seat-time credit. The
                # journal/standards path evaluates the learner's demonstration.
                "credits_awarded": [], "researcher_activated": False,
                "metadata": metadata})


@router.post("/build")
async def build_experience(request: LessonRequest, authorization: str | None = Header(default=None)):
    await verify_student_access(request.student_id, authorization)
    if request.sequence_policy == "HARD" and request.sequence_state != "READY":
        raise HTTPException(
            status_code=409,
            detail="This planned skill is still locked by an unmastered prerequisite. Open the prerequisite mission first.",
        )
    await enforce_rate_limit("experience-build", request.student_id, limit=8)
    return StreamingResponse(_stream(request), media_type="text/event-stream")


@router.get("/{student_id}/{plan_item_id}")
async def read_experience(
    student_id: str,
    plan_item_id: str,
    response: Response,
    authorization: str | None = Header(default=None),
):
    """Return the durable learner experience without entering the author path."""
    await verify_student_access(student_id, authorization)
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    record = await student_experience_store.get(student_id, plan_item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experience has not been created")
    return record


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
    bridge = sequence_bridge_block(request)
    if bridge:
        blocks.insert(0, bridge)
    contract = ((canonical.get("blocks") or [{}])[0].get("metadata") or {}).get("canonical_contract") or {}
    if blocks:
        blocks[0].setdefault("metadata", {})["learner_contribution"] = learner_contribution_for_request(
            contract, adaptation, request
        )
    from app.services.investigation_printable import build_investigation_pdf
    pdf = build_investigation_pdf(title=canonical.get("title") or request.topic, topic=request.topic,
                                  grade_level=request.grade_level, blocks=blocks)
    filename = re.sub(r"[^a-z0-9]+", "-", (canonical.get("title") or request.topic).lower()).strip("-") or "investigation"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}-field-dossier.pdf"'})
