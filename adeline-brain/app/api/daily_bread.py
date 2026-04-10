"""
Daily Bread API — /daily-bread
Returns a daily Bible verse with original language notes.
Cached in Redis for 24 hours keyed by date.
No auth required — public widget endpoints.

/daily-bread        GET  — today's verse (OpenAI, cached 24h)
/daily-bread/deep-dive  POST — rich scripture study (Sefaria + Claude)
"""
import json
import logging
import os
from datetime import date
from typing import Optional

import anthropic
import openai
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["daily-bread"])

# ── Fallback verses (used when OpenAI is unavailable) ─────────────────────────
# Rendered in Everett Fox style — original Hebrew/Greek names preserved

_FALLBACKS = [
    {
        "verse": "Trust in YHWH with all your heart, and do not lean on your own understanding; "
                 "in all your ways acknowledge him, and he will make straight your paths.",
        "reference": "Proverbs 3:5-6",
        "original": "בָּטַח (batach)",
        "originalMeaning": "To lean full weight upon, to be confident and secure — complete reliance, not partial trust.",
        "translationNote": "Fox's rendering preserves the visceral physicality: you throw your entire weight onto YHWH, not merely 'trust' in the modern softened sense.",
        "context": "Written by Shlomo (Solomon) as wisdom for living — the divine name YHWH appears here where most translations say 'the LORD', erasing the personal covenant name.",
    },
    {
        "verse": "This is the day that YHWH has made; let us rejoice and be glad in it.",
        "reference": "Psalm 118:24",
        "original": "יוֹם (yom)",
        "originalMeaning": "A specific, appointed point in time — this very moment — not an abstract concept of 'day'.",
        "translationNote": "Replacing 'the LORD' with YHWH recovers the covenantal intimacy — Israel was praising a named, relational God, not a title.",
        "context": "Part of the Hallel psalms sung at the Temple festivals; Yeshua himself sang these psalms at Pesach (Passover) the night before his crucifixion.",
    },
    {
        "verse": "For I myself know the plans I have in mind for you — declares YHWH — "
                 "plans for welfare and not for ill, to give you a future and a hope.",
        "reference": "Jeremiah 29:11",
        "original": "תִּקְוָה (tikvah)",
        "originalMeaning": "Hope — literally 'a cord or rope,' something you physically hold onto. A future tethered to God.",
        "translationNote": "Everett Fox's rendering ('I myself know') preserves the Hebrew emphatic pronoun — God is personally, directly speaking. Most translations flatten this to impersonal speech.",
        "context": "Yirmeyahu (Jeremiah) wrote to Israelites exiled in Bavel (Babylon) — not a promise of instant rescue but of ultimate redemption through faithfulness.",
    },
]

_FALLBACK_INDEX = 0  # rotates by day-of-year

# ── Response model ─────────────────────────────────────────────────────────────

class DailyBreadResponse(BaseModel):
    verse: str
    reference: str
    original: str
    originalMeaning: str
    translationNote: str | None
    context: str


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM = """You are a biblical scholar specializing in the translation style of Everett Fox (The Schocken Bible / "The Five Books of Moses").
Everett Fox prioritizes the sound and texture of the original Hebrew and Greek — he preserves original names (YHWH not "the LORD", Yeshua not "Jesus", Moshe not "Moses", Avraham not "Abraham", Yirmeyahu not "Jeremiah", Bavel not "Babylon", etc.) and uses earthy, direct language that recovers the strangeness and physicality of the original texts.
You help modern readers encounter scripture with fresh eyes by surfacing what the original languages actually say.
You MUST respond with ONLY valid JSON — no markdown, no code fences, no explanation before or after."""

