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
import time
from typing import Optional, AsyncIterator, Literal

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.connections.conversation_store import conversation_store

from app.api.middleware import get_current_user_id, verify_student_access_for_user
from app.algorithms.pedagogical_directives import get_mode_directives, get_quick_directives
from app.agents.pedagogy import detect_zpd_zone
from app.agents.persona import SCRIPTURE_TRANSLATION_POLICY
from app.models.student import load_student_state, MasteryBand
from app.services.resource_router import ResourceQuery, resource_block_from_packet, resource_router
from app.services.rate_limit import enforce_rate_limit
from app.utils.stream_parser import parse_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversation", tags=["conversation"])

_ADELINE_BASE = (
    """You are Adeline — a Truth-First K-12 AI Mentor grounded in the 10-Track Constitution.\n\n"""
    + SCRIPTURE_TRANSLATION_POLICY
    + """\n\nCORE RULES:
- This conversation is curricular. Teach, diagnose gaps, notice real learning,
  and connect what the learner says to the living plan, portfolio, and credit flow.
- Ordinary life can be rigorous learning. When a learner describes something
  they made, repaired, grew, cooked, researched, practiced, observed, or helped
  accomplish, identify the concepts and invite the existing activity recorder
  to preserve it; do not dismiss it as merely casual conversation.
- Teach from verified primary sources only. Never invent facts or citations.
- No asterisk actions, no endearments (sweetie, dear, child), no performance.
- Warm, direct, a little bookish. Like a trusted older sibling who reads a lot.
- Do not keep a conversation alive merely by asking another connection question.
- Questions are diagnostic tools, not the product. Once you understand enough, teach or act.
- Keep responses focused: 3–6 sentences unless teaching complex material.

BLOCK INJECTION:
When you want to show the student a primary source, lab guide, quiz, timeline, mind map,
experiment, project builder, or socratic debate — output it as a JSON block tag:

<BLOCK>
{"block_type": "PRIMARY_SOURCE", "title": "...", "content": "...", "source_url": "..."}
</BLOCK>

Valid block_type values: PRIMARY_SOURCE, LAB_MISSION, NARRATIVE, RESEARCH_MISSION,
QUIZ, MIND_MAP, TIMELINE, MNEMONIC, LAB_GUIDE, EXPERIMENT,
SOCRATIC_DEBATE, PROJECT_BUILDER, SCAFFOLDED_PROBLEM, HARD_THING_CHALLENGE.

You may inject a block mid-sentence. Text before and after the block will render
separately. After the block, continue your response naturally.
"""
)

