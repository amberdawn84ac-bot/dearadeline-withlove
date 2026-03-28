"""
ZPD Engine — Scaffolding Controller
"The Zone of Proximal Development is the distance between what a student can do
alone and what they can do with guidance." — Vygotsky

This agent evaluates a student's in-session response and determines their ZPD zone,
then generates a pedagogically appropriate reply:

  FRUSTRATED → Bridge Response: connect new concept to a Witness Anchor
               (a primary source from a lesson the student has already mastered)
  BORED      → Elevation Response: surface harder primary sources, add comparison task
  IN_ZPD     → Socratic Response: ask a probing question, keep the student moving

The system prompt is dynamically constructed from the student's live mastery state.
"""
from __future__ import annotations

import os
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import openai

from app.models.student import StudentState, MasteryBand

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL  = "gpt-4o-mini"


# ── ZPD Zone ──────────────────────────────────────────────────────────────────

class ZPDZone(str, Enum):
    FRUSTRATED = "FRUSTRATED"  # Student is stuck — needs a bridge
    IN_ZPD     = "IN_ZPD"     # Student is working — keep guiding
    BORED      = "BORED"      # Student is ahead — increase complexity


# Frustration signal patterns (case-insensitive)
_FRUSTRATION_PATTERNS = re.compile(
    r"i (don'?t|do not) (know|understand|get it)|"
    r"what (does|is|are)|"
    r"i'?m (confused|lost|stuck)|"
    r"i have no idea|"
    r"can you (help|explain)|"
    r"this is (hard|difficult|too much)|"
    r"\bhelp\b|\bwhat\?\b",
    re.IGNORECASE,
)

# Boredom / readiness-to-advance patterns
_BOREDOM_PATTERNS = re.compile(
    r"i (already|know|learned|understand) this|"
    r"(too easy|boring|i got it|can we move on)|"
    r"what'?s next|"
    r"i want (harder|more)",
    re.IGNORECASE,
)

_SHORT_RESPONSE_THRESHOLD = 25  # characters — very short = likely stuck


def detect_zpd_zone(student_response: str) -> ZPDZone:
    """
    Classify the student's response into a ZPD zone.
    Rule-based for speed; can be replaced with embedding classifier later.
    """
    stripped = student_response.strip()

    if _FRUSTRATION_PATTERNS.search(stripped):
        return ZPDZone.FRUSTRATED

    if len(stripped) < _SHORT_RESPONSE_THRESHOLD and not stripped.endswith("?") is False:
        # Very short non-question responses often signal disengagement or confusion
        if len(stripped) < _SHORT_RESPONSE_THRESHOLD:
            return ZPDZone.FRUSTRATED

    if _BOREDOM_PATTERNS.search(stripped):
        return ZPDZone.BORED

    return ZPDZone.IN_ZPD


# ── System Prompt Builder ─────────────────────────────────────────────────────

