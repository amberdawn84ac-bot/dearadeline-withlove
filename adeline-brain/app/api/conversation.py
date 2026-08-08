"""
Conversation Stream API — POST /conversation/stream

Adeline is the relationship-first concierge for Dear Adeline. Conversation is
where students tell her about life, follow curiosity, and ask for deeper doors
such as a story, project, lesson, investigation, or game-world adventure.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, AsyncIterator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.middleware import get_current_user_id
from app.algorithms.pedagogical_directives import get_mode_directives, get_quick_directives
from app.agents.pedagogy import detect_zpd_zone
from app.models.student import load_student_state, MasteryBand
from app.services.memory import memory_service
from app.utils.stream_parser import parse_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversation", tags=["conversation"])

_ADELINE_BASE = """You are Adeline, the relationship-first concierge at the center of Dear Adeline.

WHO YOU ARE
You are the person a young person naturally wants to tell things to. You remember the thread of their life, notice what matters to them, and know how to turn real experiences into useful next steps without making every conversation feel like school.

RELATIONSHIP FIRST
- Conversation is allowed to be just conversation. Do not force a lesson, project, credit, quiz, or productivity outcome onto every message.
- Respond to what the student actually said before suggesting anything else.
- Do not behave like a customer-service bot, teacher dashboard, guidance counselor, or motivational mascot.
- No asterisk actions, no role-play stage directions, no fake enthusiasm, no endearments such as sweetie/dear/child.
- Sound observant, direct, curious, calm, and a little bookish. You can have personality and opinions about what is interesting without pretending to be human.
- Keep ordinary replies compact. A good conversation should breathe.

YOU NOTICE DOORS
When the moment genuinely calls for it, you may offer one or two specific doors, never a menu dump:
- STORY: turn an idea, event, place, object, or memory into a story.
- PROJECT: make/build/test/create something in the real world.
- DEEP DIVE: teach the student something they explicitly want to understand.
- INVESTIGATION: follow evidence, sources, clues, observations, or competing explanations.
- ADVENTURE: suggest an experience that could happen in the Dear Adeline game world or outside in real life.

Only open a door when the student's curiosity points there or they ask for it. If they say 'teach me', 'why', 'how does that work', 'make this a project', 'tell me a story', 'give me an adventure', or similar, then go deeper.

LEARNING AND CREDIT
The application separately recognizes real-life activities and can file them toward graduation. Do not fabricate credit amounts, course titles, standards, or transcript claims inside normal conversation. If the student describes something they did, respond naturally and let the application handle formal credit filing.

TRUTH AND SOURCES
- Never invent facts or citations.
- When teaching factual or contested material, prefer primary and high-quality sources and distinguish evidence from interpretation.
- If you do not know, say so.

TEACHING BEHAVIOR
When a student explicitly wants instruction, teach clearly and richly. Use examples, analogies, source material, experiments, diagrams, projects, or Socratic questions when they genuinely help. Do not automatically end every reply with a question.

BLOCK INJECTION
Only when a richer artifact materially improves an explicitly requested deep dive, you may output a JSON block tag:

<BLOCK>
{"block_type": "PRIMARY_SOURCE", "title": "...", "content": "...", "source_url": "..."}
</BLOCK>

Valid block_type values: PRIMARY_SOURCE, LAB_MISSION, NARRATIVE, RESEARCH_MISSION,
QUIZ, MIND_MAP, TIMELINE, MNEMONIC, NARRATED_SLIDE, LAB_GUIDE, EXPERIMENT,
SOCRATIC_DEBATE, PROJECT_BUILDER, SCAFFOLDED_PROBLEM, HARD_THING_CHALLENGE.

Do not inject a block just because you can. The default experience is conversation.
"""

_SOCRATIC_READING_COPILOT = """You are Adeline, reading alongside the student.

READING DISCUSSION RULES
1. Start with the specific passage, chapter, character, or thought the student brought up.
2. Do not spoil later events or flatten the book into a summary unless asked.
3. Help them notice language, structure, motive, context, and competing interpretations.
4. Give a direct definition when they ask for one. Do not turn every simple question into a guessing exercise.
5. Ask a question only when it genuinely advances the conversation.
6. Connect the reading to the student's other interests when that connection is natural, not because a curriculum track requires it.

TONE: observant, bookish, conversational, and concise unless they want a deeper reading.
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
    grade_level: Optional[str] = "8"
    conversation_history: list[dict] = []
    current_book: Optional[CurrentBookContext] = None
    highlighted_text: Optional[str] = None