# Socratic Reading Co-Pilot persona for Literature discussions
_SOCRATIC_READING_COPILOT = (
    """You are Adeline — a Socratic Reading Co-Pilot.\n\n"""
    + SCRIPTURE_TRANSLATION_POLICY
    + """\n\nREADING DISCUSSION RULES:
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
)


class CurrentBookContext(BaseModel):
    id: str = Field(max_length=200)
    title: str = Field(max_length=300)
    author: str = Field(max_length=200)
    cfi: Optional[str] = None
    chapter: Optional[str] = Field(default=None, max_length=300)
    progress_percent: Optional[int] = None


class ConversationTurn(BaseModel):
    role: Literal["user", "adeline", "assistant"]
    content: str = Field(max_length=4000)


class ConversationRequest(BaseModel):
    student_id: str
    message: str = Field(min_length=1, max_length=4000)
    track: Optional[str] = None
    grade_level: Optional[str] = "8"  # Default to middle school
    conversation_history: list[ConversationTurn] = Field(default_factory=list, max_length=20)
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
    learner_turn_count: int = 1,
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

    if learner_turn_count <= 1:
        progression = (
            "DISCOVERY TURN: You may ask at most one specific question if a missing detail truly changes "
            "what you should teach or propose. Otherwise begin teaching now."
        )
    elif learner_turn_count == 2:
        progression = (
            "TEACHING TURN: Stop gathering generic connections. Teach one substantial idea with facts, "
            "an example, and a brief check for understanding. Inject a NARRATIVE, TIMELINE, QUIZ, "
            "SCAFFOLDED_PROBLEM, or LAB_GUIDE block when it improves the teaching."
        )
    else:
        progression = (
            "ACTION TURN: Do not end with another open-ended connection question. Choose a concrete next "
            "move: teach the missing lesson, propose a specific mission/project, or—only when the learner "
            "describes completed work and evidence—invite them to record that accomplishment for credit. "
            "When the work is visual or physical (built, made, grown, repaired, cooked, drawn, performed), "
            "invite them to add a photo to their portfolio. Never use assessment language like 'submit "
            "evidence' with the learner. Do not ask for a photo of private writing, sensitive "
            "personal material, location, identity documents, or the learner's face. State the next step "
            "plainly and finish decisively."
        )

    return (
        f"{_ADELINE_BASE}\n\n"
        f"TODAY'S CONVERSATION TOPIC: {topic}\n"
        f"ACTIVE TRACKS: {tracks_str}\n"
        f"STUDENT GRADE: {grade_level}\n\n"
        f"TEACHING VOICES AVAILABLE:\n{mode_section}\n\n"
        "Follow the conversation. Use whichever voice the moment calls for.\n\n"
        f"CONVERSATION PROGRESSION:\n{progression}\n\n"
        f"{zpd_directives}"
    )


def _infer_tracks(message: str, explicit_track: Optional[str]) -> list[str]:
    """
    Return active tracks for this conversation turn.
    Uses the explicit track if provided; otherwise returns a safe default.
    DISCIPLESHIP is the fallback — it bypasses the Witness Protocol so Adeline
    can always respond without hitting ARCHIVE_SILENT on general chat.
    """
    if explicit_track:
        return [explicit_track]
    words = message.lower()
    if any(term in words for term in ("code", "coding", "program", "game design", "makecode", "business", "sell")):
        return ["CREATIVE_ECONOMY"]
    if any(term in words for term in ("history", "war", "ancient", "primary source", "historical")):
        return ["TRUTH_HISTORY"]
    if any(term in words for term in ("government", "civics", "election", "economics", "law")):
        return ["GOVERNMENT_ECONOMICS"]
    if any(term in words for term in ("science", "chemistry", "physics", "biology", "energy", "circuit", "experiment")):
        return ["CREATION_SCIENCE"]
    if any(term in words for term in ("math", "algebra", "geometry", "fraction", "number")):
        return ["APPLIED_MATHEMATICS"]
    if any(term in words for term in ("book", "read", "writing", "literature", "poem")):
        return ["ENGLISH_LITERATURE"]
    return ["DISCIPLESHIP"]


def _wants_outside_resource(message: str) -> bool:
    normalized = message.lower()
    return any(term in normalized for term in (
        "play a game", "find a game", "learning game", "learn coding", "learn to code",
        "makecode", "arcade", "simulation", "interactive", "outside resource",
        "find a video", "watch a video", "youtube channel", "find a source",
        "primary source", "find an experiment", "real artifact", "museum object",
    ))


def _requested_resource_types(message: str) -> tuple[str, ...]:
    normalized = message.lower()
    if "video" in normalized or "youtube" in normalized:
        return ("VIDEO",)
    if any(term in normalized for term in ("coding", "code", "makecode", "arcade")):
        return ("GAME_BUILDER", "GAME")
    if any(term in normalized for term in ("simulation", "interactive")):
        return ("SIMULATION", "GAME")
    if any(term in normalized for term in ("primary source", "source", "artifact", "museum")):
        return ("PRIMARY_SOURCE", "ARTIFACT_3D")
    if "experiment" in normalized:
        return ("EXPERIMENT", "SIMULATION")
    return ("GAME", "GAME_BUILDER")


async def _stream_llm(
    system_prompt: str,
    messages: list[dict],
) -> AsyncIterator[str]:
    """Yield text using the active synthesis client (Gemini, with Claude fallback)."""
    from app.services.synthesis import stream_synthesis

    # Build a single user turn: history + current message concatenated
    history_text = ""
    for m in messages[:-1]:
        role = "Student" if m.get("role") == "user" else "Adeline"
        history_text += f"{role}: {m.get('content', '')}\n"
    last = messages[-1].get("content", "") if messages else ""
    user_prompt = (history_text + last).strip()

    async for delta in stream_synthesis(system_prompt, user_prompt, max_tokens=2000):
        yield delta


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
        started_at = time.perf_counter()
        first_visible_at: float | None = None
        tracks = _infer_tracks(message, track)

        if not history:
            try:
                stored_history = await conversation_store.get_recent_history(student_id, limit=8)
                history = [
                    {
                        "role": "user" if item.get("role") == "USER" else "adeline",
                        "content": str(item.get("content") or "")[:4000],
                    }
                    for item in stored_history
                ]
            except Exception:
                logger.warning("[/conversation/stream] Persistent history unavailable", exc_info=True)

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
        first_visible_at = time.perf_counter()

        routed_resource_count = 0
        routed_resource_memory = ""
        if _wants_outside_resource(message):
            try:
                packet = await resource_router.search(ResourceQuery(
                    topic=message,
                    track=tracks[0],
                    grade_level=grade_level,
                    resource_types=_requested_resource_types(message),
                    limit=4,
                ))
                resource_block = resource_block_from_packet(packet)
                if resource_block:
                    routed_resource_count = len(packet.get("resources", []))
                    remembered = [
                        f"{item.get('name') or item.get('title')} ({item.get('url')})"
                        for item in packet.get("resources", [])[:4]
                        if item.get("name") or item.get("title")
                    ]
                    routed_resource_memory = (
                        "Adeline recommended these outside learning resources for this investigation: "
                        + "; ".join(remembered)
                        + ". The learner should return with an explanation, creation, screenshot, code, photo, or other demonstration; opening the resource alone earns no mastery."
                    )
                    yield _sse("block", resource_block)
            except Exception:
                logger.exception("[/conversation/stream] Resource Router failed")

        system_prompt = _build_conversation_prompt(
            topic=message[:120],
            tracks=tracks,
            grade_level=grade_level,
            zpd_directives=zpd_directives,
            current_book=current_book,
            highlighted_text=highlighted_text,
            learner_turn_count=1 + sum(1 for item in history if item.get("role") == "user"),
        )
        if routed_resource_count:
            system_prompt += (
                f"\n\nRESOURCE ROUTER: {routed_resource_count} approved options have already been shown. "
                "Briefly explain how the learner should use one as a curricular experience. Tell them to return "
                "and explain what they built, tested, decided, or understood; opening or playing alone earns no credit."
            )

        # Build message list (cap history at last 10 turns)
        llm_messages = []
        for h in history[-10:]:
            role = "user" if h.get("role") == "user" else "assistant"
            llm_messages.append({"role": role, "content": h.get("content", "")})
        llm_messages.append({"role": "user", "content": message})

        # Stream + parse
        assistant_text = ""
        try:
            async for event in parse_stream(_stream_llm(system_prompt, llm_messages)):
                if event["type"] == "text":
                    assistant_text += event["delta"]
                    yield _sse("text", {"delta": event["delta"]})
                elif event["type"] == "block":
                    yield _sse("block", event["block"])
        except Exception as llm_err:
            logger.exception(f"[/conversation/stream] LLM stream failed: {llm_err}")
            yield _sse("error", {"message": "I ran into a hiccup — give me a moment and try again."})
            return

        try:
            await conversation_store.save_interaction(
                student_id,
                message,
                assistant_text + (f"\n\n{routed_resource_memory}" if routed_resource_memory else ""),
                zpd_zone=zpd_zone.value,
                mastery_band=mastery_band.value,
                track=tracks[0],
            )
        except Exception:
            logger.exception("[/conversation/stream] Could not persist conversation")

        yield _sse("done", {})
        logger.info(
            "[/conversation/stream] timing student=%s first_event_ms=%.1f total_ms=%.1f resource_count=%d history_turns=%d",
            student_id,
            ((first_visible_at or time.perf_counter()) - started_at) * 1000,
            (time.perf_counter() - started_at) * 1000,
            routed_resource_count,
            len(history),
        )

    except Exception as e:
        logger.exception(f"[/conversation/stream] Unhandled error: {e}")
        yield _sse("error", {"message": "I ran into a hiccup — give me a moment and try again."})


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

    await verify_student_access_for_user(current_user_id, body.student_id)
    await enforce_rate_limit("conversation", body.student_id, limit=30)

    return StreamingResponse(
        _conversation_sse(
            student_id=body.student_id,
            message=body.message,
            track=body.track,
            grade_level=body.grade_level,
            history=[item.model_dump() for item in body.conversation_history],
            current_book=body.current_book,
            highlighted_text=body.highlighted_text,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
