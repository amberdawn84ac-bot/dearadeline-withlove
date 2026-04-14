"""
Adaptation Layer — transforms a CanonicalLesson for a specific student.

Two-pass process:
  1. select_transformation(): decide block_type for this student (pure logic, no LLM)
  2. adapt/generate: rewrite text OR generate structured data (cheap LLM call)

Cost: ~1-3 LLM calls vs 3-8 for full orchestrator generation.
PRIMARY_SOURCE and RESEARCH_MISSION blocks are never transformed (Witness Protocol content).
"""
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_GRADE_DESC = {
    "K": "kindergarten (age 5–6)", "1": "1st grade (age 6–7)", "2": "2nd grade (age 7–8)",
    "3": "3rd grade (age 8–9)", "4": "4th grade (age 9–10)", "5": "5th grade (age 10–11)",
    "6": "6th grade (age 11–12)", "7": "7th grade (age 12–13)", "8": "8th grade (age 13–14)",
    "9": "9th grade (age 14–15)", "10": "10th grade (age 15–16)",
    "11": "11th grade (age 16–17)", "12": "12th grade (age 17–18)",
}

_ADAPTATION_SYSTEM = """You are Adeline's ZPD distillation engine. You receive a canonical lesson (written at adult/HS depth) and a student's live mastery state.
Your job is to distill — not just rewrite — the lesson for this specific student. Rules:
- Keep every fact, date, name, and quote. NEVER invent or remove verified content.
- Filter depth: if bkt_pL < 0.30, simplify and skip advanced nuance sections.
- Rewrite vocabulary and sentence complexity for the grade level.
- Inject a GENUI hint comment at the end of the block ONLY when specified in the prompt instructions.
- Do NOT add busywork, "great job!", or filler.
- Return ONLY the rewritten content block — no preamble, no explanation.
- Write like you're talking to a smart kid at the kitchen table, not lecturing.
- If the topic genuinely touches justice, stewardship, creation, or discipleship and the track is a worldview track, append one short reflective question tied to relevant scripture (≤1 sentence). Omit entirely if no natural connection exists."""

_HIGH_STAKES_TRACKS = frozenset({
    "TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "DISCIPLESHIP",
    "CREATION_SCIENCE", "GOVERNMENT_ECONOMICS",
})

_DISCIPLESHIP_KEYWORDS = frozenset({
    "justice", "steward", "creation", "neighbor", "truth", "law",
    "sabbath", "covenant", "scripture", "gospel", "redeem", "shalom",
})


@dataclass
class AdaptationRequest:
    grade_level:            str
    track:                  str
    interests:              list[str] = field(default_factory=list)
    interaction_count:      int = 10
    recent_quiz_scores:     list[float] = field(default_factory=list)  # last N SM-2 easiness scores (0-5)
    preferred_modality:     str = "text"   # "text" | "visual" | "kinesthetic"
    # ── ZPD / BKT state (Step 1 — full personalization) ──────────────────────
    bkt_pL:                 float = 0.1   # current BKT mastery probability P(L)
    bkt_pT:                 float = 0.15  # BKT learning rate P(T)
    priority_score:         float = 0.5   # compute_priority() result 0-1
    decay_adjusted_mastery: float = 0.0   # mastery after apply_decay()
    cross_track_bias:       float = 0.0   # from apply_cross_track_bias()


# ── Transformation selection (pure logic, no LLM) ────────────────────────────

def _grade_int(grade_level: str) -> int:
    if grade_level.upper() == "K":
        return 0
    try:
        return int(grade_level)
    except ValueError:
        return 8


