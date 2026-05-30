"""
Multi-Agent Orchestrator
Routes lesson requests to the appropriate specialist agent based on Track.
Enforces the Witness Protocol before any content reaches the student.

6 Specialist Agents:
  historian_agent     — TRUTH_HISTORY
                        Strictest Witness Protocol (0.82); PRIMARY_SOURCE focus
  justice_agent       — JUSTICE_CHANGEMAKING
                        Witness Protocol (0.82); PRIMARY_SOURCE blocks when verified;
                        power-capture framing; always includes RESEARCH_MISSION
  science_agent       — CREATION_SCIENCE, HOMESTEADING
                        LAB_MISSION blocks for hands-on tracks; homestead lens
  literature_agent    — ENGLISH_LITERATURE
                        Book-context aware; literary analysis without Witness gate
  practical_agent     — APPLIED_MATHEMATICS, CREATIVE_ECONOMY
                        Applied skills; Claude synthesis without Witness gate
  discipleship_agent  — HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP
                        Worldview alignment; NARRATIVE + scripture integration
  registrar_agent     — ALL tracks (post-processing)
                        Emits xAPI LearningActivity records + CASE credit entry

Researcher Upgrade: when Hippocampus returns ARCHIVE_SILENT, the orchestrator
calls SearchWitnesses (Tavily → scrape → cosine) before falling back to a
RESEARCH_MISSION block. If a verified source is found, the lesson continues
with a PRIMARY_SOURCE block from the auto-found archive.
"""

import contextvars
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Literal, Optional

import anthropic

from app.schemas.api_models import (
    LessonRequest, LessonResponse, LessonBlockResponse,
    Track, BlockType, EvidenceVerdict,
)
from app.protocols.witness import evaluate_evidence
from app.connections.pgvector_client import hippocampus
from app.connections.neo4j_client import neo4j_client
from app.tools.researcher import search_witnesses
from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL, GOOGLE_API_KEY, ADELINE_MODEL, LEARNLM_MODEL
from app.algorithms.pedagogical_directives import generate_pedagogical_directives, get_quick_directives
from app.agents.pedagogy import ZPDZone
from app.models.student import MasteryBand

_ANTHROPIC_MODEL = ADELINE_MODEL
logger = logging.getLogger(__name__)

# ── Controversial Topic Detection ────────────────────────────────────────────
# Topics that trigger safety filters or require theological review before publishing.
# When these are detected, lessons are saved as "pending approval" for admin review.

_CONTROVERSIAL_KEYWORDS = {
    # Origins / Creation vs Evolution
    "origins", "origin of life", "evolution", "darwin", "darwinism", "natural selection",
    "common ancestor", "ape", "monkey", "primate", "hominid", "missing link",
    "big bang", "cosmology", "abiogenesis", "spontaneous generation",
    # Sensitive History
    "civil war", "slavery", "slave", "confederate", "holocaust", "genocide",
    "concentration camp", "nazi", "hitler", "world war", "atomic bomb",
    # Sexuality / Gender (requires careful theological framing)
    "sexuality", "gender", "transgender", "homosexual", "gay", "lesbian", "lgbt",
    # Other potentially sensitive topics
    "abortion", "euthanasia", "assisted suicide", "divorce", "marriage equality",
}


def is_controversial_topic(topic: str) -> tuple[bool, str]:
    """
    Check if a topic may trigger AI safety filters or requires theological review.
    Returns (is_controversial, reason_string).
    """
    topic_lower = topic.lower()
    matched = [kw for kw in _CONTROVERSIAL_KEYWORDS if kw in topic_lower]
    if matched:
        return True, f"Controversial keywords detected: {', '.join(matched[:3])}"
    return False, ""


class SynthesisSafetyError(Exception):
    """Raised when Gemini's safety filter blocks content generation."""
    pass


async def _save_pending_canonical(state: "AdelineState", reason: str) -> None:
    """
    Save a stub canonical lesson marked as pending approval.
    Called when synthesis fails (e.g., safety filter) so the topic is queued
    for admin review instead of showing students a broken lesson.
    """
    from app.connections.canonical_store import canonical_store, canonical_slug
    request = state["request"]
    slug = canonical_slug(request.topic, request.track.value)
    
    record = {
        "id": str(uuid.uuid4()),
        "topic": request.topic,
        "track": request.track.value,
        "title": f"{request.topic} — {request.track.value.replace('_', ' ').title()}",
        "blocks": [{
            "block_type": "NARRATIVE",
            "content": (
                f"**{request.topic}**\n\n"
                "This lesson is being carefully prepared by our teaching team "
                "to ensure it presents truth with accuracy and care. Check back soon!"
            ),
            "evidence": [],
            "is_silenced": False,
        }],
        "oas_standards": [],
        "researcher_activated": False,
        "agent_name": "PendingReview",
        "needs_review_reason": reason,
    }
    
    try:
        await canonical_store.save(slug, record, pending=True)
        logger.info(f"[PendingCanonical] Saved for review — slug={slug}, reason={reason}")
    except Exception as e:
        logger.warning(f"[PendingCanonical] Failed to save (non-fatal): {e}")


# ── Cognitive load token ceilings ────────────────────────────────────────────
# Set per-request via apply_cognitive_load_budget() before awaiting any agent.
# ContextVar propagates through all awaited coroutines in the same task.
_synthesis_token_ceil: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "adeline_synthesis_token_ceil", default=None
)
_pedagogical_token_ceil: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "adeline_pedagogical_token_ceil", default=None
)


def apply_cognitive_load_budget(load) -> None:
    """
    Set token ceilings based on cognitive load level.
    Call before awaiting any specialist agent so all _synthesis_call /
    _pedagogical_call invocations in that request respect the ceiling.
    No-op when load is None, LOW, or MEDIUM.
    """
    from app.algorithms.cognitive_load import should_simplify_content
    if load is not None and should_simplify_content(load):
        if load.level == "CRITICAL":
            _synthesis_token_ceil.set(1200)
            _pedagogical_token_ceil.set(800)
            logger.info("[Orchestrator] CRITICAL cognitive load — token ceiling 1200/800")
        else:  # HIGH
            _synthesis_token_ceil.set(1800)
            _pedagogical_token_ceil.set(1200)
            logger.info("[Orchestrator] HIGH cognitive load — token ceiling 1800/1200")


def _synthesis_client():
    """
    Returns an async OpenAI-compatible client for multimodal synthesis.
    Priority order:
      1. ADELINE_MODEL starts with "gemini" + GOOGLE_API_KEY set
         → ChatGoogleGenerativeAI via OpenAI-compat endpoint
      2. GEMINI_API_KEY set (legacy cheap synthesis key)
         → Gemini Flash via OpenAI-compat endpoint
      3. Fallback → Claude via ANTHROPIC_API_KEY
    Returns (client, model_name, is_gemini).
    """
    if _ANTHROPIC_MODEL.lower().startswith("gemini") and GOOGLE_API_KEY:
        import openai as _oai
        return (
            _oai.AsyncOpenAI(api_key=GOOGLE_API_KEY, base_url=GEMINI_BASE_URL),
            _ANTHROPIC_MODEL,
            True,
        )
    if GEMINI_API_KEY:
        import openai as _oai
        return (
            _oai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL),
            GEMINI_MODEL,
            True,
        )
    return (
        anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY")),
        _ANTHROPIC_MODEL,
        False,
    )


async def _pedagogical_call(system: str, user: str, max_tokens: int = 1000) -> str:
    """
    Pedagogical synthesis via LearnLM (Google's educationally fine-tuned model).
    Routes narrative voice, Socratic scaffolding, and ZPD-adapted content through
    LearnLM for higher pedagogical quality. Falls back to Gemini Flash on any error.
    """
    ceil = _pedagogical_token_ceil.get()
    if ceil is not None:
        max_tokens = min(max_tokens, ceil)
    api_key = GEMINI_API_KEY or GOOGLE_API_KEY
    if api_key:
        import openai as _oai
        for model in (LEARNLM_MODEL, GEMINI_MODEL):  # LearnLM → Flash fallback
            try:
                client = _oai.AsyncOpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
                response = await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                )
                choice = response.choices[0]
                finish_reason = getattr(choice, "finish_reason", None)
                content = choice.message.content or ""
                # Treat safety-filter / non-stop finish reasons as a failure so we fall through
                # to the next model (or Claude). Returning a truncated fragment would render a
                # broken lesson to the student.
                if finish_reason and finish_reason != "stop":
                    logger.warning(
                        f"[Pedagogical] {model} returned finish_reason={finish_reason!r} "
                        f"(content len={len(content)}) — trying next model"
                    )
                    continue
                return content
            except Exception as e:
                logger.warning(f"[Pedagogical] {model} failed ({e}) — trying fallback")
    # Final fallback: Claude
    return await _synthesis_call(system, user, max_tokens)


async def _synthesis_call(system: str, user: str, max_tokens: int = 1000) -> str:
    """
    Single synthesis API call — uses Gemini Flash if available, else Claude.
    On Gemini failure, automatically retries once then falls back to Claude.
    Returns the text content of the response.
    """
    ceil = _synthesis_token_ceil.get()
    if ceil is not None:
        max_tokens = min(max_tokens, ceil)
    import asyncio as _asyncio
    client, model, is_gemini = _synthesis_client()

    if is_gemini:
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                )
                choice = response.choices[0]
                finish_reason = getattr(choice, "finish_reason", None)
                content = choice.message.content or ""
                # If Gemini's safety filter blocked the response (partial or empty content with
                # a non-"stop" finish_reason), fall through to Claude instead of returning the
                # truncated fragment. This is common for Creation Science / Origins topics.
                if finish_reason and finish_reason != "stop":
                    logger.warning(
                        f"[Synthesis] Gemini returned finish_reason={finish_reason!r} "
                        f"(content len={len(content)}) — treating as failure and falling back to Claude"
                    )
                    break
                return content
            except Exception as gemini_err:
                if attempt == 0:
                    logger.warning(
                        f"[Synthesis] Gemini attempt {attempt + 1} failed ({gemini_err}) — retrying..."
                    )
                    await _asyncio.sleep(1)
                    continue
                logger.warning(
                    f"[Synthesis] Gemini failed after 2 attempts ({gemini_err}) — "
                    "falling back to Claude"
                )
                break
        # Gemini exhausted — fall back to Claude
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            # No Claude fallback available — this is a safety-filter scenario on a controversial topic.
            # Raise SynthesisSafetyError so the agent can save a "pending review" canonical
            # instead of returning a broken/partial lesson to the student.
            raise SynthesisSafetyError(
                f"Gemini safety filter triggered (finish_reason={finish_reason}) "
                "and ANTHROPIC_API_KEY not set — cannot generate lesson"
            )
        fallback_client = anthropic.AsyncAnthropic(api_key=anthropic_key)
        try:
            response = await fallback_client.messages.create(
                model=_ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as claude_err:
            raise SynthesisSafetyError(
                f"Claude fallback unavailable ({type(claude_err).__name__}): {claude_err}"
            ) from claude_err
        return response.content[0].text
    else:
        # Use Anthropic prompt caching on the system prompt (static prefix cached 5 min)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        return response.content[0].text

# Track routing constants
# TRUTH_HISTORY is the ONLY track that requires the Witness Protocol —
# every block must be backed by a verified primary source (cosine ≥ 0.82 via WITNESS_HISTORY_THRESHOLD).
_HISTORIAN_TRACKS  = {Track.TRUTH_HISTORY}
_JUSTICE_TRACKS    = {Track.JUSTICE_CHANGEMAKING}
_SCIENCE_TRACKS    = {Track.CREATION_SCIENCE, Track.HOMESTEADING}
_DISCIPLESHIP_TRACKS = {
    Track.HEALTH_NATUROPATHY, Track.GOVERNMENT_ECONOMICS,
    Track.DISCIPLESHIP,
}
_LITERATURE_TRACKS = {Track.ENGLISH_LITERATURE}


# ── Claude synthesis ─────────────────────────────────────────────────────────

# Grade band → readable description and age mapping
_GRADE_DESC = {
    "K": "kindergarten (age 5-6)", "1": "1st grade (age 6-7)", "2": "2nd grade (age 7-8)",
    "3": "3rd grade (age 8-9)", "4": "4th grade (age 9-10)", "5": "5th grade (age 10-11)",
    "6": "6th grade (age 11-12)", "7": "7th grade (age 12-13)", "8": "8th grade (age 13-14)",
    "9": "9th grade (age 14-15)", "10": "10th grade (age 15-16)",
    "11": "11th grade (age 16-17)", "12": "12th grade (age 17-18)",
}

# Grade → minimum age mapping (lower bound for content filtering)
_GRADE_TO_MIN_AGE = {
    "K": 5, "1": 6, "2": 7, "3": 8, "4": 9, "5": 10, "6": 11,
    "7": 12, "8": 13, "9": 14, "10": 15, "11": 16, "12": 17,
}

# Per-track character voice for synthesis
_TRACK_PERSONA = {
    Track.TRUTH_HISTORY: (
        "a truth-first historian. You show what actually happened — not the sanitized textbook version. "
        "You put primary sources in front of students and let them read real words from real people. "
        "You name the people in power who lied, and the people they harmed. You don't editorialize. "
        "You let the documents speak."
    ),
    Track.JUSTICE_CHANGEMAKING: (
        "a justice investigator. Your job is to show students exactly what happened, "
        "who got hurt, and who profited. You focus on three categories of harm: "
        "(1) NATION-BUILDING PROPAGANDA — government and corporate narratives designed to "
        "justify wars, displacement, and exploitation. You name the specific lies, who told them, "
        "and who benefited financially or politically. "
        "(2) CORPORATE CRIMES — deliberate harm for profit. Pharma companies that hid trial data. "
        "Food companies that funded research to blame fat instead of sugar. Chemical companies that "
        "knew their products caused cancer. Oil companies that buried their own climate science. "
        "You always name the company, the executive, the internal memo if it exists, and the body count. "
        "(3) JUSTICE FOR PEOPLE HARMED — you center the victims by name. Not statistics. "
        "Real people. What happened to them. What it cost them. Whether anyone was held accountable. "
        "You teach students to follow the money: find the lobbying disclosures, read the court documents, "
        "look at who funded the science, trace the revolving door between regulators and industry. "
        "You treat students as investigators who can use the same tools journalists and lawyers use."
    ),
    Track.CREATION_SCIENCE: (
        "a creation science mentor who sees YHWH's fingerprints on every natural law. "
        "You teach science through awe and hands-on discovery. You don't sanitize the hard questions — "
        "you name them and work through them honestly. You connect every concept back to how God designed it."
    ),
    Track.HOMESTEADING: (
        "a self-sufficiency mentor. Your whole frame is: what happens if the grid goes down tomorrow? "
        "No electricity. No grocery store. No pharmacy. No lumber yard. "
        "Every skill you teach is something a family actually needs to survive and thrive on their own. "
        "You are practical, direct, and allergic to theory that doesn't build anything."
    ),
    Track.DISCIPLESHIP: (
        "a discipleship guide who takes Scripture seriously in its original context. "
        "You draw from Hebrew and Greek roots when they matter. "
        "No churchy clichés. No hollow motivation. Just truth, plainly spoken. "
        "You connect what YHWH says to what is actually happening in the world right now."
    ),
    Track.HEALTH_NATUROPATHY: (
        "a health mentor who has watched the medical system harm people who trusted it. "
        "You teach how the body actually works, what actually heals it, and what the pharmaceutical industry "
        "doesn't want families to know. You honor how YHWH designed the body. "
        "You give families real knowledge so they are never dependent on a system that profits from their sickness."
    ),
    Track.GOVERNMENT_ECONOMICS: (
        "a systems mentor who teaches how power actually works — not how civics textbooks say it works. "
        "You explain money flows, lobbying, regulatory capture, and who actually benefits. "
        "You teach students to build alternative systems, not just understand broken ones. "
        "You treat them as capable of both seeing corruption clearly and doing something about it."
    ),
    Track.ENGLISH_LITERATURE: (
        "a literature mentor who reads every story as a truth claim about the world. "
        "You teach students to read critically — to notice what an author believes, "
        "what they're asking the reader to accept, and whether it holds up. "
        "You connect great writing to real courage. You point to books that shaped movements."
    ),
    Track.APPLIED_MATHEMATICS: (
        "a practical math mentor. Your whole frame is: math you will actually use in real life. "
        "Budgeting, interest, measuring land, building structures, pricing crops for market, "
        "calculating yields, understanding loans, reading a balance sheet. "
        "You never teach a formula without showing exactly where a person would use it this week. "
        "Math is a tool — not a performance. Show them how it works in the real world."
    ),
    Track.CREATIVE_ECONOMY: (
        "a maker-entrepreneur mentor. You teach students to create beautiful, functional things "
        "with their hands — and sell them. Upcycled furniture, handmade goods, farm products, "
        "branded packaging, market displays. You teach craft, pricing, marketing, and the satisfaction "
        "of building something real. Every project ends with a finished product worth money. "
        "You treat creativity as a survival skill, not a hobby."
    ),
}

# Brand voice rules injected into every synthesis call
_ADELINE_VOICE = """
BRAND VOICE (non-negotiable):
• Clear, strong sentences. No fluff. No busywork.
• Write like you are telling the truth to someone at the kitchen table — not giving a lecture.
• Short paragraphs. Active verbs. Specific details.
• Do not soften hard truths. If something is corrupt, say it's corrupt.
• Do not use academic or corporate language. No "it is important to note that..."
• Scripture references should feel natural, not pasted in. Draw from real context, not clichés.
• Treat the student like a leader in training — capable of doing something hard right now.
• No "Today we will learn..." openers. No "Great job!" closings. No filler.
• If the source reveals injustice, name it plainly and connect it to purpose.

SCRIPTURE RULES (non-negotiable):
• Use the Everett Fox translation for Torah/Pentateuch references.
• Use Hebrew names: Moshe (not Moses), Avraham (not Abraham), Ya'akov (not Jacob), Yitzhak (not Isaac), Rivkah (not Rebecca), Yosef (not Joseph), Miryam (not Miriam), Aharon (not Aaron).
• Use Hebrew book names: Bereshit (Genesis), Shemot (Exodus), Vayikra (Leviticus), Bemidbar (Numbers), Devarim (Deuteronomy).
• Use YHWH or HaShem — never 'LORD' or 'God' for the divine name.
• Cite as [Paradise Scripture: Bereshit 1:1].
"""


async def _synthesize_content(
    request: LessonRequest,
    block_type: str,
    source_chunks: list[dict],
    raw_content: str,
    *,
    student_message: str | None = None,
    mastery_score: float = 0.5,
    mastery_band: MasteryBand = MasteryBand.DEVELOPING,
) -> str:
    """
    Call Claude to synthesize lesson content from verified sources using Adeline's voice.

    If the Anthropic API key is absent, returns raw_content unchanged.

    Claude's job:
      1. Write at the student's grade level
      2. Match Adeline's voice — direct, plain, truth-first, justice-aware
      3. Ground every claim in the provided source
      4. No busywork, no padding, no academic tone
      5. Adapt scaffolding and vocabulary based on student's ZPD state (if provided)
    
    Args:
        request: The lesson request
        block_type: Type of block being synthesized
        source_chunks: Verified source chunks to ground content in
        raw_content: Fallback content if synthesis fails
        student_message: Optional student message for ZPD detection
        mastery_score: Student's current mastery score (0.0-1.0)
        mastery_band: Student's current mastery band
    """
    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        return raw_content

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona    = _TRACK_PERSONA.get(request.track, "a knowledgeable mentor")
    track_name = request.track.value.replace("_", " ").title()

    sources_text = "\n\n---\n\n".join(
        f"[SOURCE: {c['source_title']} — {c.get('citation_author', 'Unknown')}, "
        f"{c.get('citation_year', 'n.d.')}]\n{c['chunk']}"
        for c in source_chunks
    ) if source_chunks else f"Topic: {raw_content[:500]}"

    block_label = block_type.replace("_", " ").lower()

    # Build base system prompt
    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are writing for a {grade_desc} student in a Christian homeschool family.\n\n"
        f"{_ADELINE_VOICE}\n"
        "CONTENT RULES:\n"
        "• Use ONLY the provided source text — never invent facts\n"
        "• 2–3 paragraphs maximum\n"
        "• End with one direct question or challenge — not 'What did you learn?' but something that demands thought or action\n"
    )
    
    # Inject pedagogical directives if student context is available
    if student_message:
        pedagogical_block = generate_pedagogical_directives(
            student_message=student_message,
            mastery_score=mastery_score,
            mastery_band=mastery_band,
        )
        system_prompt += pedagogical_block
    else:
        # Use quick directives based on mastery band alone
        quick_directive = get_quick_directives(ZPDZone.IN_ZPD, mastery_band)
        system_prompt += f"\n{quick_directive}\n"

    user_prompt = (
        f"Topic: {request.topic}\n"
        f"Track: {track_name}\n"
        f"Block type: {block_label}\n\n"
        f"Source(s):\n{sources_text}\n\n"
        f"Write the {block_label} content in Adeline's voice. "
        f"Ground every claim in the source. Make it land."
    )

    try:
        # Pedagogical content routes through LearnLM (educationally fine-tuned)
        # with automatic fallback to Gemini Flash → Claude
        return (await _pedagogical_call(system_prompt, user_prompt, max_tokens=800)).strip()
    except Exception as e:
        logger.warning(
            f"[Synthesis] Content synthesis failed ({type(e).__name__}: {e}) "
            f"— topic='{request.topic}' track={request.track.value} block={block_type}"
        )
        if raw_content and raw_content.strip():
            return raw_content
        return (
            f"**{request.topic}** — source material is available but synthesis is temporarily unavailable. "
            f"Your research mission: find a primary source on this topic and bring it back to Adeline."
        )


