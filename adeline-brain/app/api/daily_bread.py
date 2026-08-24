"""
Daily Bread API — /daily-bread
Returns a daily source-text Bible study with explicitly labeled translation layers.
Cached in Redis for 24 hours keyed by date.
No auth required — public widget endpoints.

/daily-bread        GET  — today's verse (OpenAI, cached 24h)
/daily-bread/deep-dive  POST — rich scripture study (Sefaria + Claude)
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GOOGLE_API_KEY,
)
from app.agents.persona import SCRIPTURE_TRANSLATION_POLICY

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
        "originalMeaning": "To trust, rely on, or feel secure. The separate verb in the next phrase, tisha'en, means to lean or support oneself; those images should not be collapsed into one word.",
        "translationNote": "The Hebrew names YHWH rather than saying 'the LORD'; verse 6 literally says 'know him in all your ways,' which many English versions interpret as 'acknowledge him.'",
        "context": "Written by Shlomo (Solomon) as wisdom for living — the divine name YHWH appears here where most translations say 'the LORD', erasing the personal covenant name.",
        "originalText": "בְּטַח אֶל־יְהוָה בְּכָל־לִבֶּךָ וְאֶל־בִּינָתְךָ אַל־תִּשָּׁעֵן׃ בְּכָל־דְּרָכֶיךָ דָעֵהוּ וְהוּא יְיַשֵּׁר אֹרְחֹתֶיךָ׃",
        "translationLabel": "Close rendering from the Masoretic Hebrew source text",
    },
    {
        "verse": "This is the day that YHWH has made; let us rejoice and be glad in it.",
        "reference": "Psalm 118:24",
        "original": "יוֹם (yom)",
        "originalMeaning": "Day. In this thanksgiving psalm, the surrounding context may point to the day of YHWH's deliverance or victory; the noun by itself does not mean 'appointed moment.'",
        "translationNote": "The Hebrew names YHWH rather than using the substitute title 'the LORD.' The surrounding song of deliverance matters more than treating the line as a generic slogan about every day.",
        "context": "Part of the Hallel psalms sung at the Temple festivals; Yeshua himself sang these psalms at Pesach (Passover) the night before his crucifixion.",
        "originalText": "זֶה־הַיּוֹם עָשָׂה יְהוָה נָגִילָה וְנִשְׂמְחָה בוֹ׃",
        "translationLabel": "Close rendering from the Masoretic Hebrew source text",
    },
    {
        "verse": "For I myself know the plans I have in mind for you — declares YHWH — "
                 "plans for welfare and not for ill, to give you a future and a hope.",
        "reference": "Jeremiah 29:11",
        "original": "תִּקְוָה (tikvah)",
        "originalMeaning": "Hope or expectation. The same spelling can refer to a cord in another context, but 'cord' is not the intended lexical sense in this sentence.",
        "translationNote": "The Hebrew has an emphatic anokhi ('I myself'), names YHWH, and uses machashavot ('thoughts, intentions, plans') and shalom ('well-being, wholeness, peace') rather than promising immediate individual prosperity.",
        "context": "Yirmeyahu (Jeremiah) wrote to Israelites exiled in Bavel (Babylon) — not a promise of instant rescue but of ultimate redemption through faithfulness.",
        "originalText": "כִּי אָנֹכִי יָדַעְתִּי אֶת־הַמַּחֲשָׁבֹת אֲשֶׁר אָנֹכִי חֹשֵׁב עֲלֵיכֶם נְאֻם־יְהוָה מַחְשְׁבוֹת שָׁלוֹם וְלֹא לְרָעָה לָתֵת לָכֶם אַחֲרִית וְתִקְוָה׃",
        "translationLabel": "Close rendering from the Masoretic Hebrew source text",
    },
]

_FALLBACK_INDEX = 0  # rotates by day-of-year


def _json_object(content) -> dict:
    """Decode Gemini/LangChain text whether returned as text or content blocks."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if value:
                    parts.append(str(value))
        text = "\n".join(parts)
    else:
        text = str(content or "")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Gemini response did not contain a JSON object")
    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response JSON was not an object")
    return parsed