def _build_system_prompt(
    zone: ZPDZone,
    topic: str,
    track: str,
    mastery_band: MasteryBand,
    mastery_score: float,
    witness_anchors: list[dict],
) -> str:
    """
    Build a dynamic system prompt tailored to the student's current ZPD zone
    and mastery level. The prompt instructs Adeline on exactly how to respond.
    """
    anchor_text = ""
    if witness_anchors:
        anchor_lines = "\n".join(
            f"  - [{a.get('track', track)}] {a.get('text', a.get('standard_id', ''))}"
            for a in witness_anchors
        )
        anchor_text = f"\nThe student's Witness Anchors (previously mastered standards):\n{anchor_lines}\n"

    if zone == ZPDZone.FRUSTRATED:
        zone_instruction = f"""
The student is FRUSTRATED or STUCK on this topic.

Your job: offer a Bridge Response.
  1. Do NOT give the answer directly.
  2. Find something the student already knows (use their Witness Anchors below).
  3. Say: "You learned about [anchor topic]. How might that connect to {topic}?"
  4. Ask one simple, open-ended question that they can answer with what they already know.
  5. Keep it warm, encouraging, and brief (2-3 sentences max).
{anchor_text}
"""
    elif zone == ZPDZone.BORED:
        zone_instruction = f"""
The student is BORED or READY TO ADVANCE beyond this topic.

Your job: offer an Elevation Response.
  1. Acknowledge their confidence briefly ("Great — you've got the foundation.").
  2. Introduce a harder dimension of {topic}: a contradiction in the primary sources,
     a comparison between two historical accounts, or a modern application challenge.
  3. End with a higher-order question (synthesis or evaluation level, not recall).
  4. Mention that Adeline is searching the verified archive for a more advanced source.
"""
    else:  # IN_ZPD
        zone_instruction = f"""
The student is IN their Zone of Proximal Development — engaged and working.

Your job: offer a Socratic Response.
  1. Affirm their effort without praising the answer ("Good thinking — let's go deeper.").
  2. Ask one probing question that moves them one step further into {topic}.
  3. Do not summarize what they said back to them. Move forward.
  4. If they gave a partial answer, isolate the gap with a follow-up question.
"""

    complexity_note = {
        MasteryBand.NOVICE:     "Use simple language. Avoid jargon. Connect to everyday life.",
        MasteryBand.DEVELOPING: "Use correct terminology but define it on first use.",
        MasteryBand.PROFICIENT: "Use subject-appropriate vocabulary. Introduce primary source excerpts.",
        MasteryBand.ADVANCED:   "Use full academic register. Engage with historiography and debate.",
    }[mastery_band]

    return f"""You are Adeline — a Truth-First K-12 AI Mentor grounded in the 8-Track Constitution.
You teach from verified primary sources only. You never invent facts or citations.
You are currently helping a student with: "{topic}" (Track: {track.replace("_", " ").title()}).

Student mastery level: {mastery_band.value} (score: {mastery_score:.2f}/1.0)
Complexity guidance: {complexity_note}
{zone_instruction}
Biblical worldview: Adeline has a biblical worldview rooted in scripture. When it is natural and relevant,
she may reference scripture. When she does, she uses the Everett Fox translation style:
  - Use the divine name YHWH (not "the Lord" or "God" in generic form)
  - Use original Hebrew/Greek names: Yeshua (not Jesus), Moshe (not Moses), Avraham, Yirmeyahu, etc.
  - Quote with the earthy, direct register of Fox's Schocken Bible
  - Scripture references must be brief and relevant — never preachy, never forced

Tone: warm, direct, a little bookish. Like a trusted older sibling who reads a lot.
Length: 2–4 sentences. Never lecture. Always end with a question or an invitation.
"""


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class ScaffoldResponse:
    zpd_zone: ZPDZone
    adeline_response: str
    witness_anchor_used: Optional[str]   # The standard text used as bridge, if any
    mastery_band: MasteryBand
    mastery_score: float


async def scaffold(
    student_response: str,
    topic: str,
    track: str,
    student_state: StudentState,
) -> ScaffoldResponse:
    """
    Evaluate the student's response and generate a ZPD-aware reply from Adeline.

    1. Detect ZPD zone from response text
    2. Load Witness Anchors from the student's mastered standards
    3. Build a dynamic system prompt
    4. Call OpenAI to generate Adeline's reply
    5. Return ScaffoldResponse with zone, reply, and anchor metadata
    """
    zone = detect_zpd_zone(student_response)
    logger.info(
        f"[Pedagogy] ZPD zone={zone.value} | topic='{topic}' | "
        f"response_len={len(student_response)}"
    )

    track_mastery = student_state.get(track)
    anchors = student_state.witness_anchors(track, limit=3)

    # For FRUSTRATED, also check adjacent tracks for anchors if current track is empty
    if zone == ZPDZone.FRUSTRATED and not anchors:
        for other_track, tm in student_state.tracks.items():
            if other_track != track and tm.mastered_standards:
                anchors = tm.mastered_standards[:2]
                break

    anchor_used = anchors[0].get("text", "") if anchors and zone == ZPDZone.FRUSTRATED else None

    system_prompt = _build_system_prompt(
        zone=zone,
        topic=topic,
        track=track,
        mastery_band=track_mastery.mastery_band,
        mastery_score=track_mastery.mastery_score,
        witness_anchors=anchors if zone == ZPDZone.FRUSTRATED else [],
    )

    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        completion = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": student_response},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[Pedagogy] OpenAI call failed: {e}")
        # Graceful fallback — never leave the student with nothing
        if zone == ZPDZone.FRUSTRATED:
            reply = (
                f"That's a tricky part of {topic}. Let's slow down. "
                "What do you already know about this from a previous lesson?"
            )
        elif zone == ZPDZone.BORED:
            reply = (
                f"Great — you've got the foundation. Here's a harder angle: "
                f"can you find a primary source that *contradicts* what we just read about {topic}?"
            )
        else:
            reply = f"Good thinking. What would you say is the most important idea in what we just read about {topic}?"

    return ScaffoldResponse(
        zpd_zone=zone,
        adeline_response=reply,
        witness_anchor_used=anchor_used,
        mastery_band=track_mastery.mastery_band,
        mastery_score=track_mastery.mastery_score,
    )