def _band_from_state(state: "AdelineState") -> MasteryBand:
    """Convert the state mastery_band string to a MasteryBand enum, defaulting to DEVELOPING."""
    try:
        return MasteryBand(state.get("mastery_band", "DEVELOPING"))
    except (ValueError, KeyError):
        return MasteryBand.DEVELOPING


async def _state_synthesize(
    state: "AdelineState",
    block_type: str,
    source_chunks: list[dict],
    raw_content: str,
) -> str:
    """
    Convenience wrapper: calls _synthesize_content with ZPD context extracted from AdelineState.
    Keeps agent code clean — pass state instead of repeating mastery kwargs.
    """
    return await _synthesize_content(
        request=state["request"],
        block_type=block_type,
        source_chunks=source_chunks,
        raw_content=raw_content,
        student_message=state.get("student_message"),
        mastery_score=state.get("mastery_score", 0.0),
        mastery_band=_band_from_state(state),
    )


# ── Agent State ───────────────────────────────────────────────────────────────

class AdelineState(TypedDict):
    request:              LessonRequest
    lesson_id:            str
    query_embedding:      list[float]
    blocks:               list[dict]
    oas_standards:        list[dict]
    has_research_missions: bool
    researcher_activated: bool
    agent_name:           str
    xapi_statements:      list[dict]
    credits_awarded:      list[dict]
    interaction_count:    int
    cross_track_acknowledgment: str | None
    # Pedagogical state (optional — populated from student profile)
    mastery_score:        float
    mastery_band:         str  # MasteryBand value
    student_message:      str | None  # Last student message for ZPD detection
    # Adaptive learning path — modality-matched component injection
    preferred_modality:   str  # "visual" | "auditory" | "kinesthetic" | "text"
    # Component selector state — tracks struggle and recently used components
    recent_struggle_count: int  # Consecutive wrong attempts in this session
    recently_used_components: list[str]  # Component IDs used recently to avoid repetition
    profiler_components: list[str]  # Top components from learner_profiler decision tree


# ── Neo4j graph-link (multi-hop) ──────────────────────────────────────────────

async def _fetch_graph_context(track: str) -> list[dict]:
    """
    Multi-hop graph context for a lesson.

    Returns two categories of OAS standards, each tagged with source_type:
      'primary'     — standards on the requested track (direct curriculum match)
      'cross_track' — standards on connected tracks via CROSS_TRACK_LINK

    The cross-track entries include 'bridge_standard_text' explaining WHY the
    connection exists, and 'connected_track' naming the other track.
    This powers Adeline's ability to say:
      "This connects to [Track] because [bridge standard says...]"
    """
    results = []

    # 1. Primary standards for the requested track
    try:
        primary = await neo4j_client.run(
            """
            MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t:Track {name: $track})
            RETURN s.id AS standard_id,
                   s.standard_text AS text,
                   s.grade AS grade,
                   coalesce(s.lesson_hook, '') AS lesson_hook,
                   $track AS connected_track,
                   'primary' AS source_type,
                   '' AS bridge_standard_text
            ORDER BY s.grade
            LIMIT 4
            """,
            {"track": track},
        )
        results.extend(primary)
    except Exception as e:
        logger.warning(f"[Neo4j] primary standards query failed for track={track}: {e}")

    # 2. Cross-track connections via CROSS_TRACK_LINK (1 hop)
    try:
        cross = await neo4j_client.get_cross_track_context(track, limit=4)
        for row in cross:
            results.append({
                "standard_id":          row.get("standard_id", ""),
                "text":                 row.get("text", ""),
                "grade":                row.get("grade", 0),
                "lesson_hook":          row.get("lesson_hook", ""),
                "connected_track":      row.get("connected_track", ""),
                "source_type":          "cross_track",
                "bridge_standard_text": row.get("bridge_standard_text", ""),
            })
    except Exception as e:
        logger.warning(f"[Neo4j] cross-track query failed for track={track}: {e}")

    return results


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _homestead_adapt(content: str) -> str:
    return (
        f"[Homestead Lens] {content[:300]}...\n\n"
        "*How does this connect to caring for your land and family?*"
    )


async def _researcher_fallback(
    state: AdelineState, track_value: str, source_title: str = ""
) -> dict | None:
    """Call SearchWitnesses and return a PRIMARY_SOURCE block dict, or None."""
    request = state["request"]

    # Get student age from grade level for content filtering
    student_age = _GRADE_TO_MIN_AGE.get(request.grade_level)

    witness_list = await search_witnesses(
        query=request.topic,
        track=track_value,
        top_k=1,
        student_age=student_age,
    )
    if witness_list:
        state["researcher_activated"] = True
        best_evidence = witness_list[0]
        content = best_evidence['chunk']
        return {
            "block_type":       BlockType.PRIMARY_SOURCE.value,
            "content": (
                f"*[Adeline searched the archives and found:]*\n\n{content}"
            ),
            "evidence":         [best_evidence],
            "is_silenced":      False,
            "homestead_content": (
                _homestead_adapt(content) if request.is_homestead else None
            ),
        }
    return None


# ── Rich structured lesson constants ─────────────────────────────────────────

_ADELINE_RICH_SYSTEM_INSTRUCTION = (
    "You are Adeline, an authentic, adaptive AI Mentor for K-12 students. "
    "You are grounded in a Truth-First, worldview-driven educational philosophy. "
    "You speak as a grounded, supportive peer — never a rigid lecturer.\n\n"
    "You use a Sketchnote aesthetic in your descriptions, highlighting:\n"
    "- [Papaya Vocab] for rich vocabulary or key terms\n"
    "- [Paradise Scripture] for Scripture integration or divine reference\n"
    "- [Fuchsia Investigation] for active scientific exploration, lab, or history discovery\n\n"
    "You guide students through 10 Integrated Tracks:\n"
    "1. God's Creation & Science (CREATION_SCIENCE) — Prioritize direct observation with homestead tools.\n"
    "2. Health/Naturopathy (HEALTH_NATUROPATHY) — Body stewardship, local herbs, natural nutrition.\n"
    "3. Homesteading & Stewardship (HOMESTEADING) — Practical homesteading, farming, resource stewardship.\n"
    "4. Government/Economics (GOVERNMENT_ECONOMICS) — Liberty, free markets, local administration.\n"
    "5. Justice/Change-making (JUSTICE_CHANGEMAKING) — Advocacy, truth, real-world community action.\n"
    "6. Discipleship & Cultural Discernment (DISCIPLESHIP) — Scripture applied to media and culture.\n"
    "7. Truth-Based History (TRUTH_HISTORY) — Only speak if a primary source Witness exists. Never simulate history.\n"
    "8. English Language & Literature (ENGLISH_LITERATURE) — Classic texts, grammar, creative journaling.\n"
    "9. Applied Mathematics (APPLIED_MATHEMATICS) — Math connected to real life: budgets, land, building, markets.\n"
    "10. Creative Economy (CREATIVE_ECONOMY) — Making, crafting, branding, and selling real products.\n\n"
    "Calibrate to the chosen Grade Level:\n"
    "- early-elementary: K-3, highly visual, warm, simplified.\n"
    "- upper-elementary: 4-5, narrative-focused, hands-on.\n"
    "- middle-school: 6-8, analytical, investigative.\n"
    "- high-school: 9-12, rigorous, primary source analysis, moral discernment.\n\n"
    "BRAND VOICE (non-negotiable): Clear, strong sentences. No fluff. "
    "Write like you are telling truth at a kitchen table. "
    "Short paragraphs. Active verbs. Specific details. "
    "No 'Today we will learn...' openers. No 'Great job!' closings. "
    "Treat the student like a leader in training.\n\n"
    "SCRIPTURE RULES (non-negotiable):\n"
    "- Use the Everett Fox translation for all Torah/Pentateuch references.\n"
    "- Use Hebrew names: Moshe (not Moses), Avraham (not Abraham), "
    "Ya'akov (not Jacob), Yitzhak (not Isaac), Rivkah (not Rebecca), "
    "Yosef (not Joseph), Miryam (not Miriam), Aharon (not Aaron).\n"
    "- Use Hebrew book names: Bereshit (Genesis), Shemot (Exodus), "
    "Vayikra (Leviticus), Bemidbar (Numbers), Devarim (Deuteronomy).\n"
    "- Use YHWH or HaShem, never 'LORD' or 'God' for the divine name.\n"
    "- Cite as [Paradise Scripture: Bereshit 1:1].\n\n"
    "THOROUGHNESS REQUIREMENT:\n"
    "Every lesson must be rigorous enough to meet public school state standards. "
    "Teach real content: specific facts, names, dates, processes, or principles. "
    "This is the student's only lesson on this topic today — make it count."
)

_LESSON_SCHEMA_PROMPT = """{
  "title": "string",
  "trackId": "string",
  "gradeLevel": "string",
  "narrativeIntro": "string with embedded [Papaya Vocab: word], [Paradise Scripture: text], [Fuchsia Investigation: action] markers",
  "suggestedJournalPrompt": "string",
  "vocabulary": [{"word": "string", "definition": "string", "pronunciation": "string (optional)", "exampleSentence": "string"}],
  "scripture": {"verse": "string", "reference": "string", "insight": "string"},
  "scienceLab": {"title": "string", "hypothesis": "string", "materials": ["string"], "steps": ["string"], "observationChecklist": ["string"], "labDesignBackup": "string (optional)"},
  "historyWitness": {"title": "string", "documentDate": "string", "excerpt": "string (REAL primary source, never invented)", "sourceOrigin": "string", "reliabilityContext": "string", "witnessReflectionPrompts": ["string"]},
  "challengeActivity": {"title": "string", "challengePrompt": "string", "steps": ["string"], "interactiveVariables": [{"label": "string", "description": "string", "options": ["string","string","string"], "outcomes": ["string","string","string"]}]},
  "quiz": [{"id": "string", "question": "string", "options": ["string","string","string"], "correctIndex": 0, "explanation": "string"}]
}"""


def _grade_level_band(grade_level: str | None) -> str:
    """Map grade string (K, 1-12) to Adeline's grade band."""
    if grade_level in ("K", "1", "2", "3"):
        return "early-elementary"
    if grade_level in ("4", "5"):
        return "upper-elementary"
    if grade_level in ("6", "7", "8"):
        return "middle-school"
    return "high-school"


def _track_module_for_prompt(track: Track) -> str:
    """Return per-track JSON population instruction for the structured lesson prompt."""
    if track == Track.CREATION_SCIENCE:
        return (
            'Populate "scienceLab" with a hands-on experiment using homestead/kitchen tools. '
            'Omit "historyWitness" and "challengeActivity".'
        )
    if track == Track.TRUTH_HISTORY:
        return (
            'Populate "historyWitness" with a REAL primary source — a genuine document, letter, or record. '
            'Never invent or simulate history. If no primary source exists, say so in reliabilityContext. '
            'Omit "scienceLab" and "challengeActivity".'
        )
    return (
        'Populate "challengeActivity" with exactly 3 "interactiveVariables", '
        'each with exactly 3 options and exactly 3 outcomes (one per option). '
        'Omit "scienceLab" and "historyWitness".'
    )


