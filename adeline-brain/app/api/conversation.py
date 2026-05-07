"""
Conversation Stream API — POST /conversation/stream

SSE endpoint. Streams Adeline's response token-by-token with inline block injection.
Replaces the generate + scaffold pair as the primary student delivery path.

Events emitted:
  event: text   data: {"delta": "..."}
  event: block  data: {"block_type": "...", "content": "...", ...}
  event: zpd    data: {"zone": "IN_ZPD", "mastery_score": 0.42, "mastery_band": "DEVELOPING"}
  event: done   data: {}
  event: error  data: {"message": "..."}
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional, AsyncIterator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import create_llm, ADELINE_MODEL

from app.api.middleware import get_current_user_id
from app.algorithms.pedagogical_directives import get_mode_directives, get_quick_directives
from app.agents.pedagogy import detect_zpd_zone
from app.models.student import load_student_state, MasteryBand
from app.utils.stream_parser import parse_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversation", tags=["conversation"])

_MODEL = ADELINE_MODEL

_ADELINE_BASE = """You are Adeline — a Truth-First K-12 AI Mentor grounded in the 10-Track Constitution.

CORE RULES:
- Teach from verified primary sources only. Never invent facts or citations.
- No asterisk actions, no endearments (sweetie, dear, child), no performance.
- Warm, direct, a little bookish. Like a trusted older sibling who reads a lot.
- End every response with a question or an invitation — never a lecture.
- Keep responses focused: 3–6 sentences unless teaching complex material.

BLOCK INJECTION:
When you want to show the student a primary source, lab guide, quiz, timeline, mind map,
experiment, project builder, or socratic debate — output it as a JSON block tag:

<BLOCK>
{"block_type": "PRIMARY_SOURCE", "title": "...", "content": "...", "source_url": "..."}
</BLOCK>

Valid block_type values: PRIMARY_SOURCE, LAB_MISSION, NARRATIVE, RESEARCH_MISSION,
QUIZ, MIND_MAP, TIMELINE, MNEMONIC, NARRATED_SLIDE, LAB_GUIDE, EXPERIMENT,
SOCRATIC_DEBATE, PROJECT_BUILDER, SCAFFOLDED_PROBLEM, HARD_THING_CHALLENGE.

You may inject a block mid-sentence. Text before and after the block will render
separately. After the block, continue your response naturally.
"""

# Socratic Reading Co-Pilot persona for Literature discussions
_SOCRATIC_READING_COPILOT = """You are Adeline — a Socratic Reading Co-Pilot.

READING DISCUSSION RULES:
1. NEVER give away the answer or summarize the whole book
2. ALWAYS acknowledge the specific chapter and highlighted passage first
3. Ask LEADING QUESTIONS to help the student deduce meaning from context:
   - "What do you think the author meant by...?"
   - "How does this connect to what happened earlier?"
   - "What emotions or ideas might this word carry here?"
4. Connect themes to the student's track/mastery when relevant:
   - Homesteading track: connect to soil, seasons, stewardship, craftsmanship
   - Applied Mathematics: patterns, logic, problem-solving in the text
   - Natural Philosophy: scientific metaphors, observation, wonder
   - Truth-History: historical context, primary source mindset
   - Discipleship: character formation, moral choices, wisdom
5. Guide students to discover layers of meaning through questioning
6. End EVERY response with a question or invitation — never a lecture
7. If a student asks for a word definition, give a brief hint first, then ask them to infer from context