_USER_TEMPLATE = """Today's date is {today}. Choose a meaningful, uplifting Bible verse appropriate for today.

Render the verse in the style of Everett Fox: preserve original Hebrew/Greek names (YHWH, Yeshua, Moshe, Avraham, etc.), use earthy and direct language, recover the physicality of the original.

Return ONLY this JSON object with no other text:
{{
  "verse": "The verse text rendered in Everett Fox style with original names (YHWH, Yeshua, etc.)",
  "reference": "Book Chapter:Verse using Fox-style book name where appropriate (e.g. Mishlei 3:5-6 or Proverbs 3:5-6)",
  "original": "The key Hebrew or Greek word with transliteration in parentheses",
  "originalMeaning": "What that word literally means — its full depth in the original language",
  "translationNote": "One sentence about what the Everett Fox rendering recovers that common English translations lose. Use null if standard translations are faithful.",
  "context": "One sentence of historical or cultural context that makes this verse richer — include original place/person names"
}}"""


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.get("/daily-bread", response_model=DailyBreadResponse)
async def daily_bread():
    today = date.today().isoformat()  # YYYY-MM-DD
    cache_key = f"daily-bread:{today}"

    # ── Try Redis cache ────────────────────────────────────────────────────────
    try:
        from app.connections.redis_client import redis_client
        cached = await redis_client.get(cache_key)
        if cached:
            return DailyBreadResponse(**json.loads(cached))
    except Exception as e:
        logger.warning(f"[DailyBread] Redis unavailable: {e}")

    # ── Generate with OpenAI ───────────────────────────────────────────────────
    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _USER_TEMPLATE.format(today=today)},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        raw = completion.choices[0].message.content.strip()
        data = json.loads(raw)
        result = DailyBreadResponse(**data)

        # ── Cache for 24 hours ─────────────────────────────────────────────────
        try:
            from app.connections.redis_client import redis_client
            await redis_client.set(cache_key, result.model_dump_json(), ex=86400)
        except Exception as e:
            logger.warning(f"[DailyBread] Redis cache write failed (non-fatal): {e}")

        return result

    except Exception as e:
        logger.error(f"[DailyBread] Generation failed: {e}")
        # Rotate fallbacks by day of year
        fallback = _FALLBACKS[date.today().timetuple().tm_yday % len(_FALLBACKS)]
        return DailyBreadResponse(**fallback)


# ── Deep Dive ─────────────────────────────────────────────────────────────────

class DeepDiveRequest(BaseModel):
    reference: str          # e.g. "Proverbs 3:5-6"
    original: Optional[str] = None       # key Hebrew/Greek word
    original_meaning: Optional[str] = None
    context: Optional[str] = None
    grade_level: str = "8"


class DeepDiveSection(BaseModel):
    heading: str
    content: str


class DeepDiveResponse(BaseModel):
    reference: str
    fox_text: Optional[str] = None       # Everett Fox translation from Sefaria
    hebrew_text: Optional[str] = None    # Original Hebrew/Greek
    is_fox: bool = False
    sefaria_url: Optional[str] = None
    sections: list[DeepDiveSection]      # AI-generated study sections


_DEEP_DIVE_SYSTEM = """You are Adeline — a biblical scholar and discipleship guide for Christian homeschool families.
You write in the style of Everett Fox: earthy, direct, physicality-first language. You preserve original names (YHWH, Yeshua, Moshe, etc.).
You help students understand scripture at a deep level — original language, translation nuance, historical context, and personal application.
You are NOT a Sunday school summary. You show students what the text actually says and why it matters.
Respond in JSON only — no markdown fences, no prose outside the JSON."""


