"""
Adaptation Layer — transforms a CanonicalLesson for a specific student.

This is the cheap pass: a fast model (Gemini Flash or Claude Haiku) rewrites
content blocks from adult/HS level down to the student's grade and persona.
No research, no Witness Protocol, no Hippocampus — just distillation.

Cost: ~1 LLM call at 500-800 tokens vs 3-8 calls at 2000+ tokens for full generation.
"""
import json
import logging
import os
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

_ADAPTATION_SYSTEM = """You are Adeline's adaptation engine. You receive a lesson written at adult/high school depth.
Your job is to rewrite it for a specific student. Rules:
- Keep every fact, date, name, and quote. Never invent or remove verified content.
- Adjust vocabulary and sentence complexity only.
- Do NOT add busywork, "great job!", or filler.
- Return ONLY the rewritten content block — no preamble, no explanation.
- Write like you're talking to a smart kid at the kitchen table, not lecturing."""


@dataclass
class AdaptationRequest:
    grade_level:       str
    track:             str
    interests:         list[str] = field(default_factory=list)
    interaction_count: int = 10


def build_adaptation_prompt(req: AdaptationRequest, content: str) -> str:
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    interests_str = ", ".join(req.interests) if req.interests else "general learning"

    complexity = (
        "This is their first time in this subject — use introductory language, shorter sentences, "
        "and connect concepts to everyday things."
        if req.interaction_count <= 3
        else "They have some background here — you can use subject vocabulary but explain it naturally."
    )

    return (
        f"Rewrite the following lesson content for a {grade_desc} student "
        f"in the {req.track.replace('_', ' ').title()} curriculum. "
        f"Their interests include: {interests_str}. "
        f"{complexity}\n\n"
        f"ORIGINAL CONTENT:\n{content}"
    )


async def adapt_block_content(content: str, req: AdaptationRequest) -> str:
    """
    Rewrite a single content block for the student's level.
    Uses Gemini Flash if available (cheapest), falls back to Claude Haiku, then Claude Sonnet.
    Returns original content if all LLM calls fail.
    """
    from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL

    user_prompt = build_adaptation_prompt(req, content)

    try:
        if GEMINI_API_KEY:
            import openai as _oai
            client = _oai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
            response = await client.chat.completions.create(
                model=GEMINI_MODEL,
                max_tokens=600,
                messages=[
                    {"role": "system", "content": _ADAPTATION_SYSTEM},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or content

        import anthropic
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",  # cheapest Claude — sufficient for distillation
            max_tokens=600,
            system=[{"type": "text", "text": _ADAPTATION_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_prompt}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        return response.content[0].text

    except Exception as e:
        logger.warning(f"[Adapter] Adaptation failed for block, returning original: {e}")
        return content


async def adapt_canonical_for_student(
    canonical: dict,
    req: AdaptationRequest,
) -> list[dict]:
    """
    Adapt all content blocks in a canonical lesson for the student.
    Preserves block_type, evidence, block_id, and all structured data.
    Only rewrites the `content` field.

    Returns adapted blocks as list[dict] (same shape as LessonBlockResponse).
    """
    import asyncio

    blocks = canonical.get("blocks", [])
    if not blocks:
        return blocks

    # Adapt all content blocks concurrently
    adapted_contents = await asyncio.gather(*[
        adapt_block_content(b.get("content", ""), req)
        for b in blocks
    ])

    adapted_blocks = []
    for block, new_content in zip(blocks, adapted_contents):
        adapted = dict(block)
        adapted["content"] = new_content
        adapted_blocks.append(adapted)

    logger.info(
        f"[Adapter] Adapted {len(adapted_blocks)} blocks for grade={req.grade_level}, "
        f"track={req.track}, interactions={req.interaction_count}"
    )
    return adapted_blocks