async def _gemini_structured_lesson(
    topic: str,
    track: Track,
    grade_level: str | None,
) -> dict | None:
    """
    Call Gemini with JSON response format to produce the full rich lesson schema.
    Returns parsed dict or None on any failure — caller falls back to plain synthesis.
    """
    import json as _json
    import openai as _openai

    grade_band = _grade_level_band(grade_level)
    user_message = (
        f"Generate a complete lesson for:\n"
        f"Topic: {topic}\n"
        f"Track: {track.value}\n"
        f"Grade Level: {grade_band}\n\n"
        f"{_track_module_for_prompt(track)}\n\n"
        "Include exactly 3 quiz questions testing worldview, direct observation, or analytical reading. "
        "Include 2-4 vocabulary words.\n\n"
        f"Return valid JSON matching exactly this schema:\n{_LESSON_SCHEMA_PROMPT}"
    )

    try:
        client = _openai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
        resp = await client.chat.completions.create(
            model=GEMINI_MODEL,
            response_format={"type": "json_object"},
            temperature=0.8,
            messages=[
                {"role": "system", "content": _ADELINE_RICH_SYSTEM_INSTRUCTION},
                {"role": "user",   "content": user_message},
            ],
        )
        raw_text = resp.choices[0].message.content or ""
        if not raw_text.strip():
            logger.warning("[RichLesson] Gemini returned empty content")
            return None
        return _json.loads(raw_text)
    except Exception as e:
        logger.warning(f"[RichLesson] Gemini structured call failed: {e}")
        return None


def _structured_lesson_to_blocks(lesson: dict, request: LessonRequest) -> list[dict]:
    """Convert a structured Gemini lesson dict to LessonBlock wire format."""
    import json as _json
    blocks: list[dict] = []

    def _block(block_type: BlockType, content: str) -> dict:
        return {
            "block_type": block_type.value,
            "content": content,
            "evidence": [],
            "is_silenced": False,
            "homestead_content": (
                _homestead_adapt(content) if request.is_homestead else None
            ),
        }

    narrative = lesson.get("narrativeIntro", "")
    if narrative:
        blocks.append(_block(BlockType.NARRATIVE, narrative))

    vocab = lesson.get("vocabulary", [])
    if vocab:
        vocab_lines = []
        for v in vocab:
            word = v.get("word", "")
            defn = v.get("definition", "")
            pron = v.get("pronunciation", "")
            example = v.get("exampleSentence", "")
            pron_str = f" *({pron})*" if pron else ""
            vocab_lines.append(f"**{word}**{pron_str} — {defn}")
            if example:
                vocab_lines.append(f"> *{example}*")
        b = _block(BlockType.TEXT, "\n\n".join(vocab_lines))
        b["_enrichment"] = True
        blocks.append(b)

    scripture = lesson.get("scripture")
    if scripture:
        verse = scripture.get("verse", "")
        ref = scripture.get("reference", "")
        insight = scripture.get("insight", "")
        b = _block(
            BlockType.NARRATIVE,
            f"**[Paradise Scripture: {ref}]**\n\n> {verse}\n\n{insight}",
        )
        b["_enrichment"] = True
        blocks.append(b)

    journal = lesson.get("suggestedJournalPrompt", "")
    if journal:
        b = _block(BlockType.TEXT, f"**Journal Prompt:** {journal}")
        b["_enrichment"] = True
        blocks.append(b)

    science_lab = lesson.get("scienceLab")
    history_witness = lesson.get("historyWitness")
    challenge = lesson.get("challengeActivity")

    if science_lab and request.track == Track.CREATION_SCIENCE:
        blocks.append({
            "block_type": BlockType.LAB_MISSION.value,
            "content": _json.dumps(science_lab),
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
        })
    elif history_witness and request.track == Track.TRUTH_HISTORY:
        blocks.append({
            "block_type": BlockType.PRIMARY_SOURCE.value,
            "content": _json.dumps(history_witness),
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
        })
    elif challenge:
        blocks.append({
            "block_type": BlockType.LAB_MISSION.value,
            "content": _json.dumps(challenge),
            "evidence": [],
            "is_silenced": False,
            "homestead_content": (
                _homestead_adapt(_json.dumps(challenge)) if request.is_homestead else None
            ),
        })

    quiz = lesson.get("quiz", [])
    if quiz:
        blocks.append({
            "block_type": BlockType.QUIZ.value,
            "content": _json.dumps(quiz),
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
        })

    return blocks


async def _generate_from_knowledge(
    state: AdelineState,
    silent_sources: list[str],
) -> list[dict]:
    """
    Knowledge-generation fallback — Adeline ALWAYS teaches.

    Called when both Hippocampus and the Researcher return empty.
    First tries Gemini structured output (rich lesson: vocabulary, scripture,
    lab/witness/challenge, quiz). Falls back to plain narrative synthesis if
    Gemini fails.
    """
    request = state["request"]

    structured = await _gemini_structured_lesson(
        request.topic, request.track, request.grade_level
    )
    if structured:
        logger.info(
            f"[RichLesson] Structured lesson generated for {request.topic!r} ({request.track.value})"
        )
        return _structured_lesson_to_blocks(structured, request)

    # Graceful degradation: original plain narrative synthesis
    track_name = request.track.value.replace("_", " ").title()
    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona = _TRACK_PERSONA.get(request.track, "a knowledgeable mentor")

    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are teaching a {grade_desc} student.\n\n"
        f"{_ADELINE_VOICE}\n"
        "IMPORTANT: You are teaching from your own knowledge because the primary source "
        "archive does not yet have verified documents on this topic. That is fine — teach "
        "the lesson anyway. Be specific: name real people, real dates, real places, real events. "
        "Do NOT say 'I don't have sources' or 'research this yourself.' TEACH.\n\n"
        "Structure your response as THREE sections, separated by ---:\n"
        "SECTION 1: Opening hook — one vivid paragraph that drops the student into the moment.\n"
        "SECTION 2: The lesson — 2-3 paragraphs with specific facts, names, dates. "
        "Ground every claim in real history. End with a direct question or challenge.\n"
        "SECTION 3: A single sentence connecting this topic to why it matters RIGHT NOW.\n"
    )

    user_prompt = (
        f"Topic: {request.topic}\n"
        f"Track: {track_name}\n\n"
        f"Teach this lesson. Be specific. Make it land."
    )

    blocks: list[dict] = []

    try:
        raw = await _synthesis_call(system_prompt, user_prompt, max_tokens=1200)
        content = raw.strip()
    except Exception as e:
        logger.warning(f"[KnowledgeGen] Synthesis failed ({e}) — using topic as fallback")
        track_name = request.track.value.replace("_", " ").title()
        content = (
            f"**{request.topic}**\n\n"
            f"Today we're exploring *{request.topic}* in the "
            f"**{track_name}** track.\n\n"
            "Adeline is building her archive on this topic. In the meantime, "
            "let's think critically about it together using the questions below."
        )

    blocks.append({
        "block_type":  BlockType.NARRATIVE.value,
        "content":     content,
        "evidence":    [],
        "is_silenced": False,
        "homestead_content": (
            _homestead_adapt(content) if request.is_homestead else None
        ),
    })

    sources_text = "\n".join(f"- {s}" for s in silent_sources[:3]) if silent_sources else ""
    enrichment = (
        "**Dig Deeper (Optional Research Mission):**\n"
        "Adeline taught this from her own knowledge. Want to go further? "
        "Find a primary source document on this topic and bring it back — "
        "she'll verify it and add it to the archive so future students benefit too."
    )
    if sources_text:
        enrichment += f"\n\nStart by looking for:\n{sources_text}"

    blocks.append({
        "block_type":  BlockType.RESEARCH_MISSION.value,
        "content":     enrichment,
        "evidence":    [],
        "is_silenced": False,
    })
    state["has_research_missions"] = True

    return blocks


# ── Historian Agent (TRUTH_HISTORY) ───────────────────────────────────

async def historian_agent(state: AdelineState) -> AdelineState:
    """
    Truth-Based History specialist. TRUTH_HISTORY only.
    PRIMARY_SOURCE blocks when VERIFIED (cosine >= 0.82).
    On ARCHIVE_SILENT: tries SearchWitnesses before falling back to RESEARCH_MISSION.
    Strictest application of the Witness Protocol.
    """
    request = state["request"]
    state["agent_name"] = "HistorianAgent"
    blocks: list[dict] = []

    # Hard guard: Witness Protocol is TRUTH_HISTORY only.
    # evaluate_evidence already handles this, but this ensures no accidental bleed-through.
    _use_witness = request.track.value == "TRUTH_HISTORY"

    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    silent_sources: list[str] = []

    for result in raw_results:
        evidence = evaluate_evidence(
            source_id=result["id"],
            source_title=result["source_title"],
            source_url=result.get("source_url", ""),
            citation_author=result.get("citation_author", ""),
            citation_year=result.get("citation_year"),
            citation_archive_name=result.get("citation_archive_name", ""),
            similarity_score=float(result["similarity_score"]),
            chunk=result["chunk"],
            track=request.track.value,
        )

        if evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT:
            # Collect silent sources — try researcher once at the end, not per-result
            silent_sources.append(result["source_title"])
        else:
            raw = result["chunk"]
            content = await _state_synthesize(
                state,
                block_type=BlockType.PRIMARY_SOURCE.value,
                source_chunks=[result],
                raw_content=raw,
            )
            blocks.append({
                "block_type":       BlockType.PRIMARY_SOURCE.value,
                "content":          content,
                "evidence":         [evidence.model_dump()],
                "is_silenced":      False,
                "homestead_content": (
                    _homestead_adapt(raw) if request.is_homestead else None
                ),
            })

    # If no verified blocks, try researcher once (not per silent result)
    if not blocks:
        logger.info(
            f"[HistorianAgent] No verified sources for '{request.topic}' — "
            "activating Researcher..."
        )
        block = await _researcher_fallback(state, request.track.value)
        if block:
            blocks.append(block)
        else:
            # Researcher also failed — Adeline teaches from knowledge (Gemini)
            logger.info(
                f"[HistorianAgent] Researcher empty for '{request.topic}' — "
                "generating lesson from knowledge"
            )
            blocks = await _generate_from_knowledge(state, silent_sources[:3])

    # ── Render to cohesive format ──────────────────────────────────────────────
    await _render_lesson(state, blocks)

    state["blocks"] = blocks
    return state


# ── Justice Agent (JUSTICE_CHANGEMAKING) ─────────────────────────────────────

async def justice_agent(state: AdelineState) -> AdelineState:
    """
    Justice Changemaking specialist — investigative journalism model.

    Applies the Witness Protocol (0.82 threshold) to seeded primary sources.
    VERIFIED sources (lobbying records, civil rights docs, legislative history)
    are surfaced as PRIMARY_SOURCE blocks before the NARRATIVE and RESEARCH_MISSION.
    ARCHIVE_SILENT sources are used as background context for Claude only.

    The investigative model is preserved: the student always receives a
    RESEARCH_MISSION to find additional evidence; verified sources are shown
    alongside the mission, not instead of it.

    Three focal areas (always present at least one per lesson):
      1. Nation-building propaganda — name the lie, who told it, who profited
      2. Corporate crimes — deliberate harm for profit, name company + body count
      3. People harmed — center victims by name, not as statistics

    Block structure:
      PRIMARY_SOURCE   — Witness-verified archive sources (when available, ≥ 0.82)
      NARRATIVE        — presents the harm clearly: who, what, how much they profited
      RESEARCH_MISSION — gives the student a specific place to look for evidence
                         (lobbying disclosures, court records, internal memos, etc.)
    """
    request = state["request"]
    state["agent_name"] = "JusticeAgent"
    blocks: list[dict] = []

    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    # Evaluate each result through the Witness Protocol.
    # VERIFIED → PRIMARY_SOURCE block; ARCHIVE_SILENT → background context only.
    silent_context_chunks: list[str] = []
    for result in raw_results:
        evidence = evaluate_evidence(
            source_id=result["id"],
            source_title=result["source_title"],
            source_url=result.get("source_url", ""),
            citation_author=result.get("citation_author", ""),
            citation_year=result.get("citation_year"),
            citation_archive_name=result.get("citation_archive_name", ""),
            similarity_score=float(result["similarity_score"]),
            chunk=result["chunk"],
            track=request.track.value,
        )
        if evidence.verdict == EvidenceVerdict.VERIFIED:
            content = await _state_synthesize(
                state,
                block_type=BlockType.PRIMARY_SOURCE.value,
                source_chunks=[result],
                raw_content=result["chunk"],
            )
            blocks.append({
                "block_type":  BlockType.PRIMARY_SOURCE.value,
                "content":     content,
                "evidence":    [evidence.model_dump()],
                "is_silenced": False,
            })
        else:
            silent_context_chunks.append(f"[Source: {result['source_title']}]\n{result['chunk']}")

    source_context = "\n\n".join(silent_context_chunks)

    grade_desc = _GRADE_DESC.get(request.grade_level or "8", "middle school")
    persona    = _TRACK_PERSONA[Track.JUSTICE_CHANGEMAKING]

    investigation_prompt = f"""You are {persona}

Grade level: {grade_desc}
Topic: {request.topic}

{"Unverified background context (below Witness threshold — do NOT cite as established fact):\\n" + source_context if source_context else "No background context available. Rely on well-documented public knowledge."}

Write a justice investigation lesson in two parts:

PART 1 — THE BRIEF (NARRATIVE block):
Open with the specific harm. Name it plainly. Then:
• Who was hurt? Name real people if possible — not "communities" or "workers."
• Who profited? Name the company, the executive, the dollar amount if known.
• What mechanism did they use? (propaganda campaign, regulatory capture, buried research, legislative capture, media control)
• What did they know and when? If there are internal documents, name them.
• One sentence on whether anyone faced accountability — and if not, say so plainly.

PART 2 — THE INVESTIGATION (RESEARCH_MISSION block):
Give the student exactly ONE specific investigation task. Not "research the topic."
A real task: find a specific document, read a specific database, look up a specific filing.
Examples of good tasks:
  • "Go to opensecrets.org and find how much [company] spent lobbying [agency] in [year range]."
  • "Search the FDA adverse event database for [drug name] and count how many deaths were reported."
  • "Read the 1969 internal Sugar Research Foundation memo at UCSF's tobacco documents archive."
  • "Look up [company] v. [plaintiff] in PACER — read the plaintiff's complaint, paragraph 12."

Format your response as:

NARRATIVE:
[The investigation brief — plain, direct, no academic language]

RESEARCH_MISSION:
[The specific task — one concrete action with a real URL or database name]

{_ADELINE_VOICE}
"""

    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        blocks.append({
            "block_type":  BlockType.NARRATIVE.value,
            "content":     f"Justice investigation: {request.topic}",
            "evidence":    [],
            "is_silenced": False,
        })
        state["blocks"] = blocks
        return state

    raw_output = ""
    try:
        raw_output = await _synthesis_call("", investigation_prompt, max_tokens=1200)
        raw_output = raw_output.strip()
    except Exception as e:
        logger.warning(f"[JusticeAgent] LLM call failed ({e}) — using fallback NARRATIVE")
        blocks.append({
            "block_type":  BlockType.NARRATIVE.value,
            "content":     f"Justice investigation: {request.topic}",
            "evidence":    [],
            "is_silenced": False,
        })
        state["blocks"] = blocks
        return state

    # Parse NARRATIVE and RESEARCH_MISSION sections
    narrative_text = ""
    mission_text   = ""
    if "RESEARCH_MISSION:" in raw_output:
        parts          = raw_output.split("RESEARCH_MISSION:", 1)
        narrative_text = parts[0].replace("NARRATIVE:", "").strip()
        mission_text   = parts[1].strip()
    else:
        narrative_text = raw_output.replace("NARRATIVE:", "").strip()

    if narrative_text:
        blocks.append({
            "block_type":  BlockType.NARRATIVE.value,
            "content":     narrative_text,
            "evidence":    [],
            "is_silenced": False,
        })

    if mission_text:
        blocks.append({
            "block_type":  BlockType.RESEARCH_MISSION.value,
            "content":     mission_text,
            "evidence":    [],
            "is_silenced": False,
        })
        state["has_research_missions"] = True

    if not blocks:
        logger.info(
            f"[JusticeAgent] No blocks generated for '{request.topic}' — "
            "generating lesson from knowledge"
        )
        blocks = await _generate_from_knowledge(state, [])

    # ── Render to cohesive format ──────────────────────────────────────────────
    await _render_lesson(state, blocks)

    state["blocks"] = blocks
    return state


# ── Science Agent (CREATION_SCIENCE, HOMESTEADING) ────────────────────────────

