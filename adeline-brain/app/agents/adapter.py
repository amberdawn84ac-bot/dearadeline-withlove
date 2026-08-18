"""Personalize canonical lesson wording without changing lesson structure.

There is deliberately no format selector here. Specialist agents author the
canonical lesson once; this adapter may adjust vocabulary and scaffolding for a
learner, but it may not turn content into cards, slides, animations, quizzes, or
generic widgets.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_GRADE_DESC = {
    "K": "kindergarten (age 5–6)", "1": "1st grade (age 6–7)", "2": "2nd grade (age 7–8)",
    "3": "3rd grade (age 8–9)", "4": "4th grade (age 9–10)", "5": "5th grade (age 10–11)",
    "6": "6th grade (age 11–12)", "7": "7th grade (age 12–13)", "8": "8th grade (age 13–14)",
    "9": "9th grade (age 14–15)", "10": "10th grade (age 15–16)",
    "11": "11th grade (age 16–17)", "12": "12th grade (age 17–18)",
}

_ADAPTATION_SYSTEM = """You are Adeline's language-and-scaffolding editor.
You receive one block from an already-authored family lesson. Adjust only the
wording for the named learner; never redesign or replace the lesson.

Non-negotiable rules:
- Preserve the block's facts, dates, names, quotations, sources, central question,
  shared family experience, and real project.
- Preserve every family age role. Emphasize the requesting learner's role without
  deleting the responsibilities available to siblings.
- Adjust vocabulary, sentence length, examples, independence, and scaffolding only.
- Do not invent facts, activities, questions, formats, widgets, quizzes, cards,
  slides, animations, metadata, or internal rendering instructions.
- Never expose GENUI notes, system prompts, or implementation language.
- Adeline is the mentor. Never call the learner Adeline.
- Use HaShem or YHWH rather than God when a divine name is needed.
- Return only the complete revised block. Never truncate a sentence.
- Write naturally for a smart learner at the kitchen table; no filler or busywork.
"""

_STRUCTURE_OWNING_TYPES = frozenset({
    "PRIMARY_SOURCE", "EXPERIMENT", "GENUI_ASSEMBLY", "QUIZ", "FLASHCARD",
    "MIND_MAP", "TIMELINE", "MNEMONIC", "BOOK_SUGGESTION",
})


@dataclass
class AdaptationRequest:
    grade_level: str
    track: str
    interests: list[str] = field(default_factory=list)
    interaction_count: int = 10
    recent_quiz_scores: list[float] = field(default_factory=list)
    preferred_modality: str = "text"
    bkt_pL: float = 0.1
    bkt_pT: float = 0.15
    priority_score: float = 0.5
    decay_adjusted_mastery: float = 0.0
    cross_track_bias: float = 0.0
    proficiency_map: dict[str, float] = field(default_factory=dict)


async def _llm_call(system: str, user: str, max_tokens: int = 1400) -> str:
    """Use the configured synthesis provider, returning an empty string on failure."""
    from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL

    if GEMINI_API_KEY:
        import openai

        client = openai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=GEMINI_MODEL,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return response.choices[0].message.content or ""
            except Exception as error:
                if attempt == 0:
                    logger.warning("[Adapter] Gemini retry after failure: %s", error)
                    await asyncio.sleep(1)
                else:
                    logger.warning("[Adapter] Gemini adaptation failed: %s", error)
    return ""


def sanitize_learner_text(content: str) -> str:
    """Remove internal notes and enforce learner-facing identity conventions."""
    cleaned = re.sub(r"\[\s*GENUI\s+hint:[\s\S]*?\]", "", content, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bGod\b", "HaShem", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(your)\s+(job|task|role)\s*,?\s*Adeline\s*,?\s*(is|will be|is to)\b",
        r"\1 \2 \3", cleaned, flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bAdeline\s*,\s*(your\s+(?:job|task|role)\b)",
        r"\1", cleaned, flags=re.IGNORECASE,
    )
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def build_adaptation_prompt(req: AdaptationRequest, content: str, topic_hint: str = "") -> str:
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    interests = ", ".join(req.interests[:4]) if req.interests else "the lesson itself"

    if req.bkt_pL < 0.30:
        scaffolding = "Use concrete language and explain difficult terms inline. Keep all facts and family roles."
    elif req.bkt_pL >= 0.65:
        scaffolding = "Keep subject vocabulary and nuance; invite greater independence in this learner's role."
    else:
        scaffolding = "Explain specialist vocabulary naturally and keep the learner's responsibility challenging but reachable."

    return (
        f"Topic: {topic_hint or 'the current family lesson'}\n"
        f"Learner: {grade_desc}; track: {req.track.replace('_', ' ').title()}; "
        f"interests: {interests}; mastery: {req.bkt_pL:.2f}.\n"
        f"Scaffolding: {scaffolding}\n\n"
        "Revise the wording only. Preserve the complete lesson block and all shared-family roles.\n\n"
        f"ORIGINAL BLOCK:\n{content}"
    )


async def adapt_block_content(content: str, req: AdaptationRequest, topic_hint: str = "") -> str:
    result = await _llm_call(_ADAPTATION_SYSTEM, build_adaptation_prompt(req, content, topic_hint))
    return sanitize_learner_text(result if result.strip() else content)


async def _adapt_block(block: dict, req: AdaptationRequest, topic_hint: str) -> dict:
    adapted = dict(block)
    block_type = str(block.get("block_type") or "NARRATIVE").upper()
    content = str(block.get("content") or "")

    # Structured and source blocks own exact content/data. Changing their prose
    # without changing their props creates mismatched, broken lessons.
    if block_type not in _STRUCTURE_OWNING_TYPES and content.strip():
        adapted["content"] = await adapt_block_content(content, req, topic_hint)

    # Structural invariance is the contract of this adapter.
    adapted["block_type"] = block_type
    return adapted


async def adapt_canonical_for_student(canonical: dict, req: AdaptationRequest) -> list[dict]:
    """Adapt wording in parallel while preserving block count, order, and types."""
    blocks = list(canonical.get("blocks") or [])
    if not blocks:
        return []

    topic_hint = str(canonical.get("topic") or "")
    adapted = await asyncio.gather(*(
        _adapt_block(block, req, topic_hint) for block in blocks
    ))
    logger.info(
        "[Adapter] Adapted wording for %d canonical blocks (grade=%s track=%s); structure unchanged",
        len(adapted), req.grade_level, req.track,
    )
    return list(adapted)
