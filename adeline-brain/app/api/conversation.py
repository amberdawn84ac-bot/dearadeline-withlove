"""Relationship-first conversation stream for Adeline."""
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
- Sound observant, direct, curious, calm, and a little bookish.
- Keep ordinary replies compact. A good conversation should breathe.

YOU NOTICE DOORS
When the moment genuinely calls for it, you may offer one or two specific doors, never a menu dump:
- STORY: turn an idea, event, place, object, or memory into a story.
- PROJECT: make/build/test/create something in the real world.
- DEEP DIVE: teach the student something they explicitly want to understand.
- INVESTIGATION: follow evidence, sources, clues, observations, or competing explanations.
- ADVENTURE: suggest an experience that could happen in the Dear Adeline game world or outside in real life.

Only open a door when the student's curiosity points there or they ask for it.

SKETCHNOTE ANSWERS
When the student asks an explanatory question and the answer would be easier to remember visually, answer conversationally first, then make a compact SKETCHNOTE_NOTE block. Think hand-drawn field notebook, not slideshow or worksheet.
Use 2-5 short sections, a strong central big idea, a few memorable keywords, and simple doodle symbols. Do not overfill the page.
If the student says things like "sketch that", "make me notes", "help me remember this", "show me", or asks a substantial why/how question, prefer a sketchnote unless plain text is clearly better.

Exact shape:
<BLOCK>
{"block_type":"SKETCHNOTE_NOTE","title":"...","big_idea":"...","sections":[{"heading":"...","text":"...","symbol":"..."}],"keywords":["..."],"footer":"...","track":"OPTIONAL_TRACK_NAME"}
</BLOCK>

LEARNING AND CREDIT
The application separately recognizes real-life activities and can file them toward graduation. Do not fabricate credit amounts, course titles, standards, or transcript claims inside normal conversation.

TRUTH AND SOURCES
- Never invent facts or citations.
- When teaching factual or contested material, prefer primary and high-quality sources and distinguish evidence from interpretation.
- If you do not know, say so.

TEACHING BEHAVIOR
When a student explicitly wants instruction, teach clearly and richly. Use examples, analogies, source material, experiments, diagrams, projects, sketchnotes, or Socratic questions when they genuinely help. Do not automatically end every reply with a question.

OTHER RICH BLOCKS
Only when materially useful, you may also use: PRIMARY_SOURCE, LAB_MISSION, NARRATIVE, RESEARCH_MISSION, QUIZ, MIND_MAP, TIMELINE, MNEMONIC, NARRATED_SLIDE, LAB_GUIDE, EXPERIMENT, SOCRATIC_DEBATE, PROJECT_BUILDER, SCAFFOLDED_PROBLEM, HARD_THING_CHALLENGE.
Do not inject a block just because you can. The default experience is conversation.
"""

_SOCRATIC_READING_COPILOT = """You are Adeline, reading alongside the student.
Start with the specific passage, chapter, character, or thought they brought up. Do not spoil later events unless asked. Help them notice language, structure, motive, context, and competing interpretations. Give direct definitions when asked. Ask a question only when it genuinely advances the conversation. If a compact illustrated note would help them remember the idea, use a SKETCHNOTE_NOTE block with the same schema as normal Adeline conversation.
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


def _build_conversation_prompt(topic: str, tracks: list[str], grade_level: str, zpd_directives: str, memory_context: str = "", current_book: Optional[CurrentBookContext] = None, highlighted_text: Optional[str] = None) -> str:
    if current_book is not None or highlighted_text:
        context = ""
        if current_book:
            context += f"\nCURRENT BOOK: '{current_book.title}' by {current_book.author}"
            if current_book.chapter:
                context += f"\nCHAPTER: {current_book.chapter}"
            if current_book.progress_percent is not None:
                context += f"\nREADING PROGRESS: {current_book.progress_percent}%"
        if highlighted_text:
            excerpt = highlighted_text[:300] + ("..." if len(highlighted_text) > 300 else "")
            context += f'\nSTUDENT HIGHLIGHTED: "{excerpt}"'
        return f"{_ADELINE_BASE}\n\n{_SOCRATIC_READING_COPILOT}\n\n{memory_context}\n{context}\nSTUDENT GRADE: {grade_level}\n{zpd_directives}"

    mode_section = get_mode_directives(tracks)
    tracks_str = ", ".join(t.replace("_", " ").title() for t in tracks) if tracks else "General"
    return (
        f"{_ADELINE_BASE}\n\n{memory_context}\n"
        f"CURRENT MESSAGE: {topic}\nPOSSIBLE ACADEMIC CONTEXT: {tracks_str}\nSTUDENT GRADE: {grade_level}\n\n"
        "The following pedagogy is backstage guidance only. Never expose track names, ZPD labels, mastery labels, or teaching-mode jargon unless the student explicitly asks for academic details.\n\n"
        f"AVAILABLE DEEP-DIVE VOICES:\n{mode_section}\n\n{zpd_directives}"
    )