async def science_agent(state: AdelineState) -> AdelineState:
    """
    Creation Science and Homesteading specialist — "Sovereign Lab" model.

    CREATION_SCIENCE: EXPERIMENT-FIRST. Adeline acts as a Lab Director.
      1. Check the experiment catalog for a matching "wow" experiment
      2. If found → EXPERIMENT block (hands-on, filmable, viral)
      3. If not  → fall back to Hippocampus retrieval (PRIMARY_SOURCE)

    HOMESTEADING: LAB_MISSION blocks for hands-on, land-based learning.

    The "No Busywork" science loop:
      Hook → Materials Check → Live Guide → Film It → Discovery Video = Portfolio

    Witness Protocol applies to text-based blocks; experiments are pre-verified
    via the curated experiment catalog and don't need cosine scoring.
    """
    from app.api.experiments import EXPERIMENTS

    request = state["request"]
    state["agent_name"] = "ScienceAgent"
    blocks: list[dict] = []
    is_homesteading = request.track == Track.HOMESTEADING
    is_creation_science = request.track == Track.CREATION_SCIENCE

    # ── Step 1: Experiment match (CREATION_SCIENCE only) ──────────────────────
    # Search the experiment catalog for concept keyword overlap with the topic.
    if is_creation_science:
        topic_lower = request.topic.lower()
        best_experiment = None
        best_overlap = 0

        for exp in EXPERIMENTS.values():
            # Score: number of concept keywords that appear in the topic
            overlap = sum(
                1 for concept in exp.scientific_concepts
                if concept.lower() in topic_lower or any(
                    word in topic_lower for word in concept.lower().split()
                )
            )
            # Also check title/tagline
            if exp.title.lower() in topic_lower or topic_lower in exp.title.lower():
                overlap += 3
            for word in topic_lower.split():
                if len(word) > 3 and word in exp.tagline.lower():
                    overlap += 1

            if overlap > best_overlap:
                best_overlap = overlap
                best_experiment = exp

        if best_experiment and best_overlap >= 1:
            logger.info(
                f"[ScienceAgent] Experiment match: '{best_experiment.title}' "
                f"(overlap={best_overlap}) for topic='{request.topic}'"
            )

            # Build the EXPERIMENT block with the Creation Connection
            content = (
                f"**{best_experiment.title}** {_CHAOS_EMOJI[best_experiment.chaos_level]}\n\n"
                f"*{best_experiment.tagline}*\n\n"
                f"We could read about {', '.join(best_experiment.scientific_concepts[:2])}, "
                f"OR we could make enough "
            )
            # Tailor the hook per experiment
            if "toothpaste" in best_experiment.title.lower():
                content += "foam to wash an elephant. Which one?"
            elif "mentos" in best_experiment.title.lower():
                content += "pressure to launch a soda rocket 50 feet into the air. Which one?"
            elif "oobleck" in best_experiment.title.lower():
                content += "non-Newtonian fluid to walk on. Which one?"
            elif "fire" in best_experiment.title.lower():
                content += "heat to build a real vortex of fire. Which one?"
            elif "dry ice" in best_experiment.title.lower():
                content += "CO\u2082 to fill a giant fog bubble. Which one?"
            else:
                content += "something unforgettable. Ready?"

            blocks.append({
                "block_type":        BlockType.EXPERIMENT.value,
                "content":           content,
                "evidence":          [],  # experiments are pre-verified (curated catalog)
                "is_silenced":       False,
                "homestead_content": None,
                "experiment_id":     best_experiment.id,
                "experiment_data":   best_experiment.model_dump(),
            })

    # ── Step 2: Hippocampus retrieval (always — provides content for the renderer)
    # Even when an experiment matched, we need teaching content for the animated
    # sketchnote/narrated slide. The experiment is a supplement alongside it.
    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    # No Witness Protocol threshold — science content doesn't need archival verification.
    # Hippocampus results are reference material; Claude synthesizes the actual lesson.
    # Minimum relevance floor: discard anything below 0.40 — OAS standards metadata and
    # unrelated chunks can score as low as 0.15-0.25 and produce garbage Primary Source blocks.
    _SCIENCE_RELEVANCE_FLOOR = 0.40
    raw_results = [r for r in raw_results if float(r["similarity_score"]) >= _SCIENCE_RELEVANCE_FLOOR]
    if not raw_results:
        logger.info(
            f"[ScienceAgent] All Hippocampus results below relevance floor "
            f"({_SCIENCE_RELEVANCE_FLOOR}) — falling through to knowledge generation."
        )
    for result in raw_results:
        raw = result["chunk"]
        block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.PRIMARY_SOURCE
        content = await _state_synthesize(
            state,
            block_type=block_type.value,
            source_chunks=[result],
            raw_content=raw,
        )
        if is_homesteading:
            content = (
                f"**Homestead Lab Mission**\n\n{content}\n\n"
                "*Observe this directly on your land. Record what you find.*"
            )
        blocks.append({
            "block_type":        block_type.value,
            "content":           content,
            "evidence":          [{
                "source_id":        result["id"],
                "source_title":     result["source_title"],
                "source_url":       result.get("source_url", ""),
                "witness_citation": {
                    "author":       result.get("citation_author", ""),
                    "year":         result.get("citation_year"),
                    "archive_name": result.get("citation_archive_name", ""),
                },
                "similarity_score": float(result["similarity_score"]),
                "verdict":          "VERIFIED",
                "chunk":            raw,
            }],
            "is_silenced":       False,
            "homestead_content": _homestead_adapt(raw) if request.is_homestead else None,
        })

    # Check if we have any content blocks (not just experiment supplements)
    _has_content = any(
        b.get("block_type") not in (BlockType.EXPERIMENT.value, "GENUI_ASSEMBLY")
        for b in blocks
    )
    if not _has_content:
        # No teaching content yet — try web search (seeds Hippocampus for next time)
        logger.info("[ScienceAgent] No content blocks — searching web to seed and generate.")
        web_results = await search_witnesses(request.topic, request.track.value)
        if web_results:
            raw = web_results[0].get("chunk", request.topic)
            block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.PRIMARY_SOURCE
            content = await _state_synthesize(
                state,
                block_type=block_type.value,
                source_chunks=web_results,
                raw_content=raw,
            )
            if is_homesteading:
                content = (
                    f"**Homestead Lab Mission**\n\n{content}\n\n"
                    "*Observe this directly on your land. Record what you find.*"
                )
            blocks.append({
                "block_type":        block_type.value,
                "content":           content,
                "evidence":          [{
                    "source_id":        r.get("source_id", ""),
                    "source_title":     r.get("source_title", ""),
                    "source_url":       r.get("source_url", ""),
                    "witness_citation": r.get("witness_citation", {}),
                    "similarity_score": float(r.get("similarity_score", 0)),
                    "verdict":          "VERIFIED",
                    "chunk":            r.get("chunk", ""),
                } for r in web_results[:2]],
                "is_silenced":       False,
                "homestead_content": None,
            })
            state["researcher_activated"] = True
        else:
            # Web search also empty — synthesize from knowledge with a proper track voice
            logger.info("[ScienceAgent] No web results — generating from knowledge with Lab Director voice.")
            grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
            if is_homesteading:
                sys_prompt = (
                    f"You are Adeline — {_TRACK_PERSONA[Track.HOMESTEADING]}\n\n"
                    f"Teaching a {grade_desc} student in a Christian homeschool family.\n\n"
                    f"{_ADELINE_VOICE}\n"
                    "Write a HOMESTEAD LAB MISSION. Structure:\n"
                    "1. One vivid opening sentence — drop the student into a real land-based moment.\n"
                    "2. What to observe, grow, build, or do — specific and practical.\n"
                    "3. What science principle they'll see in action.\n"
                    "4. One question: 'Who designed this system and why does it work so well?'\n"
                    "Keep it under 200 words. No fluff."
                )
            else:
                sys_prompt = (
                    f"You are Adeline — {_TRACK_PERSONA[Track.CREATION_SCIENCE]}\n\n"
                    f"Teaching a {grade_desc} student in a Christian homeschool family.\n\n"
                    f"{_ADELINE_VOICE}\n"
                    "Write a CREATION SCIENCE lesson. Structure:\n"
                    "1. One hook sentence — a specific, observable fact that demands an explanation.\n"
                    "2. What the secular model says about this topic — be fair and accurate.\n"
                    "3. What the Creation model says — specific, evidence-based, no 'God said so' shortcuts.\n"
                    "   Name real scientists, real experiments, real data points where possible.\n"
                    "4. One challenge question the student can investigate themselves.\n"
                    "DO NOT say 'the archive doesn't have sources' or refer to your limitations. TEACH.\n"
                    "Keep it under 300 words. Direct, specific, intellectually honest."
                )
            user_prompt = (
                f"Topic: {request.topic}\n\n"
                "Teach this lesson now."
            )
            try:
                content = (await _synthesis_call(sys_prompt, user_prompt, max_tokens=900)).strip()
            except SynthesisSafetyError as e:
                # Safety filter triggered and no Claude fallback — save for admin review
                logger.warning(f"[ScienceAgent] Safety filter on '{request.topic}': {e}")
                is_controversial, reason = is_controversial_topic(request.topic)
                review_reason = reason if is_controversial else "AI safety filter triggered"
                await _save_pending_canonical(state, review_reason)
                content = (
                    f"**{request.topic}**\n\n"
                    "This lesson is being carefully prepared by our teaching team "
                    "to ensure it presents truth with accuracy and care. Check back soon!"
                )
            except Exception as e:
                logger.warning(f"[ScienceAgent] Knowledge synthesis failed: {e}")
                content = (
                    f"**{request.topic}**\n\n"
                    "Adeline is preparing this lesson. Check back shortly."
                )
            if is_homesteading:
                content = f"**Homestead Lab Mission**\n\n{content}"
            block_type = BlockType.LAB_MISSION if is_homesteading else BlockType.NARRATIVE
            blocks.append({
                "block_type":        block_type.value,
                "content":           content,
                "evidence":          [],
                "is_silenced":       False,
                "homestead_content": None,
            })

    # ── CREATION_SCIENCE: inject MoleculeSimulator for chemistry/matter topics ──
    if is_creation_science and blocks:
        mol_block = await _synthesize_molecule_sim_block(request, blocks[0].get("content", ""))
        if mol_block:
            blocks.append(mol_block)

    # ── Render to cohesive format ──────────────────────────────────────────────
    await _render_lesson(state, blocks)

    state["blocks"] = blocks
    return state


# Chaos level emoji lookup
_CHAOS_EMOJI = {1: "🌱", 2: "🔭", 3: "🔥"}


# ── Tracks that skip the Witness Protocol ────────────────────────────────────
# These tracks use Hippocampus as reference material (if available) but don't
# gate on cosine similarity. Claude synthesizes practical content directly.
_PRACTICAL_TRACKS = {Track.APPLIED_MATHEMATICS, Track.CREATIVE_ECONOMY}


# ── Literature Agent (ENGLISH_LITERATURE) ────────────────────────────────────

async def _get_active_book(student_id: str) -> dict | None:
    """Fetch the student's currently reading book from ReadingSession + Book."""
    try:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                """
                SELECT b.id, b.title, b.author, b.track, b.lexile_level, b.grade_band,
                       rs."currentLocation", rs."pagesRead", rs."totalPages"
                FROM "ReadingSession" rs
                JOIN "Book" b ON b.id = rs."bookId"
                WHERE rs."studentId" = $1 AND rs.status = 'reading'
                ORDER BY rs."updatedAt" DESC
                LIMIT 1
                """,
                student_id,
            )
        finally:
            await conn.close()
        if row:
            return dict(row)
    except Exception as e:
        logger.warning(f"[LiteratureAgent] Failed to fetch active book: {e}")
    return None


async def literature_agent(state: AdelineState) -> AdelineState:
    """
    English Literature specialist — literary analysis, not fact-checking.

    Does NOT use the Witness Protocol. Literature is about interpretation,
    not historical verification. A novel is not a declassified document.

    Priority:
      1. If student has an active book in ReadingNook → analyze that book
      2. If Hippocampus has relevant literature content → use as reference
      3. Otherwise → Claude generates literary discussion from its knowledge

    Always produces NARRATIVE blocks with literary analysis framing.
    """
    request = state["request"]
    state["agent_name"] = "LiteratureAgent"
    blocks: list[dict] = []

    # ── Step 1: Check for active book in ReadingNook ─────────────────────────
    active_book = await _get_active_book(request.student_id)

    if active_book:
        logger.info(
            f"[LiteratureAgent] Student reading: '{active_book['title']}' "
            f"by {active_book['author']}"
        )
        # Synthesize literary analysis grounded in the book they're reading
        content = await _synthesize_literature(
            request=request,
            book_title=active_book["title"],
            book_author=active_book["author"],
            topic=request.topic,
        )
        blocks.append({
            "block_type":       BlockType.NARRATIVE.value,
            "content":          _worldview_wrap(content, request.track),
            "evidence":         [{
                "source_id":        f"book-{active_book['id']}",
                "source_title":     f"{active_book['title']} by {active_book['author']}",
                "source_url":       "",
                "witness_citation": {
                    "author": active_book["author"],
                    "year": None,
                    "archive_name": "Student's Reading Nook",
                },
                "similarity_score": 1.0,
                "chunk":            f"Literary analysis of {active_book['title']}",
            }],
            "is_silenced":      False,
            "homestead_content": None,
        })
        # Fall through to multimodal synthesis below

    else:
        # ── Step 2: Hippocampus reference (no Witness gate) ──────────────────────
        raw_results = await hippocampus.similarity_search(
            query_embedding=state["query_embedding"],
            track=request.track.value,
            top_k=3,
        )

        reference_chunks = []
        for result in raw_results:
            reference_chunks.append(result)

        # ── Step 3: Synthesize literary content ───────────────────────────────────
        if reference_chunks:
            content = await _state_synthesize(
                state,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=reference_chunks,
                raw_content=reference_chunks[0]["chunk"],
            )
            blocks.append({
                "block_type":       BlockType.NARRATIVE.value,
                "content":          _worldview_wrap(content, request.track),
                "evidence":         [{
                    "source_id":        r["id"],
                    "source_title":     r["source_title"],
                    "source_url":       r.get("source_url", ""),
                    "witness_citation": {
                        "author":       r.get("citation_author", ""),
                        "year":         r.get("citation_year"),
                        "archive_name": r.get("citation_archive_name", ""),
                    },
                    "similarity_score": float(r["similarity_score"]),
                    "chunk":            r["chunk"],
                } for r in reference_chunks],
                "is_silenced":      False,
                "homestead_content": None,
            })
        else:
            # No Hippocampus content — Claude generates from its own literary knowledge
            content = await _synthesize_literature(
                request=request,
                book_title=None,
                book_author=None,
                topic=request.topic,
            )
            blocks.append({
                "block_type":       BlockType.NARRATIVE.value,
                "content":          _worldview_wrap(content, request.track),
                "evidence":         [],
                "is_silenced":      False,
                "homestead_content": None,
            })

    # ── Render to cohesive format ──────────────────────────────────────────────
    await _render_lesson(state, blocks)

    state["blocks"] = blocks
    return state


async def _synthesize_literature(
    request: LessonRequest,
    book_title: str | None,
    book_author: str | None,
    topic: str,
) -> str:
    """
    Claude generates literary analysis content.
    If a specific book is provided, the analysis is grounded in that text.
    """
    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        if book_title:
            return f"Literary analysis of '{topic}' in the context of *{book_title}* by {book_author}."
        return f"Literary analysis: {topic}"

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona = _TRACK_PERSONA.get(Track.ENGLISH_LITERATURE, "a literary mentor")

    if book_title:
        user_prompt = (
            f"The student is currently reading *{book_title}* by {book_author}.\n\n"
            f"Topic they asked about: {topic}\n\n"
            f"Write a literary analysis that connects this topic to the book they're reading. "
            f"Discuss themes, character choices, narrative technique, or author's intent. "
            f"Make the student think critically about what they're reading."
        )
    else:
        user_prompt = (
            f"Topic: {topic}\n\n"
            f"Write a literary analysis or discussion of this topic. "
            f"Reference specific works, authors, or literary movements where relevant. "
            f"Make the student think critically about stories, language, and meaning."
        )

    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are writing for a {grade_desc} student in a Christian homeschool family.\n\n"
        f"{_ADELINE_VOICE}\n"
        "CONTENT RULES:\n"
        "• 2-3 paragraphs maximum\n"
        "• Discuss the text as literature — themes, craft, truth claims, worldview\n"
        "• Do NOT try to fact-check fiction. Analyze it.\n"
        "• End with a question that makes the student think about what the author is really saying\n"
    )

    try:
        return await _synthesis_call(system_prompt, user_prompt, max_tokens=800)
    except Exception as e:
        logger.error(f"[LiteratureAgent] LLM synthesis failed: {e}")
        if book_title:
            return f"Literary analysis of '{topic}' in the context of *{book_title}* by {book_author}."
        return f"Literary analysis: {topic}"