def select_transformation(block: dict, req: AdaptationRequest) -> str:
    """
    Returns transformation decision:
      "text_only"        — rewrite content text, keep block_type
      "to_flashcard"     — convert to FLASHCARD + generate flashcard_data
      "to_quiz"          — convert to QUIZ + generate quiz_data
      "to_timeline"      — convert to TIMELINE + generate timeline_data
      "to_narrated_slide" — convert to NARRATED_SLIDE + generate narrated_slide_data
    """
    block_type = block.get("block_type", "TEXT")
    content = block.get("content", "")
    grade = _grade_int(req.grade_level)

    # Witness Protocol content — NEVER transform
    if block_type in ("PRIMARY_SOURCE", "RESEARCH_MISSION"):
        return "text_only"

    # Lab/experiment stays as-is
    if block_type in ("LAB_MISSION", "EXPERIMENT"):
        return "text_only"

    # Already structured — don't re-transform
    if block_type in ("MIND_MAP", "TIMELINE", "MNEMONIC", "NARRATED_SLIDE",
                      "QUIZ", "FLASHCARD", "BOOK_SUGGESTION"):
        return "text_only"

    # Early interactions: keep simple regardless
    if req.interaction_count <= 3:
        if grade <= 5:
            return "to_flashcard"
        return "text_only"

    # Low BKT mastery → force quiz to build foundational knowledge
    if req.bkt_pL < 0.4 and grade >= 5 and block_type in ("NARRATIVE", "TEXT"):
        return "to_quiz"

    # Young students (K-5): flashcard for NARRATIVE/TEXT
    if grade <= 5 and block_type in ("NARRATIVE", "TEXT"):
        return "to_flashcard"

    # Date-heavy content → timeline (3+ year patterns)
    date_count = len(re.findall(r'\b(1[5-9]\d{2}|20[0-2]\d)\b', content))
    if date_count >= 3 and block_type in ("NARRATIVE", "TEXT"):
        return "to_timeline"

    # High priority score + older student → quiz to leverage readiness
    if req.priority_score > 0.7 and grade >= 7 and block_type in ("NARRATIVE", "TEXT"):
        return "to_quiz"

    # Strong quiz history (avg SM-2 easiness > 3.5) + older student → quiz
    if (req.recent_quiz_scores and grade >= 7 and
            sum(req.recent_quiz_scores) / len(req.recent_quiz_scores) > 3.5 and
            block_type in ("NARRATIVE", "TEXT")):
        return "to_quiz"

    # Visual/kinesthetic learner, grade 6+
    if req.preferred_modality in ("visual", "kinesthetic") and grade >= 6:
        return "to_narrated_slide"

    return "text_only"


# ── LLM call helper ──────────────────────────────────────────────────────────

async def _llm_call(system: str, user: str, max_tokens: int = 600) -> str:
    import asyncio as _asyncio
    from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL
    if GEMINI_API_KEY:
        import openai as _oai
        client = _oai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=GEMINI_MODEL,
                    max_tokens=max_tokens,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                )
                return response.choices[0].message.content or ""
            except Exception as gemini_err:
                if attempt == 0:
                    logger.warning(f"[Adapter] Gemini attempt 1 failed ({gemini_err}) — retrying...")
                    await _asyncio.sleep(1)
                    continue
                logger.warning(f"[Adapter] Gemini failed after 2 attempts ({gemini_err}) — falling back to Claude")
                break
    # Claude fallback (also primary path when GEMINI_API_KEY not set)
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        return response.content[0].text
    except Exception as e:
        logger.warning(f"[Adapter] LLM call failed (Claude fallback): {e}")
        return ""


# ── Text rewrite ─────────────────────────────────────────────────────────────

def _has_discipleship_theme(topic_hint: str, track: str) -> bool:
    """True if the topic or track touches justice/stewardship/creation/discipleship themes."""
    if track in _HIGH_STAKES_TRACKS:
        return True
    topic_lower = topic_hint.lower()
    return any(kw in topic_lower for kw in _DISCIPLESHIP_KEYWORDS)