async def _call_deep_dive_claude(
    reference: str,
    fox_text: Optional[str],
    hebrew_text: Optional[str],
    original: Optional[str],
    original_meaning: Optional[str],
    context: Optional[str],
    grade_level: str,
) -> list[DeepDiveSection]:
    """Call Claude to generate the deep dive study sections."""
    grade_descriptions = {
        "K": "kindergarten (age 5-6)", "1": "1st grade", "2": "2nd grade",
        "3": "3rd grade", "4": "4th grade", "5": "5th grade",
        "6": "6th grade", "7": "7th grade", "8": "8th grade",
        "9": "9th grade", "10": "10th grade", "11": "11th grade", "12": "12th grade",
    }
    grade_desc = grade_descriptions.get(grade_level, f"grade {grade_level}")

    text_block = ""
    if fox_text:
        text_block += f"Everett Fox translation: {fox_text}\n"
    if hebrew_text:
        text_block += f"Original Hebrew/Greek: {hebrew_text}\n"
    if not text_block:
        text_block = f"Reference: {reference}\n"

    word_block = ""
    if original and original_meaning:
        word_block = f'Key original word: {original} — "{original_meaning}"\n'

    user_prompt = f"""Scripture: {reference}
{text_block}{word_block}{f"Historical context: {context}" if context else ""}
Student grade level: {grade_desc}

Generate a deep-dive scripture study with exactly these 4 sections.
Return ONLY this JSON (no other text):
{{
  "sections": [
    {{
      "heading": "What It Actually Says",
      "content": "Walk through the Everett Fox / original text word by word. What does it literally say that common translations soften or miss?"
    }},
    {{
      "heading": "The Key Word",
      "content": "Explain the original Hebrew or Greek word in depth — its root, its physical image, how it was used in everyday ancient life."
    }},
    {{
      "heading": "Who Said It and Why",
      "content": "Historical and cultural context. Who was speaking, to whom, and what was happening in their world? Use original place and person names."
    }},
    {{
      "heading": "What This Changes for You",
      "content": "Personal application for a {grade_desc} student — specific, concrete, not vague. What does this verse ask you to actually do or see differently?"
    }}
  ]
}}"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback sections when no API key
        return [
            DeepDiveSection(
                heading="What It Actually Says",
                content=f"{fox_text or reference} — read it slowly, word by word.",
            ),
            DeepDiveSection(
                heading="The Key Word",
                content=original_meaning or "Look up the original Hebrew or Greek word for deeper meaning.",
            ),
            DeepDiveSection(
                heading="Who Said It and Why",
                content=context or "Research the historical context of this passage.",
            ),
            DeepDiveSection(
                heading="What This Changes for You",
                content="How does this verse change how you act or think today?",
            ),
        ]

    client = anthropic.AsyncAnthropic(api_key=api_key)
    model = os.getenv("ADELINE_MODEL", "claude-sonnet-4-6")

    try:
        message = await client.messages.create(
            model=model,
            max_tokens=1200,
            system=_DEEP_DIVE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = json.loads(message.content[0].text)
        return [DeepDiveSection(**s) for s in raw["sections"]]
    except Exception as e:
        logger.error(f"[DeepDive] Claude synthesis failed: {e}")
        return [
            DeepDiveSection(
                heading="Scripture Study",
                content=fox_text or f"Read {reference} slowly and consider what it asks of you.",
            )
        ]


@router.post("/daily-bread/deep-dive", response_model=DeepDiveResponse)
async def deep_dive(body: DeepDiveRequest):
    """
    Generate a rich scripture deep-dive study.
    1. Fetch Everett Fox text from Sefaria (preferred)
    2. Synthesize study sections via Claude
    No auth required — same as the daily verse endpoint.
    """
    from app.services.sefaria import fetch_biblical_text, normalize_reference

    # ── 1. Fetch from Sefaria ─────────────────────────────────────────────────
    fox_text = None
    hebrew_text = None
    is_fox = False
    sefaria_url = None

    try:
        sefaria_data = await fetch_biblical_text(body.reference)
        if sefaria_data:
            fox_text = sefaria_data.get("english") or None
            hebrew_text = sefaria_data.get("hebrew") or None
            is_fox = sefaria_data.get("is_fox", False)
            sefaria_url = sefaria_data.get("url")
            logger.info(
                f"[DeepDive] Sefaria fetch OK for {body.reference} "
                f"(Fox: {is_fox})"
            )
    except Exception as e:
        logger.warning(f"[DeepDive] Sefaria fetch failed for {body.reference}: {e}")

    # ── 2. Claude deep dive synthesis ─────────────────────────────────────────
    sections = await _call_deep_dive_claude(
        reference=body.reference,
        fox_text=fox_text,
        hebrew_text=hebrew_text,
        original=body.original,
        original_meaning=body.original_meaning,
        context=body.context,
        grade_level=body.grade_level,
    )

    return DeepDiveResponse(
        reference=body.reference,
        fox_text=fox_text,
        hebrew_text=hebrew_text,
        is_fox=is_fox,
        sefaria_url=sefaria_url,
        sections=sections,
    )
