"""
Daily Bread API — /daily-bread
Returns a daily Bible verse with original language notes.
Cached in Redis for 24 hours keyed by date.
No auth required — public widget endpoint.
"""
import json
import logging
import os
from datetime import date

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
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"[DailyBread] Generation failed: {e}")
        # Rotate fallbacks by day of year
        fallback = _FALLBACKS[date.today().timetuple().tm_yday % len(_FALLBACKS)]
        return DailyBreadResponse(**fallback)