def build_adaptation_prompt(req: AdaptationRequest, content: str, topic_hint: str = "") -> str:
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    interests_str = ", ".join(req.interests) if req.interests else "general learning"
    track_name = req.track.replace("_", " ").title()

    # ── Depth / complexity tier ───────────────────────────────────────────────
    if req.interaction_count <= 3:
        complexity = (
            "This is their first time in this subject — use introductory language, shorter sentences, "
            "and connect concepts to everyday things."
        )
    elif req.bkt_pL < 0.30:
        complexity = (
            f"Their BKT mastery probability is low ({req.bkt_pL:.2f}). "
            "Simplify: skip advanced nuance, use concrete examples, shorter paragraphs. "
            "Focus only on the core concept — save depth for later."
        )
    elif req.bkt_pL >= 0.65:
        complexity = (
            f"Their BKT mastery is solid ({req.bkt_pL:.2f}, decay-adjusted: {req.decay_adjusted_mastery:.2f}). "
            "You can use subject vocabulary, introduce nuance, and challenge them slightly."
        )
    else:
        complexity = (
            f"They have some background here (BKT pL={req.bkt_pL:.2f}). "
            "Use subject vocabulary but explain it naturally."
        )

    # ── Priority score instruction ────────────────────────────────────────────
    if req.priority_score > 0.7:
        priority_clause = (
            f"\nPRIORITY: This is a high-leverage concept (priority={req.priority_score:.2f}). "
            "Spend extra time on the core mechanism — don't rush past it. "
            "Make sure the student understands the 'why' before moving on."
        )
    elif req.priority_score < 0.35:
        priority_clause = (
            f"\nPRIORITY: This is lower priority right now (priority={req.priority_score:.2f}). "
            "Give a brief, clear overview only. Save deeper treatment for when their mastery builds."
        )
    else:
        priority_clause = ""

    # ── Cross-track bias instruction ──────────────────────────────────────────
    _TRACK_LABELS = {
        "TRUTH_HISTORY": "History", "CREATION_SCIENCE": "Creation Science",
        "DISCIPLESHIP": "Discipleship", "JUSTICE_CHANGEMAKING": "Justice & Changemaking",
        "GOVERNMENT_ECONOMICS": "Government & Economics", "HOMESTEADING": "Homesteading",
        "HEALTH_NATUROPATHY": "Health & Naturopathy", "ENGLISH_LITERATURE": "Literature",
        "APPLIED_MATHEMATICS": "Applied Mathematics", "CREATIVE_ECONOMY": "Creative Economy",
    }
    cross_track_clause = ""
    if req.cross_track_bias > 0.1:
        related = _TRACK_LABELS.get(req.track, req.track)
        cross_track_clause = (
            f"\nCROSS-TRACK: This student has strong adjacent-track knowledge "
            f"(bias={req.cross_track_bias:.2f}). Explicitly connect this concept to what they already "
            f"know from related subjects like {related} — bridge the familiar to the new."
        )

    # ── Forgetting / decay instruction ────────────────────────────────────────
    decay_clause = ""
    if req.decay_adjusted_mastery < req.bkt_pL * 0.6 and req.bkt_pL > 0.2:
        decay_clause = (
            f"\nFORGETTING: Significant decay detected (raw mastery={req.bkt_pL:.2f}, "
            f"decay-adjusted={req.decay_adjusted_mastery:.2f}). "
            "Revisit foundational definitions before advancing — treat this as a refresher, not a first lesson."
        )

    # ── GENUI hint ────────────────────────────────────────────────────────────
    genui_hint = ""
    if req.bkt_pL < 0.5:
        genui_hint = "\n[GENUI hint: a quiz block after this content would reinforce foundation.]"
    elif req.priority_score > 0.7 and req.preferred_modality == "visual":
        genui_hint = "\n[GENUI hint: a mind-map or narrated slide would suit this high-readiness visual learner.]"

    # ── Discipleship nudge ────────────────────────────────────────────────────
    discipleship_clause = ""
    if _has_discipleship_theme(topic_hint or req.track, req.track):
        discipleship_clause = (
            "\nIf the content naturally connects to justice, stewardship, creation, or discipleship, "
            "append one short reflective question tied to relevant scripture (e.g., Proverbs, Matthew, Genesis). "
            "One sentence maximum. Omit entirely if no genuine connection exists."
        )

    return (
        f"Rewrite the following lesson content for a {grade_desc} student "
        f"in the {track_name} curriculum. "
        f"Their interests include: {interests_str}.\n"
        f"ZPD State — BKT P(L): {req.bkt_pL:.3f}, Learning rate: {req.bkt_pT:.3f}, "
        f"Priority score: {req.priority_score:.3f}, Decay-adjusted mastery: {req.decay_adjusted_mastery:.3f}, "
        f"Cross-track bias: {req.cross_track_bias:.3f}.\n"
        f"{complexity}"
        f"{priority_clause}"
        f"{cross_track_clause}"
        f"{decay_clause}"
        f"{discipleship_clause}"
        f"{genui_hint}"
        f"\n\nORIGINAL CONTENT:\n{content}"
    )


async def adapt_block_content(content: str, req: AdaptationRequest, topic_hint: str = "") -> str:
    result = await _llm_call(_ADAPTATION_SYSTEM, build_adaptation_prompt(req, content, topic_hint))
    return result if result else content


# ── Structured data generators ───────────────────────────────────────────────

async def generate_flashcard_data(content: str, req: AdaptationRequest) -> Optional[dict]:
    """Generate {front, back, category} from content."""
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    system = (
        "You extract a single key concept from text and format it as a flashcard. "
        "Return ONLY valid JSON with keys: front (term or question, ≤12 words), "
        "back (definition or answer, 1-2 sentences), category (topic label, ≤3 words). "
        "No markdown, no explanation, just JSON."
    )
    user = f"Create a flashcard for a {grade_desc} student from this content:\n\n{content[:800]}"
    raw = await _llm_call(system, user, max_tokens=200)
    try:
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if "front" in data and "back" in data:
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


async def generate_quiz_data(content: str, req: AdaptationRequest) -> Optional[dict]:
    """Generate {question, options:[{text,is_correct}], explanation, difficulty} from content."""
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    system = (
        "You create a multiple-choice quiz question from lesson content. "
        "Return ONLY valid JSON with keys: question (string), "
        "options (array of 4 objects with keys text:string and is_correct:bool — exactly one is_correct:true), "
        "explanation (string, 1-2 sentences explaining the correct answer), "
        "difficulty (easy|medium|hard). "
        "No markdown, no explanation, just JSON."
    )
    user = f"Create a quiz question for a {grade_desc} student from this content:\n\n{content[:800]}"
    raw = await _llm_call(system, user, max_tokens=400)
    try:
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if "question" in data and "options" in data:
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