TONE: Warm, bookish, like a trusted older sibling who loves stories. Encourage curiosity, not anxiety.
"""


class CurrentBookContext(BaseModel):
    id: str
    title: str
    author: str
    cfi: Optional[str] = None
    chapter: Optional[str] = None
    progress_percent: Optional[int] = None


class ConversationRequest(BaseModel):
    student_id: str
    message: str
    track: Optional[str] = None
    grade_level: Optional[str] = "8"  # Default to middle school
    conversation_history: list[dict] = []
    # Reading context for Literature Agent
    current_book: Optional[CurrentBookContext] = None
    highlighted_text: Optional[str] = None


def _build_conversation_prompt(
    topic: str,
    tracks: list[str],
    grade_level: str,
    zpd_directives: str,
    current_book: Optional[CurrentBookContext] = None,
    highlighted_text: Optional[str] = None,
) -> str:
    """Build the full system prompt for a conversation turn."""
    # Check if this is a reading discussion (Literature track or has book context)
    is_reading_discussion = (
        current_book is not None or 
        (highlighted_text and "highlighted this passage" in topic)
    )
    
    if is_reading_discussion:
        # Use Socratic Reading Co-Pilot persona
        base_prompt = _SOCRATIC_READING_COPILOT
        
        # Build reading context section
        reading_context = ""
        if current_book:
            reading_context += f"\nCURRENT BOOK: '{current_book.title}' by {current_book.author}"
            if current_book.chapter:
                reading_context += f"\nCHAPTER: {current_book.chapter}"
            if current_book.progress_percent is not None:
                reading_context += f"\nREADING PROGRESS: {current_book.progress_percent}%"
        
        if highlighted_text:
            reading_context += f"\n\nSTUDENT HAS HIGHLIGHTED:\"{highlighted_text[:300]}{'...' if len(highlighted_text) > 300 else ''}\""
        
        tracks_str = ", ".join(t.replace("_", " ").title() for t in tracks) if tracks else "General"
        
        return (
            f"{base_prompt}\n\n"
            f"{reading_context}\n\n"
            f"STUDENT TRACKS: {tracks_str}\n"
            f"STUDENT GRADE: {grade_level}\n\n"
            f"{zpd_directives}\n\n"
            "Remember: Guide through questions, don't give away answers. Connect to their track when relevant."
        )
    
    # Standard conversation prompt for non-reading topics
    mode_section = get_mode_directives(tracks)
    tracks_str = ", ".join(t.replace("_", " ").title() for t in tracks) if tracks else "General"

    return (
        f"{_ADELINE_BASE}\n\n"
        f"TODAY'S CONVERSATION TOPIC: {topic}\n"
        f"ACTIVE TRACKS: {tracks_str}\n"
        f"STUDENT GRADE: {grade_level}\n\n"
        f"TEACHING VOICES AVAILABLE:\n{mode_section}\n\n"
        "Follow the conversation. Use whichever voice the moment calls for.\n\n"
        f"{zpd_directives}"
    )


def _infer_tracks(message: str, explicit_track: Optional[str]) -> list[str]:
    """
    Return active tracks for this conversation turn.
    Uses the explicit track if provided; otherwise returns a safe default.
    """
    if explicit_track:
        return [explicit_track]
    return ["TRUTH_HISTORY"]


async def _stream_llm(
    system_prompt: str,
    messages: list[dict],
) -> AsyncIterator[str]:
    """Yield raw text chunks using the active LLM provider via LangChain."""
    lc_messages = [SystemMessage(content=system_prompt)]
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        else:
            from langchain_core.messages import AIMessage
            lc_messages.append(AIMessage(content=content))

    llm = create_llm(max_tokens=2000)
    async for chunk in llm.astream(lc_messages):
        if chunk.content:
            yield chunk.content


async def _conversation_sse(
    student_id: str,
    message: str,
    track: Optional[str],
    grade_level: str,
    history: list[dict],
    current_book: Optional[CurrentBookContext] = None,
    highlighted_text: Optional[str] = None,
) -> AsyncIterator[bytes]:
    """
    Core SSE generator. Yields raw SSE bytes.
    1. Load student state → get ZPD directives
    2. Build system prompt with mode + ZPD directives
    3. Stream Claude response
    4. Parse stream for <BLOCK> tags
    5. Emit text / block / zpd / done events
    """

    def _sse(event: str, data: dict) -> bytes:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()

    try:
        tracks = _infer_tracks(message, track)

        # Load student mastery for ZPD directives
        try:
            student_state = await load_student_state(student_id)
            primary_track = tracks[0]
            track_mastery = student_state.tracks.get(primary_track)
            mastery_score = track_mastery.mastery_score if track_mastery else 0.3
            mastery_band  = track_mastery.mastery_band  if track_mastery else MasteryBand.DEVELOPING
        except Exception:
            mastery_score = 0.3
            mastery_band  = MasteryBand.DEVELOPING

        zpd_zone       = detect_zpd_zone(message)
        zpd_directives = get_quick_directives(zpd_zone, mastery_band)

        # Emit ZPD state immediately so the UI updates the badge
        yield _sse("zpd", {
            "zone":         zpd_zone.value,
            "mastery_score": mastery_score,
            "mastery_band": mastery_band.value,
        })

        system_prompt = _build_conversation_prompt(
            topic=message[:120],
            tracks=tracks,
            grade_level=grade_level,
            zpd_directives=zpd_directives,
            current_book=current_book,
            highlighted_text=highlighted_text,
        )

        # Build message list (cap history at last 10 turns)
        llm_messages = []
        for h in history[-10:]:
            role = "user" if h.get("role") == "user" else "assistant"
            llm_messages.append({"role": role, "content": h.get("content", "")})
        llm_messages.append({"role": "user", "content": message})

        # Stream + parse
        async for event in parse_stream(_stream_llm(system_prompt, llm_messages)):
            if event["type"] == "text":
                yield _sse("text", {"delta": event["delta"]})
            elif event["type"] == "block":
                yield _sse("block", event["block"])

        yield _sse("done", {})

    except Exception as e:
        logger.exception(f"[/conversation/stream] Unhandled error: {e}")
        yield _sse("error", {"message": "Adeline ran into a problem. Please try again."})


@router.post("/stream")
async def conversation_stream(
    body: ConversationRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Stream Adeline's response as SSE with inline block injection.

    Track-aware mode voices (Investigator/Lab/Dialogue/Workshop) are injected
    automatically — no student-facing mode selection needed.
    
    For reading discussions (ENGLISH_LITERATURE track with book context),
    Adeline acts as a Socratic Reading Co-Pilot — guiding through questions
    rather than giving direct answers.
    """
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    return StreamingResponse(
        _conversation_sse(
            student_id=body.student_id,
            message=body.message,
            track=body.track,
            grade_level=body.grade_level,
            history=body.conversation_history,
            current_book=body.current_book,
            highlighted_text=body.highlighted_text,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
