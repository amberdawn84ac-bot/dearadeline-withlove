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
    lesson_count: int = 10,
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

    anchor_task_instruction = ""
    if lesson_count <= 3:
        anchor_task_instruction = (
            f"\nANCHOR TASK MODE (session {lesson_count + 1} of 3 for this track):\n"
            f"Do NOT assume this student is a beginner. Present a mid-level problem about "
            f"{topic} that requires real thinking. Their response will show you where they "
            f"actually are. Do not scaffold preemptively — just put the real task in front of them.\n"
        )

    return f"""You are Adeline — a Truth-First K-12 AI Mentor grounded in the 10-Track Constitution.
You teach from verified primary sources only. You never invent facts or citations.
You are currently helping a student with: "{topic}" (Track: {track.replace("_", " ").title()}).

Student mastery level: {mastery_band.value} (score: {mastery_score:.2f}/1.0)
Complexity guidance: {complexity_note}
{anchor_task_instruction}{zone_instruction}
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
        lesson_count=track_mastery.lesson_count,
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


# ── Snippet Explanation (Highlight & Ask) ────────────────────────────────────


@dataclass
class SnippetExplanation:
    """Response from explain_snippet — a quick, ZPD-adapted explanation."""
    explanation: str
    zpd_zone: ZPDZone
    mastery_band: MasteryBand
    follow_up_question: str


def _build_snippet_system_prompt(
    snippet: str,
    lesson_topic: str,
    track: str,
    mastery_band: MasteryBand,
    mastery_score: float,
    student_question: Optional[str] = None,
) -> str:
    """
    Build a system prompt for explaining a highlighted text snippet.
    Optimized for quick, contextual micro-explanations.
    """
    complexity_note = {
        MasteryBand.NOVICE:     "Use very simple language. Define every term. Use analogies to everyday life.",
        MasteryBand.DEVELOPING: "Use clear language. Define technical terms on first use.",
        MasteryBand.PROFICIENT: "Use subject-appropriate vocabulary. Connect to broader concepts.",
        MasteryBand.ADVANCED:   "Use full academic register. Reference historiography or scientific debate.",
    }[mastery_band]

    question_context = ""
    if student_question:
        question_context = f"\nThe student specifically asked: \"{student_question}\"\n"

    return f"""You are Adeline — a Truth-First K-12 AI Mentor.
You are helping a student understand a specific passage they highlighted while reading a lesson.

LESSON TOPIC: {lesson_topic}
TRACK: {track.replace("_", " ").title()}
STUDENT MASTERY: {mastery_band.value} (score: {mastery_score:.2f}/1.0)

THE HIGHLIGHTED TEXT:
\"\"\"{snippet}\"\"\"
{question_context}
YOUR TASK:
1. Explain this specific passage in 2-3 sentences, adapted to the student's level.
2. {complexity_note}
3. Connect it to the broader lesson topic if helpful.
4. End with ONE follow-up question that checks understanding or invites deeper thinking.

TONE: Warm, direct, encouraging. Like a trusted older sibling explaining something.
LENGTH: Keep it brief — this is a micro-explanation, not a lecture. 3-5 sentences total.

FORMAT YOUR RESPONSE AS:
[Your explanation here]

**Think about it:** [Your follow-up question here]
"""


async def explain_snippet(
    snippet: str,
    lesson_topic: str,
    track: str,
    student_state: StudentState,
    student_question: Optional[str] = None,
) -> SnippetExplanation:
    """
    Generate a quick, ZPD-adapted explanation for a highlighted text snippet.
    
    This is the backend for the "Highlight & Ask" feature — when a student
    selects text in a lesson and clicks "Ask Adeline", this function generates
    a contextual micro-explanation adapted to their mastery level.
    
    Args:
        snippet: The highlighted text from the lesson
        lesson_topic: The topic of the current lesson
        track: The learning track (e.g., "TRUTH_HISTORY")
        student_state: The student's current mastery state
        student_question: Optional specific question from the student
    
    Returns:
        SnippetExplanation with the explanation, follow-up question, and ZPD metadata
    """
    track_mastery = student_state.get(track)
    
    # Detect ZPD zone from the question if provided, otherwise assume IN_ZPD
    zone = ZPDZone.IN_ZPD
    if student_question:
        zone = detect_zpd_zone(student_question)
    
    logger.info(
        f"[Pedagogy] explain_snippet | topic='{lesson_topic}' | "
        f"snippet_len={len(snippet)} | zone={zone.value}"
    )

    system_prompt = _build_snippet_system_prompt(
        snippet=snippet,
        lesson_topic=lesson_topic,
        track=track,
        mastery_band=track_mastery.mastery_band,
        mastery_score=track_mastery.mastery_score,
        student_question=student_question,
    )

    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        completion = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please explain this highlighted text: \"{snippet[:500]}\""},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        full_response = completion.choices[0].message.content.strip()
        
        # Parse out the follow-up question if present
        if "**Think about it:**" in full_response:
            parts = full_response.split("**Think about it:**")
            explanation = parts[0].strip()
            follow_up = parts[1].strip() if len(parts) > 1 else ""
        else:
            explanation = full_response
            follow_up = f"What do you think is the most important idea in this passage?"
            
    except Exception as e:
        logger.error(f"[Pedagogy] explain_snippet OpenAI call failed: {e}")
        # Graceful fallback
        explanation = (
            f"This passage is talking about an important part of {lesson_topic}. "
            f"Let's break it down together — what part of it is most confusing to you?"
        )
        follow_up = "Can you tell me which word or idea you'd like me to explain first?"

    return SnippetExplanation(
        explanation=explanation,
        zpd_zone=zone,
        mastery_band=track_mastery.mastery_band,
        follow_up_question=follow_up,
    )