# ── Practical Agent (APPLIED_MATHEMATICS, CREATIVE_ECONOMY) ──────────────────

async def practical_agent(state: AdelineState) -> AdelineState:
    """
    Practical skills specialist — math, making, and business.

    Does NOT use the Witness Protocol. These tracks teach applied skills,
    not historical truth claims. A compound interest formula doesn't need
    a cosine similarity score.

    Uses Hippocampus as reference material (if available) without gating
    on similarity threshold. When Hippocampus is empty, Claude generates
    practical content from its knowledge.
    """
    request = state["request"]
    state["agent_name"] = "PracticalAgent"
    blocks: list[dict] = []

    # Pull any Hippocampus content as reference (no Witness gate)
    raw_results = await hippocampus.similarity_search(
        query_embedding=state["query_embedding"],
        track=request.track.value,
        top_k=3,
    )

    if raw_results:
        # Use Hippocampus results as reference material for synthesis
        content = await _state_synthesize(
            state,
            block_type=BlockType.NARRATIVE.value,
            source_chunks=raw_results,
            raw_content=raw_results[0]["chunk"],
        )
        blocks.append({
            "block_type":       BlockType.NARRATIVE.value,
            "content":          _worldview_wrap(content, request.track),
            "evidence":         [{
                "source_id":        r["id"],
                "source_title":     r["source_title"],
                "source_url":       r.get("source_url", ""),
                "witness_citation": {
                    "author":       r.get("citation_author", ""),
                    "year":         r.get("citation_year"),
                    "archive_name": r.get("citation_archive_name", ""),
                },
                "similarity_score": float(r["similarity_score"]),
                "verdict":          "VERIFIED",
                "chunk":            r["chunk"],
            } for r in raw_results],
            "is_silenced":      False,
            "homestead_content": (
                _homestead_adapt(raw_results[0]["chunk"]) if request.is_homestead else None
            ),
        })
    else:
        # No Hippocampus content — Claude generates practical content
        content = await _synthesize_practical(request)
        blocks.append({
            "block_type":       BlockType.NARRATIVE.value,
            "content":          _worldview_wrap(content, request.track),
            "evidence":         [],
            "is_silenced":      False,
            "homestead_content": None,
        })

    # ── CREATIVE_ECONOMY: always inject a ProjectBuilder GenUI block ──────────
    if request.track.value == "CREATIVE_ECONOMY" and blocks:
        project_block = await _synthesize_creative_project_block(request, blocks[0].get("content", ""))
        if project_block:
            blocks.append(project_block)

    # ── APPLIED_MATHEMATICS: inject a CodePlayground for interactive calculation ──
    if request.track.value == "APPLIED_MATHEMATICS" and blocks:
        code_block = await _synthesize_code_playground_block(request, blocks[0].get("content", ""))
        if code_block:
            blocks.append(code_block)

    # ── Render to cohesive format ──────────────────────────────────────────────
    await _render_lesson(state, blocks)

    state["blocks"] = blocks
    return state


async def _synthesize_creative_project_block(request: "LessonRequest", narrative_content: str) -> dict | None:
    """Generate a ProjectBuilder GENUI_ASSEMBLY block for CREATIVE_ECONOMY lessons."""
    import json as _json
    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    system = (
        "You generate structured ProjectBuilder component data for a creative economy lesson. "
        "Return ONLY valid JSON — no markdown fences. "
        "Schema: {\"component_type\": \"ProjectBuilder\", \"props\": {\"title\": str, "
        "\"description\": str, \"steps\": [{\"id\": str, \"title\": str, \"instruction\": str, \"type\": \"task|reflect|create\"}], "
        "\"materials\": [str], \"pricingPrompt\": str}, "
        "\"initial_state\": {\"currentStep\": 0, \"completedSteps\": []}, "
        "\"callbacks\": [\"onComplete\"], \"re_render_triggers\": [\"onComplete\"]}"
    )
    user = (
        f"Topic: {request.topic}\n"
        f"Grade: {grade_desc}\n"
        f"Lesson content:\n{narrative_content[:600]}\n\n"
        "Generate a ProjectBuilder block that walks the student through actually MAKING or SELLING "
        "something related to this topic. Steps should be concrete and doable today. "
        "Include real materials they likely have at home and a pricing prompt at the end."
    )
    try:
        raw = await _synthesis_call(system, user, max_tokens=800)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = _json.loads(raw)
        if "props" in data and "steps" in data.get("props", {}):
            return {
                "block_type": "GENUI_ASSEMBLY",
                "content": f"Project: {request.topic}",
                "evidence": [],
                "is_silenced": False,
                "homestead_content": None,
                "genui_assembly_data": data,
            }
    except Exception as e:
        logger.warning(f"[PracticalAgent] ProjectBuilder synthesis failed (non-fatal): {e}")
    return None


async def _synthesize_code_playground_block(request: "LessonRequest", narrative_content: str) -> dict | None:
    """Generate a CodePlayground GENUI_ASSEMBLY block for APPLIED_MATHEMATICS lessons."""
    import json as _json
    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    system = (
        "You generate starter JavaScript code for a math exercise playground. "
        "Return ONLY valid JSON — no markdown fences, no extra keys. "
        "Schema: {\"component_type\": \"CodePlayground\", \"props\": {"
        "\"language\": \"javascript\", "
        "\"starterCode\": str, "
        "\"instructions\": str, "
        "\"expectedOutput\": str"
        "}, \"initial_state\": {}, \"callbacks\": [\"onComplete\"]}"
        "\n\nRules for starterCode:"
        "\n• 6-12 lines of beginner JavaScript"
        "\n• Use console.log() so output is visible"
        "\n• One concrete calculation related to the math topic"
        "\n• Variable names that match the real-world scenario"
        "\n• A TODO comment where the student fills in the formula"
    )
    user = (
        f"Topic: {request.topic}\n"
        f"Grade: {grade_desc}\n"
        f"Lesson content:\n{narrative_content[:500]}\n\n"
        "Generate a CodePlayground block with a JavaScript exercise that lets the student "
        "calculate or verify the math concept from this lesson. "
        "Make it feel like running a real computation, not a worksheet."
    )
    try:
        raw = await _synthesis_call(system, user, max_tokens=600)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = _json.loads(raw)
        if "props" in data and "starterCode" in data.get("props", {}):
            return {
                "block_type": "GENUI_ASSEMBLY",
                "content": f"Try the math: {request.topic}",
                "evidence": [],
                "is_silenced": False,
                "homestead_content": None,
                "genui_assembly_data": data,
            }
    except Exception as e:
        logger.warning(f"[PracticalAgent] CodePlayground synthesis failed (non-fatal): {e}")
    return None


async def _synthesize_molecule_sim_block(request: "LessonRequest", narrative_content: str) -> dict | None:
    """Generate a MoleculeSimulator GENUI_ASSEMBLY block for CREATION_SCIENCE lessons."""
    import json as _json
    CHEMISTRY_KEYWORDS = {
        "molecule", "atom", "bond", "compound", "element", "reaction", "gas", "liquid",
        "solid", "water", "oxygen", "carbon", "hydrogen", "chemistry", "chemical",
        "matter", "state", "phase", "temperature", "heat", "particle", "electron",
        "protein", "cell", "dna", "energy",
    }
    topic_lower = request.topic.lower()
    if not any(kw in topic_lower for kw in CHEMISTRY_KEYWORDS):
        return None

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    system = (
        "You generate configuration for a molecule/particle simulation. "
        "Return ONLY valid JSON — no markdown fences. "
        "Schema: {\"component_type\": \"MoleculeSimulator\", \"props\": {"
        "\"title\": str, "
        "\"description\": str, "
        "\"substance\": str, "
        "\"questions\": [{\"id\": str, \"text\": str, \"options\": [str, str, str], \"correctIndex\": int}]"
        "}, \"initial_state\": {}, \"callbacks\": [\"onComplete\"]}"
        "\n\nRules:"
        "\n• title: short (4-6 words)"
        "\n• description: 1-2 sentences explaining what to observe"
        "\n• substance: the molecule or substance name with formula if applicable"
        "\n• questions: 2-3 questions about what the student observes in the simulation"
    )
    user = (
        f"Topic: {request.topic}\n"
        f"Grade: {grade_desc}\n"
        f"Lesson content:\n{narrative_content[:500]}\n\n"
        "Generate a MoleculeSimulator block so the student can interact with particle motion "
        "and answer questions about what they observe."
    )
    try:
        raw = await _synthesis_call(system, user, max_tokens=500)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = _json.loads(raw)
        if "props" in data and "title" in data.get("props", {}):
            return {
                "block_type": "GENUI_ASSEMBLY",
                "content": f"Molecule simulation: {data['props'].get('substance', request.topic)}",
                "evidence": [],
                "is_silenced": False,
                "homestead_content": None,
                "genui_assembly_data": data,
            }
    except Exception as e:
        logger.warning(f"[ScienceAgent] MoleculeSimulator synthesis failed (non-fatal): {e}")
    return None


async def _synthesize_drag_drop_timeline_block(request: "LessonRequest", timeline_events: list) -> dict | None:
    """Generate a DragDropTimeline GENUI_ASSEMBLY block from existing timeline events."""
    if not timeline_events or len(timeline_events) < 3:
        return None

    import random as _random

    # Shuffle a copy so the student must re-order them correctly
    shuffled = timeline_events[:]
    _random.shuffle(shuffled)

    # DragDropTimeline expects: events[] with id, label, date, description
    # The component determines correct order by sorting on event.date — no correctIndex needed.
    try:
        events_in_order = []
        for idx, event in enumerate(timeline_events):
            label = event.get("label", "")
            date  = event.get("date", "")
            if not label:
                continue
            events_in_order.append({
                "id":          f"evt-{idx}",
                "label":       label,
                "date":        date,
                "description": event.get("description", ""),
            })

        shuffled_events = events_in_order[:]
        _random.shuffle(shuffled_events)

        data = {
            "component_type": "DragDropTimeline",
            "props": {
                "title":   f"Put these events in order: {request.topic}",
                "events":  shuffled_events,
            },
            "initial_state": {"completed": False},
            "callbacks": ["onComplete"],
        }
        return {
            "block_type": "GENUI_ASSEMBLY",
            "content": "Arrange these events in chronological order",
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
            "genui_assembly_data": data,
        }
    except Exception as e:
        logger.warning(f"[HistorianAgent] DragDropTimeline synthesis failed (non-fatal): {e}")
    return None


def _synthesize_concept_map_block(topic: str, mind_map_data: dict) -> dict | None:
    """
    Convert an existing mind_map_data tree into an InteractiveConceptMap GENUI_ASSEMBLY block.
    Students drag nodes and draw their own connections on top of the tree structure.
    No LLM call needed — derives nodes and edges directly from the mind map.
    """
    try:
        root = mind_map_data.get("root") or {}
        nodes: list[dict] = []
        edges: list[dict] = []

        def walk(node: dict, parent_id: str | None = None) -> None:
            nid = node.get("id", "")
            label = node.get("label", "")
            if not nid or not label:
                return
            nodes.append({"id": nid, "label": label})
            if parent_id:
                edges.append({"source": parent_id, "target": nid})
            for child in node.get("children", []):
                walk(child, nid)

        walk(root)

        if len(nodes) < 3:
            return None

        data = {
            "component_type": "InteractiveConceptMap",
            "props": {
                "title":          f"Map the connections: {topic}",
                "nodes":          nodes,
                "suggestedEdges": edges[:4],  # show a few parent-child edges as hints
            },
            "initial_state": {},
            "callbacks": ["onComplete"],
        }
        return {
            "block_type":        "GENUI_ASSEMBLY",
            "content":           f"Concept map: {topic}",
            "evidence":          [],
            "is_silenced":       False,
            "homestead_content": None,
            "genui_assembly_data": data,
        }
    except Exception as e:
        logger.warning(f"[Orchestrator] InteractiveConceptMap synthesis failed (non-fatal): {e}")
    return None


async def _synthesize_practical(request: LessonRequest) -> str:
    """LLM generates practical/applied content for math and creative economy."""
    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        return f"Practical lesson: {request.topic}"

    grade_desc = _GRADE_DESC.get(request.grade_level, f"grade {request.grade_level}")
    persona = _TRACK_PERSONA.get(request.track, "a practical mentor")

    system_prompt = (
        f"You are Adeline — {persona}\n\n"
        f"You are writing for a {grade_desc} student in a Christian homeschool family.\n\n"
        f"{_ADELINE_VOICE}\n"
        "CONTENT RULES:\n"
        "• 2-3 paragraphs maximum\n"
        "• Use REAL numbers, REAL scenarios, REAL materials\n"
        "• Every lesson must end with something the student can DO or CALCULATE today\n"
        "• No abstract theory without a concrete application\n"
        "• If math: show the formula, then a worked example using their life\n"
        "• If creative economy: name a specific product, pricing strategy, or skill to practice\n"
    )

    user_prompt = (
        f"Topic: {request.topic}\n"
        f"Track: {request.track.value.replace('_', ' ').title()}\n\n"
        f"Write a practical lesson in Adeline's voice. Ground it in something real "
        f"the student can do this week."
    )

    try:
        return await _synthesis_call(system_prompt, user_prompt, max_tokens=800)
    except Exception as e:
        logger.error(f"[PracticalAgent] LLM synthesis failed: {e}")
        return f"Practical lesson: {request.topic}"


# ── Format selector ───────────────────────────────────────────────────────────

async def _decide_formats(
    topic: str,
    content: str,
    track: "Track",
    grade_level: str,
    allow_timeline: bool = False,
) -> list[str]:
    """
    One Claude call decides which multimodal formats genuinely add value
    for this specific lesson. Returns a subset of the available formats.

    Rules Claude uses:
    - MIND_MAP: good for multi-concept topics; skip for single ideas or stories
    - TIMELINE: only if chronology is present AND allow_timeline=True
    - MNEMONIC: only if 3+ distinct terms need to be memorised
    - NARRATED_SLIDE: good for most lessons; skip if content is very short (<150 chars)
    """
    import json as _json

    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        defaults = ["MIND_MAP", "NARRATED_SLIDE"]
        if allow_timeline:
            defaults.insert(1, "TIMELINE")
        return defaults

    available = ["MIND_MAP", "MNEMONIC", "NARRATED_SLIDE"]
    if allow_timeline:
        available.insert(1, "TIMELINE")

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")

    system_prompt = (
        "You are a curriculum designer deciding which learning formats add genuine value "
        "to a specific lesson. Be selective — clutter hurts learning. "
        "Output ONLY valid JSON: {\"formats\": [\"FORMAT1\", ...]}"
    )
    user_prompt = (
        f"Lesson topic: {topic}\n"
        f"Track: {track.value.replace('_', ' ')}\n"
        f"Grade: {grade_desc}\n"
        f"Content preview: {content[:400]}\n\n"
        f"Available formats: {available}\n\n"
        "Which formats genuinely add learning value for THIS specific lesson?\n"
        "Rules:\n"
        "- MIND_MAP: include if the topic has multiple related concepts with hierarchy. "
        "Skip for single-concept topics or narrative stories.\n"
        "- TIMELINE: include only if chronological sequence is central to the topic.\n"
        "- MNEMONIC: include only if there are 3+ distinct terms/facts the student must memorise.\n"
        "- NARRATED_SLIDE: include for most lessons. Skip only if content is a single short paragraph.\n"
        "Return 0-3 formats maximum. Be honest — fewer is better than irrelevant blocks."
    )

    try:
        text = await _synthesis_call(system_prompt, user_prompt, max_tokens=120)
        text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        raw = _json.loads(text)
        chosen = [f for f in raw.get("formats", []) if f in available]
        # Never return empty — always give at least a narrated slide
        if not chosen:
            chosen = ["NARRATED_SLIDE"]
        logger.info(f"[FormatSelector] Chose {chosen} for '{topic}' ({track.value})")
        return chosen
    except Exception as e:
        logger.warning(f"[FormatSelector] Failed — using defaults: {e}")
        return ["MIND_MAP", "NARRATED_SLIDE"]