async def _gemini_json(system_prompt: str, user_prompt: str, *, max_tokens: int, temperature: float = 0.2) -> dict:
    """Use the same explicit Gemini JSON path as canonical lesson authoring."""
    import openai

    key = GEMINI_API_KEY or GOOGLE_API_KEY
    if not key:
        raise RuntimeError("Gemini is not configured")
    client = openai.AsyncOpenAI(api_key=key, base_url=GEMINI_BASE_URL)
    completion = await client.chat.completions.create(
        model=GEMINI_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return _json_object(completion.choices[0].message.content or "")


def _complete_lesson(data: dict) -> dict:
    """Guarantee a useful family lesson even when generation is unavailable."""
    reference = data.get("reference", "today's passage")
    data.setdefault("lessonTitle", f"Living {reference}")
    data.setdefault("bigIdea", "Receive the text in its real context, then put its truth into practice today.")
    data.setdefault("readTogether", [reference, f"Read the verses immediately before and after {reference} to see the larger thought."])
    data.setdefault("familyDiscussion", [
        "What words, images, or repeated ideas do you notice in the passage?",
        "What would the first hearers have understood from this passage that a modern reader might miss?",
        "What is one specific action a younger child, an older student, and an adult could each take because of this truth?",
    ])
    data.setdefault("prayer", "YHWH, help us hear your words truthfully and live them faithfully. Amen.")
    data.setdefault("creditConnections", ["DISCIPLESHIP", "ENGLISH_LITERATURE"])
    data.setdefault("portfolioEvidence", ["Record a spoken, written, drawn, or photographed response that explains the passage and documents how it was practiced."])
    if not data.get("readTogether"):
        data["readTogether"] = [reference, f"Read the verses immediately before and after {reference} to see the larger thought."]
    if not data.get("familyDiscussion"):
        data["familyDiscussion"] = [
            "What words, images, or repeated ideas do you notice in the passage?",
            "What did this mean to its first hearers?",
            "What will we do differently today because of it?",
        ]
    if not data.get("portfolioEvidence"):
        data["portfolioEvidence"] = ["Record an authentic response that explains the passage and documents how it was practiced."]
    return data

# ── Response model ─────────────────────────────────────────────────────────────

class DailyBreadResponse(BaseModel):
    forDate: str
    verse: str  # close, name-preserving rendering; never an unlabeled modern-version fallback
    reference: str
    original: str
    originalMeaning: str
    translationNote: str | None
    context: str
    lessonTitle: str = "Daily Bread"
    bigIdea: str = "Receive the text, understand it in context, and live it today."
    readTogether: list[str] = Field(default_factory=list)
    familyDiscussion: list[str] = Field(default_factory=list)
    sourceTranslation: Optional[str] = None
    translationLabel: str = "Close rendering from the source text"
    prayer: str = "YHWH, give us ears to hear and courage to obey. Amen."
    creditConnections: list[str] = Field(default_factory=lambda: ["DISCIPLESHIP", "ENGLISH_LITERATURE"])
    portfolioEvidence: list[str] = Field(default_factory=lambda: ["A spoken, written, drawn, or photographed response showing what the learner understood and practiced"])
    originalText: Optional[str] = None
    sourceVersion: Optional[str] = None
    sourceUrl: Optional[str] = None
    isFoxTranslation: bool = False


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM = f"""You are a careful source-text biblical scholar for Christian homeschool families.
{SCRIPTURE_TRANSLATION_POLICY}
For Daily Bread, select a passage from the Hebrew Bible because the current source adapter can verify its Hebrew text. Produce a close English rendering, not a quotation falsely attributed to a published translation. Keep YHWH and meaningful Hebrew names or terms rather than substituting LORD, God, or modernized personal names. Explain unfamiliar terms separately.
You MUST respond with ONLY valid JSON — no markdown, no code fences, no explanation before or after."""

_USER_TEMPLATE = """Today's date is {today}. Choose a meaningful Bible passage appropriate for today.
Do not repeat any of these recently used references: {recent_references}.

Render the passage closely from Hebrew in a sound-conscious manner. Preserve YHWH, Elohim, and original personal/place names when those forms are present. Do not silently quote a modern English version and do not claim your rendering is Everett Fox.

Return ONLY this JSON object with no other text:
{{
  "verse": "A close English rendering preserving source-language names and concrete imagery",
  "reference": "Book Chapter:Verse using Fox-style book name where appropriate (e.g. Mishlei 3:5-6 or Proverbs 3:5-6)",
  "original": "The key Hebrew or Greek word with transliteration in parentheses",
  "originalMeaning": "What that word literally means — its full depth in the original language",
  "translationNote": "Identify what common renderings add, remove, flatten, or obscure. Distinguish translation choice from a documented textual variant. Use null if there is no meaningful issue.",
  "context": "One sentence of historical or cultural context that makes this verse richer — include original place/person names",
  "lessonTitle": "A short, inviting family Bible lesson title",
  "bigIdea": "The central truth of the passage in one clear sentence",
  "readTogether": ["The main reference", "One nearby passage that clarifies its context"],
  "familyDiscussion": ["An observation question", "A context or meaning question", "A concrete application question with layered answers for different ages"],
  "prayer": "A brief prayer rooted in the actual passage",
  "creditConnections": ["DISCIPLESHIP", "Add ENGLISH_LITERATURE, TRUTH_HISTORY, or another track only when the lesson genuinely demonstrates it"],
  "portfolioEvidence": ["One or two authentic evidence options: spoken explanation, written reflection, drawing, photo of practice, or source comparison"]
}}"""


async def _ground_close_rendering(reference: str, source_text: str) -> str | None:
    """Create a labeled close rendering only after the source text is available."""
    if not GOOGLE_API_KEY or not source_text.strip():
        return None
    prompt = f"""Reference: {reference}
Surviving Masoretic Hebrew source text:
{source_text}

Return JSON only: {{"rendering":"..."}}
Translate closely into readable English. Preserve YHWH, Elohim, and source-language personal/place names rather than replacing them with LORD, God, Jesus, or Anglicized forms. Preserve repetition and concrete imagery. Do not add interpretation inside the rendering. Do not attribute this rendering to Everett Fox or any published translator."""
    try:
        response = await _gemini_json(_SYSTEM, prompt, max_tokens=2048, temperature=0.1)
        return str(response["rendering"]).strip() or None
    except Exception as exc:
        logger.warning("[DailyBread] grounded close rendering failed: %s", exc)
        return None


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.get("/daily-bread", response_model=DailyBreadResponse)
async def daily_bread(response: Response):
    # The family experiences a day in Central time; Railway's server timezone is UTC.
    today_date = datetime.now(ZoneInfo("America/Chicago")).date()
    today = today_date.isoformat()
    cache_key = f"daily-bread:v5:{today}"
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Vary"] = "Accept-Encoding"

    # The current day is the hot path. Return it before reading 14 historical
    # keys; history is needed only when a new study must be generated.
    try:
        from app.connections.redis_client import redis_client
        cached = await redis_client.get(cache_key)
        if cached:
            cached_data = json.loads(cached)
            cached_data["forDate"] = today
            return DailyBreadResponse(**cached_data)
    except Exception as e:
        logger.warning(f"[DailyBread] Redis unavailable: {e}")

    recent_references: list[str] = []
    try:
        from app.connections.redis_client import redis_client
        for offset in range(1, 15):
            prior_day = (today_date - timedelta(days=offset)).isoformat()
            prior = await redis_client.get(f"daily-bread:v5:{prior_day}") or await redis_client.get(f"daily-bread:v4:{prior_day}")
            if prior:
                reference = json.loads(prior).get("reference")
                if reference and reference not in recent_references:
                    recent_references.append(reference)
    except Exception as exc:
        logger.warning("[DailyBread] recent-reference history unavailable: %s", exc)

    # ── Generate with Gemini ───────────────────────────────────────────────────
    try:
        data = await _gemini_json(
            _SYSTEM,
            _USER_TEMPLATE.format(
                today=today,
                recent_references=", ".join(recent_references) or "none",
            ),
            max_tokens=4096,
            temperature=0.7,
        )
        if data.get("reference") in recent_references:
            # The model may ignore exclusions. Enforce rotation rather than
            # presenting yesterday's study under today's date.
            data = dict(next(
                (item for item in _FALLBACKS if item.get("reference") not in recent_references),
                _FALLBACKS[today_date.timetuple().tm_yday % len(_FALLBACKS)],
            ))
        # Sefaria is the source of record for Hebrew-Bible text. Gemini builds
        # the lesson but does not get to invent or silently paraphrase the text.
        try:
            from app.services.sefaria import fetch_biblical_text
            source = await fetch_biblical_text(data["reference"])
            if source:
                data["reference"] = source.get("ref") or data["reference"]
                data["originalText"] = source.get("hebrew") or None
                data["sourceVersion"] = source.get("version_title") or "Sefaria"
                data["sourceUrl"] = source.get("url")
                data["isFoxTranslation"] = bool(source.get("is_fox"))
                # Published English is a labeled comparison, never a silent replacement
                # for the close, original-name-preserving rendering.
                if source.get("is_fox") and source.get("english"):
                    data["sourceTranslation"] = source["english"]
                grounded = await _ground_close_rendering(data["reference"], source.get("hebrew") or "")
                if grounded:
                    data["verse"] = grounded
                    data["translationLabel"] = "Close rendering from the Masoretic Hebrew source text"
                elif source.get("is_fox") and source.get("english"):
                    data["verse"] = source["english"]
                    data["translationLabel"] = "Everett Fox published translation"
                else:
                    data["verse"] = "A close English rendering is temporarily unavailable. Read the source text shown in the lesson."
                    data["translationLabel"] = "Source text available; close rendering unavailable"
            else:
                data["verse"] = "The source text could not be verified right now. Daily Bread will not substitute an unlabeled modern rendering."
                data["translationLabel"] = "Source verification unavailable"
        except Exception as source_error:
            logger.warning(f"[DailyBread] Sefaria source fetch failed (non-fatal): {source_error}")
            data["verse"] = "The source text could not be verified right now. Daily Bread will not substitute an unlabeled modern rendering."
            data["translationLabel"] = "Source verification unavailable"
        data["forDate"] = today
        result = DailyBreadResponse(**_complete_lesson(data))

        # ── Cache for 24 hours ─────────────────────────────────────────────────
        try:
            from app.connections.redis_client import redis_client
            # Keyed by the local calendar date; TTL is cleanup, not selection logic.
            await redis_client.set(cache_key, result.model_dump_json(), ex=60 * 60 * 48)
        except Exception as e:
            logger.warning(f"[DailyBread] Redis cache write failed (non-fatal): {e}")

        return result

    except Exception as e:
        logger.error(f"[DailyBread] Generation failed: {e}")
        # Rotate fallbacks by day of year
        fallback = dict(_FALLBACKS[today_date.timetuple().tm_yday % len(_FALLBACKS)])
        fallback["forDate"] = today
        return DailyBreadResponse(**_complete_lesson(fallback))


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
    direct_translation: Optional[str] = None
    source_version: Optional[str] = None
    sefaria_url: Optional[str] = None
    sections: list[DeepDiveSection]      # AI-generated study sections


_DEEP_DIVE_SYSTEM = f"""You are Adeline — a careful source-text biblical scholar and discipleship guide for Christian homeschool families.
{SCRIPTURE_TRANSLATION_POLICY}
Never call a generated rendering "Everett Fox." Fox is shown only when the source service actually returns that published version. Never claim intentional alteration without manuscript or translation-history evidence identifying the reading, date, people or institution, and evidence. Label documented facts, scholarly dispute, and unknowns separately.
Respond in JSON only — no markdown fences, no prose outside the JSON."""


async def _build_deep_dive_study(
    reference: str,
    fox_text: Optional[str],
    hebrew_text: Optional[str],
    original: Optional[str],
    original_meaning: Optional[str],
    context: Optional[str],
    grade_level: str,
) -> tuple[str | None, list[DeepDiveSection]]:
    """Build a source-grounded close rendering and study sections."""
    grade_descriptions = {
        "K": "kindergarten (age 5-6)", "1": "1st grade", "2": "2nd grade",
        "3": "3rd grade", "4": "4th grade", "5": "5th grade",
        "6": "6th grade", "7": "7th grade", "8": "8th grade",
        "9": "9th grade", "10": "10th grade", "11": "11th grade", "12": "12th grade",
    }
    grade_desc = grade_descriptions.get(grade_level, f"grade {grade_level}")

    text_block = ""
    if fox_text:
        text_block += f"Published English source comparison: {fox_text}\n"
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

First produce a close English rendering from the supplied source text. Preserve YHWH, Elohim, Yeshua and original names when applicable; do not substitute LORD, God, Jesus, or Anglicized names inside the rendering. Then generate exactly these 4 study sections.
Return ONLY this JSON (no other text):
{{
  "direct_translation": "Close English rendering grounded in the supplied source text; original names retained",
  "sections": [
    {{
      "heading": "What the Source Text Says",
      "content": "Walk through the original wording and close rendering. Separate lexical range from interpretation."
    }},
    {{
      "heading": "The Key Word",
      "content": "Explain the original Hebrew or Greek word in depth — its root, its physical image, how it was used in everyday ancient life."
    }},
    {{
      "heading": "Context and Intended Meaning",
      "content": "Historical and cultural context. Who was speaking, to whom, and what was happening in their world? Use original place and person names."
    }},
    {{
      "heading": "Translation and Textual History",
      "content": "Compare important translation choices. If the supplied evidence does not include a textual apparatus or identifiable manuscripts, explicitly say that intentional alteration cannot be determined here. If evidence documents a variant or later alteration, identify the manuscripts/readings, approximate dates, provenance, and evidence. Separate documented change from disputed motive; never invent who changed it or why."
    }}
  ]
}}"""

    fallback_sections = [
            DeepDiveSection(
                heading="What the Source Text Says",
                content=f"{hebrew_text or reference} — read the surviving source wording slowly and distinguish it from later interpretation.",
            ),
            DeepDiveSection(
                heading="The Key Word",
                content=original_meaning or "Look up the original Hebrew or Greek word for deeper meaning.",
            ),
            DeepDiveSection(
                heading="Context and Intended Meaning",
                content=context or "Research the historical context of this passage.",
            ),
            DeepDiveSection(
                heading="Translation and Textual History",
                content="Compare named translations with the source wording. Record only documented variants or changes; label disputed claims and unknown motives honestly.",
            ),
        ]
    if not hebrew_text or not GOOGLE_API_KEY:
        return None, fallback_sections

    try:
        raw = await _gemini_json(
            _DEEP_DIVE_SYSTEM, user_prompt, max_tokens=4096, temperature=0.2,
        )
        return raw.get("direct_translation"), [DeepDiveSection(**s) for s in raw["sections"]]
    except Exception as e:
        logger.error(f"[DeepDive] LLM synthesis failed: {e}")
        return None, fallback_sections


@router.post("/daily-bread/deep-dive", response_model=DeepDiveResponse)
async def deep_dive(body: DeepDiveRequest):
    """
    Generate a rich scripture deep-dive study.
    1. Fetch Everett Fox text from Sefaria (preferred)
    2. Build source-grounded study sections with Gemini
    No auth required — same as the daily verse endpoint.
    """
    from app.services.sefaria import fetch_biblical_text

    # ── 1. Fetch from Sefaria ─────────────────────────────────────────────────
    fox_text = None
    hebrew_text = None
    is_fox = False
    sefaria_url = None
    source_version = None

    try:
        sefaria_data = await fetch_biblical_text(body.reference)
        if sefaria_data:
            fox_text = sefaria_data.get("english") or None
            hebrew_text = sefaria_data.get("hebrew") or None
            is_fox = sefaria_data.get("is_fox", False)
            sefaria_url = sefaria_data.get("url")
            source_version = sefaria_data.get("version_title") or None
            logger.info(
                f"[DeepDive] Sefaria fetch OK for {body.reference} "
                f"(Fox: {is_fox})"
            )
    except Exception as e:
        logger.warning(f"[DeepDive] Sefaria fetch failed for {body.reference}: {e}")

    # ── 2. Source-grounded deep dive synthesis ────────────────────────────────
    direct_translation, sections = await _build_deep_dive_study(
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
        direct_translation=direct_translation,
        source_version=source_version,
        sefaria_url=sefaria_url,
        sections=sections,
    )