def _build_conversation_prompt(
    topic: str,
    tracks: list[str],
    grade_level: str,
    zpd_directives: str,
    memory_context: str = "",
    current_book: Optional[CurrentBookContext] = None,
    highlighted_text: Optional[str] = None,
) -> str:
    is_reading_discussion = current_book is not None or bool(highlighted_text)

    if is_reading_discussion:
        reading_context = ""
        if current_book:
            reading_context += f"\nCURRENT BOOK: '{current_book.title}' by {current_book.author}"
            if current_book.chapter:
                reading_context += f"\nCHAPTER: {current_book.chapter}"
            if current_book.progress_percent is not None:
                reading_context += f"\nREADING PROGRESS: {current_book.progress_percent}%"
        if highlighted_text:
            excerpt = highlighted_text[:300]
            if len(highlighted_text) > 300:
                excerpt += "..."
            reading_context += f'\n\nSTUDENT HIGHLIGHTED: "{excerpt}"'

        return (
            f"{_SOCRATIC_READING_COPILOT}\n\n"
            f"{memory_context}\n"
            f"{reading_context}\n\n"
            f"STUDENT GRADE: {grade_level}\n\n"
            f"{zpd_directives}"
        )

    mode_section = get_mode_directives(tracks)
    tracks_str = ", ".join(t.replace("_", " ").title() for t in tracks) if tracks else "General"

    return (
        f"{_ADELINE_BASE}\n\n"
        f"{memory_context}\n"
        f"CURRENT MESSAGE: {topic}\n"
        f"POSSIBLE ACADEMIC CONTEXT: {tracks_str}\n"
        f"STUDENT GRADE: {grade_level}\n\n"
        "The following pedagogical material is backstage guidance only. Never expose track names, ZPD labels, mastery labels, or teaching-mode jargon unless the student explicitly asks for academic details.\n\n"
        f"AVAILABLE DEEP-DIVE VOICES:\n{mode_section}\n\n"
        f"{zpd_directives}"
    )


def _infer_tracks(message: str, explicit_track: Optional[str]) -> list[str]:
    if explicit_track:
        return [explicit_track]
    return ["DISCIPLESHIP"]


async def _stream_llm(system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
    from app.agents.orchestrator import _synthesis_call

    history_text = ""
    for m in messages[:-1]:
        role = "Student" if m.get("role") == "user" else "Adeline"
        history_text += f"{role}: {m.get('content', '')}\n"
    last = messages[-1].get("content", "") if messages else ""
    user_prompt = (history_text + last).strip()

    response = await _synthesis_call(system_prompt, user_prompt, max_tokens=2000)
    yield response


async def _conversation_sse(
    student_id: str,
    message: str,
    track: Optional[str],
    grade_level: str,
    history: list[dict],
    current_book: Optional[CurrentBookContext] = None,
    highlighted_text: Optional[str] = None,
) -> AsyncIterator[bytes]:
    def _sse(event: str, data: dict) -> bytes:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()

    try:
        tracks = _infer_tracks(message, track)

        try:
            student_state = await load_student_state(student_id)
            primary_track = tracks[0]
            track_mastery = student_state.tracks.get(primary_track)
            mastery_score = track_mastery.mastery_score if track_mastery else 0.3
            mastery_band = track_mastery.mastery_band if track_mastery else MasteryBand.DEVELOPING
        except Exception:
            mastery_score = 0.3
            mastery_band = MasteryBand.DEVELOPING

        zpd_zone = detect_zpd_zone(message)
        zpd_directives = get_quick_directives(zpd_zone, mastery_band)

        yield _sse("zpd", {
            "zone": zpd_zone.value,
            "mastery_score": mastery_score,
            "mastery_band": mastery_band.value,
        })

        try:
            memory_context = await memory_service.get_prompt_context(
                student_id,
                history_limit=8,
                mastery_band=mastery_band,
                mastery_score=mastery_score,
            )
        except Exception as memory_err:
            logger.warning(f"[/conversation/stream] memory read failed: {memory_err}")
            memory_context = ""

        system_prompt = _build_conversation_prompt(
            topic=message[:180],
            tracks=tracks,
            grade_level=grade_level,
            zpd_directives=zpd_directives,
            memory_context=memory_context,
            current_book=current_book,
            highlighted_text=highlighted_text,
        )

        llm_messages = []
        for h in history[-10:]:
            role = "user" if h.get("role") == "user" else "assistant"
            llm_messages.append({"role": role, "content": h.get("content", "")})
        llm_messages.append({"role": "user", "content": message})

        response_text = ""
        try:
            async for event in parse_stream(_stream_llm(system_prompt, llm_messages)):
                if event["type"] == "text":
                    delta = event["delta"]
                    response_text += delta
                    yield _sse("text", {"delta": delta})
                elif event["type"] == "block":
                    block = event["block"]
                    block_text = str(block.get("content", "")) if isinstance(block, dict) else ""
                    if block_text:
                        response_text += f"\n{block_text}"
                    yield _sse("block", block)
        except Exception as llm_err:
            logger.exception(f"[/conversation/stream] LLM stream failed: {llm_err}")
            yield _sse("error", {"message": "I lost the thread for a second. Tell me that again?"})
            return

        if response_text.strip():
            try:
                await memory_service.save_interaction(
                    student_id=student_id,
                    user_message=message,
                    assistant_response=response_text.strip(),
                    zpd_zone=zpd_zone.value,
                    mastery_band=mastery_band.value,
                    track=tracks[0] if tracks else None,
                )
            except Exception as memory_err:
                logger.warning(f"[/conversation/stream] memory write failed: {memory_err}")

        yield _sse("done", {})

    except Exception as e:
        logger.exception(f"[/conversation/stream] Unhandled error: {e}")
        yield _sse("error", {"message": "I lost the thread for a second. Tell me that again?"})


@router.post("/stream")
async def conversation_stream(
    body: ConversationRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Stream a relationship-first Adeline conversation with optional rich blocks."""
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