async def _inject_modal_supplement(
    state: "AdelineState",
    blocks: list[dict],
    synthesis_text: str,
) -> None:
    """
    Append a modality-matched GENUI_ASSEMBLY supplement if the student's preferred
    learning style is not already well-served by the rendered blocks.

    Called at the end of _render_lesson after the main cascade resolves.
    Mutates blocks in place. Non-blocking — any failure is logged and skipped.
    """
    from app.algorithms.component_selector import select_modal_supplement

    modality = state.get("preferred_modality", "text")
    if not modality or modality == "auditory":
        return  # auditory is served by animated sketchnote / narrated slide cascade

    # Collect components already in this lesson to avoid duplication
    already_emitted = [
        b.get("genui_assembly_data", {}).get("component_type", "")
        for b in blocks
        if b.get("block_type") == "GENUI_ASSEMBLY"
    ]

    request = state["request"]
    mastery_band = state.get("mastery_band", "DEVELOPING")

    # Map mastery band to DifficultyLevel
    diff_map = {
        "NOVICE":      "EMERGING",
        "DEVELOPING":  "DEVELOPING",
        "PROFICIENT":  "EXPANDING",
        "ADVANCED":    "MASTERING",
        "EMERGING":    "EMERGING",
        "EXPANDING":   "EXPANDING",
        "MASTERING":   "MASTERING",
    }
    difficulty = diff_map.get(mastery_band, "DEVELOPING")

    component_type = select_modal_supplement(
        preferred_modality=modality,
        difficulty=difficulty,
        track=request.track.value,
        already_emitted=already_emitted,
    )

    if not component_type:
        return

    # Build lightweight props for the selected component
    try:
        props: dict = {}
        initial_state: dict = {}
        callbacks: list[str] = ["onComplete"]

        if component_type == "AutoDiagram":
            props = {
                "description": synthesis_text[:500],
                "diagramType": "concept_map",
                "title": f"Concept Map: {request.topic}",
            }

        elif component_type == "VirtualManipulative":
            topic_lower = request.topic.lower()
            manip_type = (
                "fractions" if any(w in topic_lower for w in ["fraction", "ratio", "divide", "part"])
                else "geometry" if any(w in topic_lower for w in ["shape", "angle", "area", "perimeter", "geometry"])
                else "place_value"
            )
            props = {"type": manip_type, "title": f"Explore: {request.topic}"}
            initial_state = {"currentStep": 0}

        elif component_type == "SimulationEmbed":
            props = {
                "simulationUrl": "https://phet.colorado.edu/en/simulations",
                "title": f"Interactive Simulation: {request.topic}",
                "parameters": {"topic": request.topic},
            }

        elif component_type == "TaskScaffold":
            props = {
                "title": f"Step-by-step: {request.topic}",
                "tasks": [
                    {"id": "t1", "instruction": f"Read through what you learned about {request.topic}."},
                    {"id": "t2", "instruction": "Write down the three most important facts in your own words."},
                    {"id": "t3", "instruction": "Apply what you learned: find one real example in your home or community."},
                ],
                "currentStep": 0,
            }
            initial_state = {"currentStep": 0, "completedTasks": []}

        elif component_type == "ScaffoldedProblem":
            props = {
                "title": f"Practice Problem: {request.topic}",
                "problem": {
                    "question": f"Based on what you just learned about {request.topic}, solve this step-by-step.",
                    "context": synthesis_text[:300],
                    "scaffoldLevel": 3,
                },
                "scaffoldLevel": 3,
            }
            initial_state = {"currentStep": 0, "hintsUsed": 0}

        elif component_type == "HardThingChallenge":
            props = {
                "title": f"Challenge: {request.topic}",
                "misconceptions": [
                    f"A common misunderstanding about {request.topic} is oversimplifying it.",
                ],
                "counterexamples": [
                    f"Think of a situation where the standard explanation of {request.topic} breaks down.",
                ],
                "testCases": [
                    f"Explain {request.topic} to someone younger without using any technical terms.",
                ],
            }

        elif component_type == "GlowGrow":
            props = {
                "strengthArea": f"You engaged with {request.topic}",
                "growthArea": f"Going deeper on {request.topic}",
                "feedbackText": (
                    f"You've covered the core ideas around {request.topic}. "
                    "What's one question you still have? Bring it back to Adeline."
                ),
            }

        elif component_type == "RealWorldApplication":
            props = {
                "applicationText": synthesis_text[:400],
                "examples": [
                    {"scenario": f"How does {request.topic} show up on a homestead or in your daily life?"},
                ],
            }

        elif component_type in ("PeerTutoringCard", "DiscussionForum"):
            props = {
                "conceptTitle": request.topic,
                "conceptTrack": request.track.value,
                "difficulty": difficulty,
                "prompt": (
                    f"Now that you've studied {request.topic}, here's a question to discuss: "
                    f"{synthesis_text[:200]}..."
                ),
            }
            if component_type == "PeerTutoringCard":
                props["requestingStudentId"] = request.student_id

        elif component_type == "LabGuide":
            # LabGuide requires a full Experiment object (frontend dereferences
            # experiment.chaos_level/materials/steps). Reuse the canonical builder
            # so generic {title, content} props never reach the render path.
            props = _build_component_props(
                component_id="LabGuide",
                topic=request.topic,
                content=synthesis_text,
                track=request.track.value,
                key_phrase=request.topic,
            )

        else:
            # Generic fallback props
            props = {"title": request.topic, "content": synthesis_text[:400]}

        blocks.append({
            "block_type": "GENUI_ASSEMBLY",
            "content": f"{component_type}: {request.topic}",
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
            "genui_assembly_data": {
                "component_type": component_type,
                "props": props,
                "initial_state": initial_state,
                "callbacks": callbacks,
            },
        })
        logger.info(
            f"[ModalSupplement] Injected {component_type} for "
            f"modality={modality} track={request.track.value}"
        )

    except Exception as e:
        logger.warning(f"[ModalSupplement] Failed to build props for {component_type} (non-fatal): {e}")


async def _render_lesson(
    state: "AdelineState",
    blocks: list[dict],
) -> None:
    """
    Render gathered content into a cohesive lesson format. Mutates `blocks` in place.

    Cascade (first successful format wins):
      1. ANIMATED_SKETCHNOTE_LESSON — full animated whiteboard lesson via Gemini
      2. NARRATED_SLIDE             — slide deck with narration (cheaper fallback)
      3. GENUI_ASSEMBLY — adaptive component via component selector (always available)

    Enrichment blocks (_enrichment=True) are SKIPPED — vocab, scripture, and
    journal cards are embedded inside the cohesive format's teaching layers.

    Interactive supplement blocks (EXPERIMENT, CodePlayground, ProjectBuilder,
    MoleculeSimulator) are ALWAYS preserved and appended after the cohesive block.

    After the cohesive format is selected, the Component Selector injects ONE
    modality-matched supplement (e.g. AutoDiagram for visual, TaskScaffold for
    kinesthetic) via _inject_modal_supplement.
    """
    if not blocks:
        return

    request = state["request"]

    # ── Separate interactive supplements and enrichment from content blocks ────
    _SUPPLEMENT_TYPES = {"EXPERIMENT"}
    supplements: list[dict] = []
    content_blocks: list[dict] = []

    for b in blocks:
        block_type = b.get("block_type", "")
        if b.get("_enrichment"):
            continue  # Enrichment is embedded in cohesive format — skip
        if block_type in _SUPPLEMENT_TYPES:
            supplements.append(b)
        elif block_type == "GENUI_ASSEMBLY":
            supplements.append(b)
        else:
            content_blocks.append(b)

    # ── Gather synthesis text from content blocks ─────────────────────────────
    _PLACEHOLDER_PHRASES = (
        "adeline is preparing",
        "check back shortly",
        "check back again soon",
        "please check back",
        "no content provided",
        "(no content provided",
        "[genui hint",
    )

    def _is_placeholder(text: str) -> bool:
        t = text.strip().lower()
        return not t or any(p in t for p in _PLACEHOLDER_PHRASES)

    synthesis_text = "\n\n".join(
        b.get("content", "") for b in content_blocks
        if not _is_placeholder(b.get("content", ""))
    ).strip()
    if not synthesis_text:
        synthesis_text = request.topic

    # ── Clean supplements — strip placeholder text from content & props.description
    def _clean_supplement(b: dict) -> dict:
        content = b.get("content", "")
        if _is_placeholder(content):
            b["content"] = request.topic
        gdata = b.get("genui_assembly_data", {})
        props = gdata.get("props", {})
        for key in ("description", "title", "thesis"):
            if key in props and _is_placeholder(str(props[key])):
                props[key] = request.topic
        gdata["props"] = props
        b["genui_assembly_data"] = gdata
        return b

    supplements = [_clean_supplement(b) for b in supplements]

    all_evidence = []
    for b in content_blocks:
        all_evidence.extend(b.get("evidence", []))

    # ── Learner context for cascade decisions ─────────────────────────────────
    mastery = state.get("mastery_score", 0.5)
    modality = state.get("preferred_modality", "visual")
    interaction_count = state.get("interaction_count", 0)
    struggle_count = state.get("recent_struggle_count", 0)
    recently_used = state.get("recently_used_components", [])

    if mastery < 0.35:
        difficulty = "EMERGING"
    elif mastery < 0.65:
        difficulty = "DEVELOPING"
    else:
        difficulty = "MASTERING"

    grade_level = getattr(request, "grade_level", "8") or "8"
    try:
        grade_int = int(grade_level) if grade_level.upper() != "K" else 0
    except (ValueError, AttributeError):
        grade_int = 8

    # Target ages string for animated sketchnote prompt
    if grade_int <= 2:
        target_ages = "5-8"
    elif grade_int <= 5:
        target_ages = "8-11"
    elif grade_int <= 8:
        target_ages = "11-14"
    else:
        target_ages = "14-18"

    # ── Precompute selector context (used in cascade level 3 and modal supplement) ──
    _TRACK_TAGS = {
        "TRUTH_HISTORY": ["history", "reading", "exploration"],
        "CREATION_SCIENCE": ["science", "exploration", "hands-on"],
        "APPLIED_MATHEMATICS": ["math", "concrete", "spatial"],
        "ENGLISH_LITERATURE": ["reading", "text", "reference"],
        "DISCIPLESHIP": ["application", "scenario", "problem-solving"],
        "JUSTICE_CHANGEMAKING": ["application", "scenario", "problem-solving"],
        "GOVERNMENT_ECONOMICS": ["reading", "scenario", "problem-solving"],
        "HOMESTEADING": ["hands-on", "application", "concrete"],
        "HEALTH_NATUROPATHY": ["science", "application", "hands-on"],
        "CREATIVE_ECONOMY": ["hands-on", "application", "problem-solving"],
    }
    topic_tags = _TRACK_TAGS.get(request.track.value, ["reading", "exploration"])
    profiler_components: list[str] = state.get("profiler_components", [])
    recently_used_for_selector = list(set(recently_used + profiler_components[1:]))

    # ── CASCADE LEVEL 1: Animated Sketchnote Lesson ───────────────────────────
    cohesive_block: dict | None = None

    try:
        from app.api.animated_lessons import generate_animated_lesson
        from app.schemas.api_models import AnimatedLessonRequest as _ALR
        _alr = _ALR(
            topic=request.topic,
            focus=synthesis_text[:800],
            duration_seconds=180,
            target_ages=target_ages,
            track=request.track.value,
            student_id=request.student_id,
        )
        sketchnote_data = await generate_animated_lesson(_alr)
        cohesive_block = {
            "block_type": BlockType.ANIMATED_SKETCHNOTE_LESSON.value,
            "content": request.topic,
            "evidence": all_evidence,
            "is_silenced": False,
            "homestead_content": None,
            "animated_sketchnote_data": sketchnote_data.model_dump(),
        }
        logger.info(f"[Render] CASCADE-1 AnimatedSketchnote OK for '{request.topic}'")
    except Exception as _e:
        logger.warning(f"[Render] CASCADE-1 AnimatedSketchnote failed ({_e}) — falling back to NarratedSlide")

    # ── CASCADE LEVEL 2: Narrated Slides ──────────────────────────────────────
    if cohesive_block is None:
        try:
            from app.agents.adapter import generate_narrated_slide_data
            from app.agents.adapter import AdaptationRequest as _AR
            _ar = _AR(
                grade_level=grade_level,
                track=request.track.value,
                bkt_pL=mastery,
            )
            slide_data = await generate_narrated_slide_data(synthesis_text, _ar)
            if slide_data:
                cohesive_block = {
                    "block_type": BlockType.NARRATED_SLIDE.value,
                    "content": request.topic,
                    "evidence": all_evidence,
                    "is_silenced": False,
                    "homestead_content": None,
                    "narrated_slide_data": slide_data,
                }
                logger.info(f"[Render] CASCADE-2 NarratedSlide OK for '{request.topic}'")
        except Exception as _e:
            logger.warning(f"[Render] CASCADE-2 NarratedSlide failed ({_e}) — falling back to component selector")

    # ── CASCADE LEVEL 3: Component Selector adaptive fallback ─────────────────
    if cohesive_block is None:
        try:
            from app.algorithms.component_selector import select_components, LearnerContext
            _ctx = LearnerContext(
                mastery_score=mastery,
                difficulty=difficulty,
                preferred_modalities=[modality, "reading"] if modality != "reading" else ["reading", "visual"],
                recent_struggle_count=struggle_count,
                time_available_minutes=15,
                needs_assessment=(interaction_count >= 3 and mastery < 0.6),
                topic_tags=topic_tags,
                recently_used_components=recently_used_for_selector,
            )
            _recs = select_components(_ctx, max_results=1)
            _component_id = _recs[0].component_id if _recs else "AdaptiveQuiz"
        except Exception as _e:
            logger.warning(f"[Render] CASCADE-3 selector failed ({_e}) — using AdaptiveQuiz")
            _component_id = "AdaptiveQuiz"

        _component_props = _build_component_props(
            component_id=_component_id,
            topic=request.topic,
            content=synthesis_text[:1500],
            track=request.track.value,
            key_phrase=synthesis_text[:80].split(".")[0] if synthesis_text else request.topic,
        )
        cohesive_block = {
            "block_type": BlockType.GENUI_ASSEMBLY.value,
            "content": synthesis_text,
            "evidence": all_evidence,
            "is_silenced": False,
            "homestead_content": None,
            "genui_assembly_data": {
                "component_type": _component_id,
                "props": _component_props,
                "initial_state": {},
                "callbacks": ["onComplete", "onStateChange"],
                "re_render_triggers": ["onComplete"],
            },
        }
        logger.info(f"[Render] CASCADE-3 selector fallback: {_component_id} for '{request.topic}'")

    # ── Assemble final block list ──────────────────────────────────────────────
    blocks.clear()
    blocks.append(cohesive_block)
    blocks.extend(supplements)

    # ── Modal supplement (component selector — ONE additional component) ───────
    from app.algorithms.component_selector import select_components, LearnerContext
    learner_ctx = LearnerContext(
        mastery_score=mastery,
        difficulty=difficulty,
        preferred_modalities=[modality, "reading"] if modality != "reading" else ["reading", "visual"],
        recent_struggle_count=struggle_count,
        time_available_minutes=15,
        needs_assessment=(interaction_count >= 3 and mastery < 0.6),
        topic_tags=topic_tags,
        recently_used_components=recently_used_for_selector,
    )
    recommendations = select_components(learner_ctx, max_results=1)

    key_phrase = synthesis_text[:80].split(".")[0] if synthesis_text else request.topic
    for rec in recommendations:
        component_props = _build_component_props(
            component_id=rec.component_id,
            topic=request.topic,
            content=synthesis_text[:1500],
            track=request.track.value,
            key_phrase=key_phrase,
        )
        blocks.append({
            "block_type": BlockType.GENUI_ASSEMBLY.value,
            "content": f"{rec.component_id}: {request.topic}",
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
            "genui_assembly_data": {
                "component_type": rec.component_id,
                "props": component_props,
                "initial_state": {},
                "callbacks": ["onComplete", "onStateChange"],
                "re_render_triggers": ["onComplete"],
            },
        })

    logger.info(
        f"[Render] Final blocks: {[b.get('block_type') for b in blocks]} "
        f"(mastery={mastery:.2f}, modality={modality}) for '{request.topic}'"
    )

    await _inject_modal_supplement(state, blocks, synthesis_text[:500])