def _infer_tracks(message: str, explicit_track: Optional[str]) -> list[str]:
    return [explicit_track] if explicit_track else ["DISCIPLESHIP"]


async def _stream_llm(system_prompt: str, messages: list[dict]) -> AsyncIterator[str]:
    from app.agents.orchestrator import _synthesis_call
    history_text = ""
    for m in messages[:-1]:
        role = "Student" if m.get("role") == "user" else "Adeline"
        history_text += f"{role}: {m.get('content', '')}\n"
    last = messages[-1].get("content", "") if messages else ""
    yield await _synthesis_call(system_prompt, (history_text + last).strip(), max_tokens=2200)


async def _conversation_sse(student_id: str, message: str, track: Optional[str], grade_level: str, history: list[dict], current_book: Optional[CurrentBookContext] = None, highlighted_text: Optional[str] = None) -> AsyncIterator[bytes]:
    def _sse(event: str, data: dict) -> bytes:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()

    try:
        tracks = _infer_tracks(message, track)
        try:
            student_state = await load_student_state(student_id)
            track_mastery = student_state.tracks.get(tracks[0])
            mastery_score = track_mastery.mastery_score if track_mastery else 0.3
            mastery_band = track_mastery.mastery_band if track_mastery else MasteryBand.DEVELOPING
        except Exception:
            mastery_score = 0.3
            mastery_band = MasteryBand.DEVELOPING

        zpd_zone = detect_zpd_zone(message)
        zpd_directives = get_quick_directives(zpd_zone, mastery_band)
        yield _sse("zpd", {"zone": zpd_zone.value, "mastery_score": mastery_score, "mastery_band": mastery_band.value})

        try:
            memory_context = await memory_service.get_prompt_context(student_id, history_limit=8, mastery_band=mastery_band, mastery_score=mastery_score)
        except Exception as memory_err:
            logger.warning(f"[/conversation/stream] memory read failed: {memory_err}")
            memory_context = ""

        system_prompt = _build_conversation_prompt(message[:180], tracks, grade_level, zpd_directives, memory_context, current_book, highlighted_text)
        llm_messages = [{"role": "user" if h.get("role") == "user" else "assistant", "content": h.get("content", "")} for h in history[-10:]]
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
                    if isinstance(block, dict) and block.get("block_type") != "SKETCHNOTE_NOTE":
                        block_text = str(block.get("content", ""))
                        if block_text:
                            response_text += f"\n{block_text}"
                    yield _sse("block", block)
        except Exception as llm_err:
            logger.exception(f"[/conversation/stream] LLM stream failed: {llm_err}")
            yield _sse("error", {"message": "I lost the thread for a second. Tell me that again?"})
            return

        if response_text.strip():
            try:
                await memory_service.save_interaction(student_id=student_id, user_message=message, assistant_response=response_text.strip(), zpd_zone=zpd_zone.value, mastery_band=mastery_band.value, track=tracks[0] if tracks else None)
            except Exception as memory_err:
                logger.warning(f"[/conversation/stream] memory write failed: {memory_err}")

        yield _sse("done", {})
    except Exception as exc:
        logger.exception(f"[/conversation/stream] Unhandled error: {exc}")
        yield _sse("error", {"message": "I lost the thread for a second. Tell me that again?"})


@router.post("/stream")
async def conversation_stream(body: ConversationRequest, current_user_id: str = Depends(get_current_user_id)):
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    return StreamingResponse(
        _conversation_sse(body.student_id, body.message, body.track, body.grade_level, body.conversation_history, body.current_book, body.highlighted_text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