async def generate_timeline_data(content: str, req: AdaptationRequest) -> Optional[dict]:
    """Generate {span, events:[{date,label,description}]} from date-heavy content."""
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    system = (
        "You extract chronological events from lesson content and format them as a timeline. "
        "Return ONLY valid JSON with keys: span (string, e.g. '1865-1877'), "
        "events (array of objects with keys date:string, label:string ≤6 words, description:string 1-2 sentences). "
        "Include 3-6 events. No markdown, just JSON."
    )
    user = f"Extract a timeline for a {grade_desc} student from this content:\n\n{content[:1000]}"
    raw = await _llm_call(system, user, max_tokens=500)
    try:
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if "events" in data and len(data["events"]) >= 2:
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


async def generate_narrated_slide_data(content: str, req: AdaptationRequest) -> Optional[dict]:
    """Generate {total_duration_minutes, slides:[{slide_number,title,bullets,narration}]}."""
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    system = (
        "You convert lesson content into 2-3 narrated slides. "
        "Return ONLY valid JSON with keys: total_duration_minutes (number), "
        "slides (array of objects with keys slide_number:int, title:string, "
        "bullets:array of 2-4 strings, narration:string 2-3 sentences). "
        "No markdown, just JSON."
    )
    user = f"Convert this to narrated slides for a {grade_desc} student:\n\n{content[:800]}"
    raw = await _llm_call(system, user, max_tokens=600)
    try:
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if "slides" in data and len(data["slides"]) >= 1:
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


# ── Main adaptation entry point ──────────────────────────────────────────────

async def _transform_block(block: dict, req: AdaptationRequest, topic_hint: str = "") -> dict:
    """Apply transformation decision to a single block. Returns updated block dict."""
    decision = select_transformation(block, req)
    adapted = dict(block)
    content = block.get("content", "")

    if decision == "text_only":
        adapted["content"] = await adapt_block_content(content, req, topic_hint)

    elif decision == "to_flashcard":
        data = await generate_flashcard_data(content, req)
        if data:
            adapted["block_type"] = "FLASHCARD"
            adapted["flashcard_data"] = data
            adapted["content"] = data.get("front", content)
        else:
            adapted["content"] = await adapt_block_content(content, req, topic_hint)

    elif decision == "to_quiz":
        data = await generate_quiz_data(content, req)
        if data:
            adapted["block_type"] = "QUIZ"
            adapted["quiz_data"] = data
            adapted["content"] = data.get("question", content)
        else:
            adapted["content"] = await adapt_block_content(content, req, topic_hint)

    elif decision == "to_timeline":
        data = await generate_timeline_data(content, req)
        if data:
            adapted["block_type"] = "TIMELINE"
            adapted["timeline_data"] = data
            adapted["content"] = content  # keep original as context
        else:
            adapted["content"] = await adapt_block_content(content, req, topic_hint)

    elif decision == "to_narrated_slide":
        data = await generate_narrated_slide_data(content, req)
        if data:
            adapted["block_type"] = "NARRATED_SLIDE"
            adapted["narrated_slide_data"] = data
            adapted["content"] = content
        else:
            adapted["content"] = await adapt_block_content(content, req, topic_hint)

    return adapted


async def adapt_canonical_for_student(
    canonical: dict,
    req: AdaptationRequest,
) -> list[dict]:
    """
    Adapt all blocks in a canonical lesson for the student.

    Per-block: select_transformation() decides the block_type, then
    the appropriate generator produces structured data (or text rewrite).
    PRIMARY_SOURCE and RESEARCH_MISSION blocks are never transformed.

    Returns adapted blocks as list[dict] (same shape as LessonBlockResponse).
    """
    blocks = canonical.get("blocks", [])
    if not blocks:
        return blocks

    topic_hint = canonical.get("topic", "")

    adapted_blocks = await asyncio.gather(*[
        _transform_block(b, req, topic_hint) for b in blocks
    ])

    transformed = sum(
        1 for orig, adapted in zip(blocks, adapted_blocks)
        if orig.get("block_type") != adapted.get("block_type")
    )

    logger.info(
        f"[Adapter] Adapted {len(adapted_blocks)} blocks for grade={req.grade_level}, "
        f"track={req.track}, bkt_pL={req.bkt_pL:.3f}, priority={req.priority_score:.3f}, "
        f"interactions={req.interaction_count}, transformed={transformed} block types"
    )
    return list(adapted_blocks)