def _build_component_props(
    component_id: str,
    topic: str,
    content: str,
    track: str,
    key_phrase: str,
) -> dict:
    """
    Build props for a GenUI component based on its type.
    Each component has a specific prop schema — this maps content into it.
    """
    if component_id == "TextExplanation":
        return {
            "title": topic,
            "content": content[:2000],
            "keyTerms": [],
            "track": track,
        }
    elif component_id == "VideoExplanation":
        return {
            "title": topic,
            "description": f"Visual explanation of {topic}",
            "sourceType": "generated",
            "content": content[:500],
            "track": track,
        }
    elif component_id == "AdaptiveQuiz":
        return {
            "topic": topic,
            "questions": [],
            "initialDifficulty": "medium",
            "track": track,
        }
    elif component_id == "AutoDiagram":
        return {
            "title": f"Concept Map: {topic}",
            "sourceContent": content[:1000],
            "diagramType": "concept-map",
            "track": track,
        }
    elif component_id == "RealWorldApplication":
        return {
            "title": f"Apply It: {topic}",
            "scenario": f"How does {topic} connect to your world?",
            "content": content[:800],
            "track": track,
        }
    elif component_id == "StealthAssessment":
        return {
            "topic": topic,
            "content": content[:800],
            "assessmentType": "comprehension",
            "track": track,
        }
    elif component_id == "VirtualManipulative":
        return {
            "title": f"Hands-on: {topic}",
            "type": "exploration",
            "track": track,
        }
    elif component_id == "MultiCompetencyWorkspace":
        return {
            "title": f"Deep Work: {topic}",
            "competencies": [topic],
            "content": content[:800],
            "track": track,
        }
    elif component_id == "CorrectiveOverlay":
        return {
            "topic": topic,
            "misconception": "",
            "correction": "",
            "track": track,
        }
    elif component_id == "LearningVelocityCard":
        return {
            "topic": topic,
            "track": track,
        }
    elif component_id == "ProgressMap":
        return {
            "topic": topic,
            "track": track,
        }
    elif component_id == "GlowGrow":
        return {
            "title": f"Check Your Understanding: {topic}",
            "topic": topic,
            "track": track,
            "questions": [
                {
                    "question": f"What is the most important idea about {key_phrase}?",
                    "options": [
                        {"text": f"It reveals a key principle within {topic}", "is_correct": True},
                        {"text": f"It is unrelated to {topic}", "is_correct": False},
                        {"text": "It has been disproved by modern research", "is_correct": False},
                    ],
                    "explanation": f"Understanding {key_phrase} is foundational to {topic}.",
                    "glow": "You're engaging with real content — keep going.",
                    "grow": f"Find one primary source that addresses {key_phrase} directly.",
                },
                {
                    "question": f"How does {topic} connect to a biblical worldview?",
                    "options": [
                        {"text": "It reflects God's ordered creation", "is_correct": True},
                        {"text": "It contradicts Scripture", "is_correct": False},
                        {"text": "It has no spiritual significance", "is_correct": False},
                    ],
                    "explanation": f"All knowledge, including {topic}, finds its foundation in God's truth.",
                    "glow": "Strong thinking about faith and learning.",
                    "grow": "Dig into a Scripture passage that speaks to this area.",
                },
            ],
        }
    elif component_id == "TaskScaffold":
        return {
            "title": f"Action Plan: {topic}",
            "context": content[:300],
            "tasks": [
                {"id": "t1", "text": f"Review the core ideas from today's lesson on {key_phrase}", "priority": "now", "estimated_minutes": 5},
                {"id": "t2", "text": f"Find one primary source or real-world example of {topic}", "priority": "today", "estimated_minutes": 10},
                {"id": "t3", "text": f"Apply what you learned: how does {topic} show up in your life or community?", "priority": "this_week", "estimated_minutes": 15},
            ],
        }
    elif component_id == "HardThingChallenge":
        return {
            "principle": f"The principle of {key_phrase}",
            "challenge": f"Take one concrete action this week that demonstrates your understanding of {topic}. "
                         f"Document it with a photo, journal entry, or short video.",
            "commitmentPrompt": f"What specific thing will you do to live out what you learned about {topic}?",
            "track": track,
        }
    elif component_id == "ScaffoldedProblem":
        return {
            "question": f"How does {key_phrase} relate to the broader topic of {topic}?",
            "steps": [
                {"instruction": f"Read or re-read the material on {topic}", "hint": "Focus on the central argument or evidence"},
                {"instruction": "Identify the two most important facts or ideas", "hint": "Look for what the author emphasizes most"},
                {"instruction": f"Explain how {key_phrase} fits into the bigger picture of {topic}", "hint": "Use your own words — no copy-paste"},
            ],
            "difficulty": "medium",
            "track": track,
        }
    elif component_id == "PeerTutoringCard":
        return {
            "conceptTitle": topic,
            "conceptTrack": track,
            "difficulty": "DEVELOPING",
        }
    elif component_id == "DiscussionForum":
        return {
            "prompt": f"How does {topic} shape the way you think or act? "
                      f"Share one specific way {key_phrase} connects to your life, faith, or community.",
            "conceptTitle": key_phrase or topic,
            "track": track,
        }
    elif component_id == "MoleculeSimulator":
        return {
            "title": f"Explore: {topic}",
            "description": content[:400] or f"Observe and interact with {topic} at a molecular level.",
            "substance": key_phrase or topic,
            "track": track,
        }
    elif component_id == "LabGuide":
        return {
            "experiment": {
                "id": str(uuid.uuid4())[:8],
                "title": topic,
                "tagline": f"Explore {key_phrase} hands-on",
                "chaos_level": 1,
                "wow_factor": 3,
                "scientific_concepts": [key_phrase or topic],
                "science_credits": [],
                "grade_band": "K-8",
                "materials": ["Paper", "Pencil", "Observation journal"],
                "safety_requirements": [],
                "steps": [
                    {"step_number": 1, "instruction": f"Read the lesson on {topic} and note the key ideas.", "tip": "Write down anything that surprises you."},
                    {"step_number": 2, "instruction": "Observe something in your environment that relates to this concept.", "tip": None},
                    {"step_number": 3, "instruction": "Sketch or describe what you observed and explain the connection.", "tip": "Include a labeled diagram if helpful."},
                ],
                "creation_connection": {
                    "title": f"God's Design in {topic}",
                    "scripture": "Psalm 19:1",
                    "explanation": f"The complexity of {key_phrase} reveals God's creative order.",
                },
                "social_media_kit": {
                    "caption_template": f"Just explored {topic}! Here's what I discovered 🔭 #HomeschoolScience",
                    "filming_tips": ["Show your materials and workspace", "Narrate each step as you go"],
                    "hashtags": ["#HomeschoolScience", "#CreationScience", "#SovereignLab"],
                },
                "estimated_minutes": 20,
            }
        }
    elif component_id in ("Simulation", "SimulationEmbed"):
        return {
            "title": f"Explore: {topic}",
            "description": f"Interactive exploration of {topic}",
            "sourceType": "generated",
            "content": content[:500],
            "track": track,
        }
    elif component_id == "TextDeep":
        return {
            "title": topic,
            "content": content[:3000],
            "keyTerms": [key_phrase] if key_phrase else [],
            "track": track,
        }
    elif component_id == "ConceptMap":
        return {
            "title": f"Concept Map: {topic}",
            "sourceContent": content[:1000],
            "diagramType": "concept-map",
            "track": track,
        }
    else:
        return {
            "topic": topic,
            "content": content[:1000],
            "track": track,
        }


# ── Multimodal synthesis functions ────────────────────────────────────────────

async def _synthesize_mind_map(
    topic: str,
    content: str,
    grade_level: str,
) -> "MindMapData | None":  # noqa: F821
    """
    Extract a concept hierarchy from lesson content.
    Returns None on any failure — never surfaces errors to the student.
    """
    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        return None
    from app.schemas.api_models import MindMapData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    system_prompt = (
        "You extract concept hierarchies from lesson content. "
        "Output ONLY valid JSON — no prose, no markdown fences. "
        "Format: {\"concept\": \"<central topic>\", \"root\": {\"id\": \"<uuid>\", \"label\": \"<root label>\", \"children\": [...]}}\n"
        "Rules: max 3 levels deep, max 4 children per node. Each node has id (uuid string), label (short phrase), children (array)."
    )
    user_prompt = (
        f"Lesson topic: {topic}\n"
        f"Student grade: {grade_desc}\n\n"
        f"Content:\n{content[:2000]}\n\n"
        "Extract the concept hierarchy as JSON."
    )
    try:
        text = await _synthesis_call(system_prompt, user_prompt, max_tokens=800)
        return MindMapData.model_validate(json.loads(text.strip()))
    except Exception as e:
        logger.warning(f"[MindMap] synthesis failed: {e}")
        return None


async def _synthesize_timeline(
    topic: str,
    content: str,
    evidence: list,
    grade_level: str,
    is_seasonal: bool = False,
) -> "TimelineData | None":  # noqa: F821
    """
    Extract a chronological sequence from lesson content.
    For history tracks: maps events to source_title from evidence.
    For homesteading: generates a seasonal calendar.
    Returns None on any failure.
    """
    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        return None
    from app.schemas.api_models import TimelineData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    source_titles = [e.get("source_title", "") for e in evidence if isinstance(e, dict)]
    source_context = f"Available primary sources: {', '.join(source_titles)}" if source_titles else ""

    if is_seasonal:
        system_prompt = (
            "You create seasonal homesteading calendars. "
            "Output ONLY valid JSON — no prose, no markdown fences. "
            "Format: {\"span\": \"<year or season range>\", \"events\": [{\"date\": \"<season>\", \"label\": \"<task>\", \"description\": \"<1-2 sentences>\", \"source_title\": \"\"}]}"
        )
        user_prompt = f"Create a seasonal homesteading calendar for: {topic}\n\nContent:\n{content[:1500]}"
    else:
        system_prompt = (
            "You extract chronological events from history lesson content. "
            "Output ONLY valid JSON — no prose, no markdown fences. "
            "Format: {\"span\": \"<year range e.g. 1860-1870>\", \"events\": [{\"date\": \"<year or date>\", \"label\": \"<short title>\", \"description\": \"<1-2 sentences>\", \"source_title\": \"<from available sources or empty>\"}]}\n"
            "Use consistent date format within the timeline. 4-8 events maximum."
        )
        user_prompt = (
            f"Lesson topic: {topic}\n"
            f"Student grade: {grade_desc}\n"
            f"{source_context}\n\n"
            f"Content:\n{content[:2000]}\n\n"
            "Extract the chronological timeline as JSON."
        )
    try:
        text = await _synthesis_call(system_prompt, user_prompt, max_tokens=800)
        return TimelineData.model_validate(json.loads(text.strip()))
    except Exception as e:
        logger.warning(f"[Timeline] synthesis failed: {e}")
        return None


async def _synthesize_mnemonic(
    content: str,
    grade_level: str,
) -> "MnemonicData | None":  # noqa: F821
    """
    Generate a mnemonic device when ≥3 concepts are present in the content.
    Returns None if fewer than 3 concepts detected or on any failure.
    """
    if not os.getenv("ANTHROPIC_API_KEY") and not GOOGLE_API_KEY and not GEMINI_API_KEY:
        return None
    from app.schemas.api_models import MnemonicData
    import json

    grade_desc = _GRADE_DESC.get(grade_level, f"grade {grade_level}")
    system_prompt = (
        "You create educational mnemonic devices. "
        "First, check if the content introduces 3 or more distinct concepts or terms. "
        "If fewer than 3, respond with exactly: {\"skip\": true}\n"
        "If 3 or more, output ONLY valid JSON — no prose, no markdown fences. "
        "Format: {\"concept\": \"<what it helps remember>\", \"acronym\": \"<WORD>\", \"words\": [\"<word1>\", \"<word2>\", ...], \"tip\": \"<memorable sentence>\"}\n"
        "CRITICAL: len(words) MUST equal len(acronym). One word per letter."
    )
    user_prompt = (
        f"Student grade: {grade_desc}\n\n"
        f"Content:\n{content[:1500]}\n\n"
        "Create a mnemonic device for the key concepts in this content."
    )
    try:
        text = await _synthesis_call(system_prompt, user_prompt, max_tokens=400)
        raw = json.loads(text.strip())
        if raw.get("skip"):
            return None
        return MnemonicData.model_validate(raw)
    except Exception as e:
        logger.warning(f"[Mnemonic] synthesis failed: {e}")
        return None


# ── Discipleship Agent ─────────────────────────────────────────────────────────
# Covers: HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP
# (ENGLISH_LITERATURE → literature_agent, APPLIED_MATH/CREATIVE_ECONOMY → practical_agent)

async def discipleship_agent(state: AdelineState) -> AdelineState:
    """
    Worldview, Character, and Cultural Discernment specialist.
    Covers HEALTH_NATUROPATHY, GOVERNMENT_ECONOMICS, DISCIPLESHIP.

    Produces NARRATIVE blocks that weave source material into a worldview-aligned
    framing (scripture context, character formation, cultural discernment).
    VERIFIED sources are presented with interpretive narrative wrap.
    ARCHIVE_SILENT: tries Researcher; falls back to RESEARCH_MISSION.

    Sefaria integration: Detects biblical references and fetches
    Everett Fox translation from Sefaria API.
    """
    request = state["request"]
    state["agent_name"] = "DiscipleshipAgent"
    blocks: list[dict] = []

    # Check for biblical references in topic (Sefaria integration)
    from app.services.sefaria import detect_biblical_reference, fetch_biblical_text, format_sefaria_content

    # Sefaria lookup ONLY for DISCIPLESHIP — not Health or Government
    biblical_ref = (
        detect_biblical_reference(request.topic)
        if request.track == Track.DISCIPLESHIP
        else None
    )

    if biblical_ref:
        logger.info(f"[DiscipleshipAgent] Detected biblical reference: {biblical_ref}")
        sefaria_data = await fetch_biblical_text(biblical_ref)

        if sefaria_data:
            content = format_sefaria_content(sefaria_data, request.grade_level)

            blocks.append({
                "block_type": BlockType.NARRATIVE.value,
                "content": _worldview_wrap(content, request.track),
                "evidence": [{
                    "source_id": f"sefaria-{biblical_ref}",
                    "source_title": f"{sefaria_data['ref']} ({sefaria_data['version_title']})",
                    "source_url": sefaria_data['url'],
                    "witness_citation": {
                        "author": "Everett Fox (Translator)" if sefaria_data['is_fox'] else "Sefaria.org",
                        "year": 1995 if sefaria_data['is_fox'] else None,
                        "archive_name": "Sefaria / Schocken Books" if sefaria_data['is_fox'] else "Sefaria.org",
                    },
                    "similarity_score": 1.0,
                    "verdict": "VERIFIED",
                    "chunk": sefaria_data['english'],
                }],
                "is_silenced": False,
            })

        else:
            logger.warning(f"[DiscipleshipAgent] Failed to fetch {biblical_ref} from Sefaria, falling back to Hippocampus")

    # Hippocampus reference — only if Sefaria didn't already provide content.
    # Discipleship content is worldview synthesis, not archival verification.
    # Hippocampus results are context; Claude wraps them in Adeline's voice.
    if not blocks:
        raw_results = await hippocampus.similarity_search(
            query_embedding=state["query_embedding"],
            track=request.track.value,
            top_k=3,
        )

        for result in raw_results:
            raw = result["chunk"]
            content = await _state_synthesize(
                state,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=[result],
                raw_content=raw,
            )
            blocks.append({
                "block_type":        BlockType.NARRATIVE.value,
                "content":           _worldview_wrap(content, request.track),
                "evidence":          [{
                    "source_id":        result["id"],
                    "source_title":     result["source_title"],
                    "source_url":       result.get("source_url", ""),
                    "witness_citation": {
                        "author":       result.get("citation_author", ""),
                        "year":         result.get("citation_year"),
                        "archive_name": result.get("citation_archive_name", ""),
                    },
                    "similarity_score": float(result["similarity_score"]),
                    "verdict":          "VERIFIED",
                    "chunk":            raw,
                }],
                "is_silenced":       False,
                "homestead_content": _homestead_adapt(raw) if request.is_homestead else None,
            })

    if not blocks:
        # Both Sefaria and Hippocampus empty — try web search (seeds Hippocampus for next time)
        logger.info("[DiscipleshipAgent] No content yet — searching web to seed and generate.")
        web_results = await search_witnesses(request.topic, request.track.value)
        if web_results:
            raw = web_results[0].get("chunk", request.topic)
            content = await _state_synthesize(
                state,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=web_results,
                raw_content=raw,
            )
            blocks.append({
                "block_type":        BlockType.NARRATIVE.value,
                "content":           _worldview_wrap(content, request.track),
                "evidence":          [{
                    "source_id":        r.get("source_id", ""),
                    "source_title":     r.get("source_title", ""),
                    "source_url":       r.get("source_url", ""),
                    "witness_citation": r.get("witness_citation", {}),
                    "similarity_score": float(r.get("similarity_score", 0)),
                    "verdict":          "VERIFIED",
                    "chunk":            r.get("chunk", ""),
                } for r in web_results[:2]],
                "is_silenced":       False,
                "homestead_content": None,
            })
            state["researcher_activated"] = True
        else:
            # Web search also empty — Claude generates from its own knowledge
            logger.info("[DiscipleshipAgent] No web results — generating from Claude knowledge.")
            content = await _state_synthesize(
                state,
                block_type=BlockType.NARRATIVE.value,
                source_chunks=[],
                raw_content=request.topic,
            )
            blocks.append({
                "block_type":        BlockType.NARRATIVE.value,
                "content":           _worldview_wrap(content, request.track),
                "evidence":          [],
                "is_silenced":       False,
                "homestead_content": None,
            })

    # ── Render to cohesive format ──────────────────────────────────────────────
    await _render_lesson(state, blocks)

    state["blocks"] = blocks
    return state


def _worldview_wrap(content: str, track: Track) -> str:
    """
    Frame content with a plain-spoken worldview lens per track.
    No churchy clichés. No hollow motivation. Just truth, connected to purpose.
    """
    lead = {
        Track.DISCIPLESHIP:         "Scripture doesn't stop at Sunday morning.",
        Track.HEALTH_NATUROPATHY:   "Your body was designed by YHWH — not by Pfizer.",
        Track.GOVERNMENT_ECONOMICS: "Power doesn't work the way the textbook says.",
        Track.ENGLISH_LITERATURE:   "Every story is a truth claim. Read it like one.",
        Track.APPLIED_MATHEMATICS:  "Math doesn't live on tests. It lives on your land, in your budget, at the market.",
        Track.CREATIVE_ECONOMY:     "Making something with your hands that someone will pay for is one of the most countercultural things you can do.",
    }.get(track, "Here's what this actually means:")

    # The closing challenge replaces the generic "How does this shape..." question
    challenge = {
        Track.DISCIPLESHIP:         "What does Scripture actually say about this — and what does that require of you?",
        Track.HEALTH_NATUROPATHY:   "What would you do differently if you trusted your body more than the system?",
        Track.JUSTICE_CHANGEMAKING:  "Corporations do this for profit. How would you do it for justice?",
        Track.GOVERNMENT_ECONOMICS: "Who benefits from this system staying broken? Who pays the price?",
        Track.ENGLISH_LITERATURE:   "What does this author want you to believe — and do you agree?",
        Track.APPLIED_MATHEMATICS:  "Where would you use this math this week? Calculate a real number.",
        Track.CREATIVE_ECONOMY:     "What will you make? What materials do you already have? What would you charge for it?",
    }.get(track, "What does this change about how you act?")

    return (
        f"*{lead}*\n\n"
        f"{content}\n\n"
        f"*{challenge}*"
    )


# ── Registrar Agent (post-processing, all tracks) ─────────────────────────────

async def registrar_agent(state: AdelineState) -> AdelineState:
    """
    CASE credit and xAPI record emitter — runs after every specialist agent.

    For each completed lesson block it emits one xAPI LearningActivity statement.
    For the lesson as a whole it generates a CASE-compatible credit entry.
    These are stored in state and returned on the LessonResponse for Phase 6
    persistence (adeline-brain/app/api/journal.py will write them to DB).
    """
    request   = state["request"]
    lesson_id = state["lesson_id"]
    now_iso   = datetime.now(timezone.utc).isoformat()
    blocks    = state["blocks"]

    # ── xAPI statements: one per block ────────────────────────────────────────
    xapi_statements: list[dict] = []
    for i, block in enumerate(blocks):
        verb = _block_type_to_xapi_verb(block.get("block_type", ""))
        xapi_statements.append({
            "id":        str(uuid.uuid4()),
            "timestamp": now_iso,
            "actor":     {"objectType": "Agent", "account": {"name": request.student_id}},
            "verb":      {
                "id":      f"http://adlnet.gov/expapi/verbs/{verb}",
                "display": {"en-US": verb},
            },
            "object":    {
                "id":         f"urn:adeline:lesson:{lesson_id}:block:{i}",
                "definition": {
                    "name": {"en-US": f"{request.topic} — Block {i + 1}"},
                    "type": "http://adlnet.gov/expapi/activities/lesson",
                },
            },
            "context":   {
                "extensions": {
                    "https://adeline.app/xapi/ext/track":       request.track.value,
                    "https://adeline.app/xapi/ext/grade_level": request.grade_level,
                    "https://adeline.app/xapi/ext/agent":       state.get("agent_name", ""),
                    "https://adeline.app/xapi/ext/is_homestead": request.is_homestead,
                    "https://adeline.app/xapi/ext/block_type":  block.get("block_type", ""),
                }
            },
        })

    # ── CASE credit entry: one per lesson ─────────────────────────────────────
    verified_count   = sum(
        1 for b in blocks
        if b.get("block_type") in (BlockType.PRIMARY_SOURCE.value, BlockType.NARRATIVE.value)
    )
    lab_count        = sum(1 for b in blocks if b.get("block_type") == BlockType.LAB_MISSION.value)
    experiment_count = sum(1 for b in blocks if b.get("block_type") == BlockType.EXPERIMENT.value)
    mindmap_count    = sum(1 for b in blocks if b.get("block_type") == BlockType.MIND_MAP.value)
    timeline_count   = sum(1 for b in blocks if b.get("block_type") == BlockType.TIMELINE.value)
    mnemonic_count   = sum(1 for b in blocks if b.get("block_type") == BlockType.MNEMONIC.value)
    slide_count      = sum(1 for b in blocks if b.get("block_type") == BlockType.NARRATED_SLIDE.value)
    credit_hours     = round(min(1.0,
        0.1  * (verified_count + lab_count) +
        0.25 * experiment_count +
        0.05 * (mindmap_count + timeline_count) +
        0.03 * mnemonic_count +
        0.08 * slide_count
    ), 2)

    credits_awarded: list[dict] = [{
        "id":                  str(uuid.uuid4()),
        "lesson_id":           lesson_id,
        "student_id":          request.student_id,
        "course_title":        f"{request.topic.title()} ({request.track.value.replace('_', ' ').title()})",
        "track":               request.track.value,
        "oas_standards":       [s.get("standard_id", "") for s in state.get("oas_standards", [])],
        "activity_description": (
            f"Lesson on '{request.topic}' via {state.get('agent_name', 'Adeline')} — "
            f"{verified_count} verified source(s)"
            + (f", {lab_count} lab mission(s)" if lab_count else "")
            + (f", {experiment_count} experiment(s)" if experiment_count else "")
            + (f", {mindmap_count + timeline_count} visual map(s)" if mindmap_count + timeline_count else "")
            + (f", {slide_count} slide deck(s)" if slide_count else "")
        ),
        "credit_hours":        credit_hours,
        "credit_type":         _track_to_credit_type(request.track),
        "is_homestead_credit": request.is_homestead,
        "completed_at":        now_iso,
        "researcher_activated": state["researcher_activated"],
    }]

    state["xapi_statements"] = xapi_statements
    state["credits_awarded"]  = credits_awarded
    logger.info(
        f"[RegistrarAgent] Emitted {len(xapi_statements)} xAPI statement(s) + "
        f"{credit_hours} credit hours for student={request.student_id}"
    )
    return state


def _block_type_to_xapi_verb(block_type: str) -> str:
    return {
        BlockType.PRIMARY_SOURCE.value:   "experienced",
        BlockType.NARRATIVE.value:        "experienced",
        BlockType.LAB_MISSION.value:      "attempted",
        BlockType.EXPERIMENT.value:       "completed",    # Sovereign Lab experiments count as "completed"
        BlockType.RESEARCH_MISSION.value: "interacted",
        BlockType.QUIZ.value:             "attempted",
        BlockType.TEXT.value:             "experienced",
        BlockType.MIND_MAP.value:       "composed",
        BlockType.TIMELINE.value:       "experienced",
        BlockType.MNEMONIC.value:       "memorized",
        BlockType.NARRATED_SLIDE.value: "experienced",
    }.get(block_type, "experienced")


def _track_to_credit_type(track: Track) -> str:
    """
    Map track to default credit type.
    CREATION_SCIENCE now returns LABORATORY_SCIENCE (not generic CORE)
    when the lesson contains EXPERIMENT blocks — handled in registrar_agent.
    """
    return {
        Track.TRUTH_HISTORY:        "CORE",
        Track.CREATION_SCIENCE:     "LABORATORY_SCIENCE",
        Track.ENGLISH_LITERATURE:   "CORE",
        Track.GOVERNMENT_ECONOMICS: "CORE",
        Track.JUSTICE_CHANGEMAKING: "CORE",
        Track.DISCIPLESHIP:         "ELECTIVE",
        Track.HEALTH_NATUROPATHY:   "ELECTIVE",
        Track.HOMESTEADING:         "HOMESTEAD",
        Track.APPLIED_MATHEMATICS:  "MATHEMATICS",
        Track.CREATIVE_ECONOMY:     "VOCATIONAL",
    }.get(track, "ELECTIVE")


# ── Router ────────────────────────────────────────────────────────────────────



async def _append_lesson_enrichment(state: AdelineState) -> None:
    """
    Append vocabulary, quiz, journal prompt, and scripture to every lesson.

    Called after the specialist agent runs. Skips if a QUIZ block already
    exists (meaning _generate_from_knowledge already produced the full rich
    set via the structured fallback). Does NOT add the track-specific activity
    module (scienceLab/historyWitness/challengeActivity) — specialist agents
    own that content.
    """
    import json as _json

    existing_types = {b.get("block_type") for b in state["blocks"]}
    if BlockType.QUIZ.value in existing_types:
        return  # already fully enriched (came through _generate_from_knowledge)

    request = state["request"]
    structured = await _gemini_structured_lesson(
        request.topic, request.track, request.grade_level
    )
    if not structured:
        return

    def _block(block_type: BlockType, content: str) -> dict:
        return {
            "block_type": block_type.value,
            "content": content,
            "evidence": [],
            "is_silenced": False,
            "homestead_content": (
                _homestead_adapt(content) if request.is_homestead else None
            ),
        }

    # Vocabulary
    vocab = structured.get("vocabulary", [])
    if vocab:
        vocab_lines = []
        for v in vocab:
            word = v.get("word", "")
            defn = v.get("definition", "")
            pron = v.get("pronunciation", "")
            example = v.get("exampleSentence", "")
            pron_str = f" *({pron})*" if pron else ""
            vocab_lines.append(f"**{word}**{pron_str} — {defn}")
            if example:
                vocab_lines.append(f"> *{example}*")
        b = _block(BlockType.TEXT, "\n\n".join(vocab_lines))
        b["_enrichment"] = True
        state["blocks"].append(b)

    # Scripture
    scripture = structured.get("scripture")
    if scripture:
        verse = scripture.get("verse", "")
        ref = scripture.get("reference", "")
        insight = scripture.get("insight", "")
        b = _block(
            BlockType.NARRATIVE,
            f"**[Paradise Scripture: {ref}]**\n\n> {verse}\n\n{insight}",
        )
        b["_enrichment"] = True
        state["blocks"].append(b)

    # Journal prompt
    journal = structured.get("suggestedJournalPrompt", "")
    if journal:
        b = _block(BlockType.TEXT, f"**Journal Prompt:** {journal}")
        b["_enrichment"] = True
        state["blocks"].append(b)

    # Quiz — always added
    quiz = structured.get("quiz", [])
    if quiz:
        state["blocks"].append({
            "block_type": BlockType.QUIZ.value,
            "content": _json.dumps(quiz),
            "evidence": [],
            "is_silenced": False,
            "homestead_content": None,
        })

    logger.info(
        f"[RichLesson] Enrichment appended for {request.topic!r} "
        f"({request.track.value}): vocab={len(vocab)}, quiz={len(quiz)}, "
        f"scripture={'yes' if scripture else 'no'}, journal={'yes' if journal else 'no'}"
    )


def _route(state: AdelineState) -> Literal[
    "historian", "justice", "science", "discipleship", "literature", "practical"
]:
    track = state["request"].track
    if track in _HISTORIAN_TRACKS:
        return "historian"
    if track in _JUSTICE_TRACKS:
        return "justice"
    if track in _SCIENCE_TRACKS:
        return "science"
    if track in _LITERATURE_TRACKS:
        return "literature"
    if track in _PRACTICAL_TRACKS:
        return "practical"
    return "discipleship"


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def run_orchestrator(
    request: LessonRequest,
    query_embedding: list[float],
    interaction_count: int = 10,
    cross_track_acknowledgment: str | None = None,
    mastery_score: float = 0.0,
    mastery_band: str = "NOVICE",
    student_message: str | None = None,
    preferred_modality: str = "text",
) -> LessonResponse:
    """
    Routes the request to the correct specialist agent, graph-links to
    OAS Standards via Neo4j, runs the RegistrarAgent for xAPI + CASE credits,
    and returns a structured LessonResponse.

    Agent routing:
      TRUTH_HISTORY                          → HistorianAgent (Witness Protocol, strict threshold 0.82)
      JUSTICE_CHANGEMAKING                   → JusticeAgent (Witness-gated PRIMARY_SOURCE + investigative RESEARCH_MISSION)
      CREATION_SCIENCE, HOMESTEADING         → ScienceAgent (LAB_MISSION, no Witness)
      ENGLISH_LITERATURE                     → LiteratureAgent (book-context, no Witness)
      APPLIED_MATHEMATICS, CREATIVE_ECONOMY  → PracticalAgent (applied skills, no Witness)
      HEALTH_NATUROPATHY, GOV_ECON, DISCIP.  → DiscipleshipAgent (worldview, no Witness)

    RegistrarAgent always runs last as a post-processing step regardless of track.

    When Hippocampus lacks verified sources (ARCHIVE_SILENT), the Researcher
    tool automatically searches archive.org, gutenberg.org, and archives.gov
    before falling back to a student-facing RESEARCH_MISSION.

    Args:
        mastery_score: Student's current mastery in this track (0.0–1.0) for ZPD scaffolding.
        mastery_band: Student's mastery band (NOVICE/DEVELOPING/PROFICIENT/ADVANCED).
        student_message: Last student message for ZPD pedagogical directive generation.
    """
    lesson_id = str(uuid.uuid4())

    state: AdelineState = {
        "request":              request,
        "lesson_id":            lesson_id,
        "query_embedding":      query_embedding,
        "blocks":               [],
        "oas_standards":        [],
        "has_research_missions": False,
        "researcher_activated": False,
        "agent_name":           "",
        "xapi_statements":      [],
        "credits_awarded":      [],
        "interaction_count":    interaction_count,
        "cross_track_acknowledgment": cross_track_acknowledgment,
        "mastery_score":        mastery_score,
        "mastery_band":         mastery_band,
        "student_message":      student_message,
        "preferred_modality":   preferred_modality,
    }

    route = _route(state)
    logger.info(
        f"[Orchestrator] Routing to: {route} | "
        f"track={request.track.value} | topic='{request.topic}'"
    )

    # ── 1. Specialist agent ────────────────────────────────────────────────────
    if route == "historian":
        state = await historian_agent(state)
    elif route == "justice":
        state = await justice_agent(state)
    elif route == "science":
        state = await science_agent(state)
    elif route == "literature":
        state = await literature_agent(state)
    elif route == "practical":
        state = await practical_agent(state)
    else:
        state = await discipleship_agent(state)

    # ── 2. Cross-track acknowledgment (prepend to first block if set) ─────────
    if state.get("cross_track_acknowledgment") and state["blocks"]:
        state["blocks"][0]["content"] = (
            state["cross_track_acknowledgment"] + "\n\n" + state["blocks"][0]["content"]
        )

    # ── 3. Graph context (Neo4j) ───────────────────────────────────────────────
    state["oas_standards"] = await _fetch_graph_context(request.track.value)
    primary_count = sum(1 for s in state["oas_standards"] if s.get("source_type") == "primary")
    cross_count   = sum(1 for s in state["oas_standards"] if s.get("source_type") == "cross_track")

    # ── 4. Registrar (xAPI + CASE credits) ────────────────────────────────────
    state = await registrar_agent(state)

    logger.info(
        f"[Orchestrator] agent={state['agent_name']} | "
        f"graph: {primary_count} primary + {cross_count} cross-track | "
        f"blocks: {len(state['blocks'])} | "
        f"research_missions: {state['has_research_missions']} | "
        f"researcher_activated: {state['researcher_activated']} | "
        f"xapi_statements: {len(state['xapi_statements'])} | "
        f"credits: {len(state['credits_awarded'])}"
    )

    blocks = [LessonBlockResponse(**b) for b in state["blocks"]]

    return LessonResponse(
        lesson_id=lesson_id,
        title=f"{request.topic.title()} — Track {request.track.value.replace('_', ' ').title()}",
        track=request.track,
        blocks=blocks,
        has_research_missions=state["has_research_missions"],
        oas_standards=state["oas_standards"],
        researcher_activated=state["researcher_activated"],
        agent_name=state["agent_name"],
        xapi_statements=state["xapi_statements"],
        credits_awarded=state["credits_awarded"],
    )
