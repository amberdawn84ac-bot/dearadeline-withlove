# Streaming Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the batch generate → render → scaffold flow with a single SSE streaming endpoint where Adeline talks conversationally and surfaces GenUI blocks inline mid-sentence.

**Architecture:** A new `POST /conversation/stream` FastAPI endpoint streams Claude's response as SSE, parsing `<BLOCK>...</BLOCK>` tags inline to emit interleaved `text` and `block` events. The UI consumes this with an async generator, appending text tokens to a streaming bubble and rendering block components between text segments. Track-aware mode directives (Investigator / Lab / Dialogue / Workshop) are injected into the system prompt automatically — no student-facing mode selection.

**Tech Stack:** FastAPI + SSE (`StreamingResponse`), Anthropic streaming API (`anthropic.AsyncAnthropic`), Python `asyncio`, Next.js 14 + TypeScript, `fetch` with `ReadableStream` for SSE parsing.

---

## File Map

### New files
- `adeline-brain/app/utils/stream_parser.py` — async generator that splits text chunks from `<BLOCK>` tags
- `adeline-brain/app/api/conversation.py` — `POST /conversation/stream` SSE endpoint
- `adeline-brain/tests/utils/test_stream_parser.py` — unit tests for stream parser
- `adeline-brain/tests/test_conversation_api.py` — integration tests for the endpoint

### Modified files
- `adeline-brain/app/algorithms/pedagogical_directives.py` — add `TRACK_TO_MODE`, `_MODE_DIRECTIVES`, `get_mode_directives()`
- `adeline-brain/app/main.py` — register `conversation_router`
- `adeline-ui/src/lib/brain-client.ts` — add `ConversationEvent` type + `streamConversation()` async generator
- `adeline-ui/src/components/AdelineChatPanel.tsx` — streaming render loop replacing generate + scaffold calls

---

## Task 1: Mode Directives

**Files:**
- Modify: `adeline-brain/app/algorithms/pedagogical_directives.py`
- Test: `adeline-brain/tests/algorithms/test_pedagogical_directives.py` (add to existing file if present, else create)

- [ ] **Step 1.1: Write failing tests**

```python
# adeline-brain/tests/algorithms/test_mode_directives.py
from app.algorithms.pedagogical_directives import get_mode_directives, TRACK_TO_MODE

def test_single_track_returns_one_mode():
    result = get_mode_directives(["TRUTH_HISTORY"])
    assert "INVESTIGATOR" in result
    assert "LAB" not in result

def test_multi_track_blends_modes():
    result = get_mode_directives(["CREATIVE_ECONOMY", "HOMESTEADING"])
    assert "WORKSHOP" in result
    assert "LAB" in result

def test_all_10_tracks_map():
    all_tracks = [
        "TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "CREATION_SCIENCE",
        "HOMESTEADING", "HEALTH_NATUROPATHY", "GOVERNMENT_ECONOMICS",
        "DISCIPLESHIP", "ENGLISH_LITERATURE", "APPLIED_MATHEMATICS",
        "CREATIVE_ECONOMY",
    ]
    for track in all_tracks:
        assert track in TRACK_TO_MODE, f"{track} missing from TRACK_TO_MODE"

def test_unknown_track_returns_empty():
    result = get_mode_directives(["NOT_A_TRACK"])
    assert result == ""

def test_empty_tracks_returns_empty():
    assert get_mode_directives([]) == ""
```

- [ ] **Step 1.2: Run to verify they fail**

```bash
cd adeline-brain
python -m pytest tests/algorithms/test_mode_directives.py -v
```
Expected: `ImportError` or `AttributeError` — `TRACK_TO_MODE` and `get_mode_directives` don't exist yet.

- [ ] **Step 1.3: Add mode directives to `pedagogical_directives.py`**

Add after the existing imports at the top of the file:

```python
# ── Track → Mode Mapping ─────────────────────────────────────────────────────

TRACK_TO_MODE: dict[str, str] = {
    "TRUTH_HISTORY":        "INVESTIGATOR",
    "JUSTICE_CHANGEMAKING": "INVESTIGATOR",
    "CREATION_SCIENCE":     "LAB",
    "HOMESTEADING":         "LAB",
    "HEALTH_NATUROPATHY":   "DIALOGUE",
    "GOVERNMENT_ECONOMICS": "INVESTIGATOR",
    "DISCIPLESHIP":         "DIALOGUE",
    "ENGLISH_LITERATURE":   "DIALOGUE",
    "APPLIED_MATHEMATICS":  "LAB",
    "CREATIVE_ECONOMY":     "WORKSHOP",
}

_MODE_DIRECTIVES: dict[str, str] = {
    "INVESTIGATOR": (
        "INVESTIGATOR MODE:\n"
        "- Lead with a question or a discrepancy — never an explanation.\n"
        "- When you have a relevant primary source, surface it with a <BLOCK> tag mid-sentence.\n"
        "- Never summarize what the archive says. Show the raw material and ask what the student notices.\n"
        "- 'Follow the money' and 'Who wrote this, and why?' are always valid questions.\n"
    ),
    "LAB": (
        "LAB MODE:\n"
        "- Frame everything as a prediction before revealing anything.\n"
        "- Ask: 'What would you expect to happen?' before showing results.\n"
        "- Surface LabGuide or ExperimentCard blocks when the student is ready to try something.\n"
        "- Connect every concept back to something testable on the homestead.\n"
    ),
    "DIALOGUE": (
        "DIALOGUE MODE:\n"
        "- Reason together, out loud. Ask 'what do you think?' before telling them what you think.\n"
        "- Pull in scripture when genuinely relevant — Fox translation, never decorative.\n"
        "- Read carefully. Name what you see honestly. Speak into it with precision and courage.\n"
        "- Surface SocraticDebate blocks when the student is ready to defend a position.\n"
    ),
    "WORKSHOP": (
        "WORKSHOP MODE:\n"
        "- Connect everything to making, pricing, and selling real things.\n"
        "- 'What would you make with this?' and 'What would you charge?' are always valid.\n"
        "- Surface ProjectBuilder blocks when the student has enough context to build something.\n"
        "- Math lives in the workshop: materials, margins, market pricing.\n"
    ),
}


def get_mode_directives(tracks: list[str]) -> str:
    """
    Return blended mode directives for the given active tracks.
    Multiple tracks may map to the same mode — deduplication is handled automatically.
    Adeline moves between voices as the conversation calls for it.
    """
    modes = {TRACK_TO_MODE[t] for t in tracks if t in TRACK_TO_MODE}
    if not modes:
        return ""
    parts = [_MODE_DIRECTIVES[mode] for mode in sorted(modes)]
    return "\n\n".join(parts)
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
cd adeline-brain
python -m pytest tests/algorithms/test_mode_directives.py -v
```
Expected: all 5 tests pass.

- [ ] **Step 1.5: Commit**

```bash
cd adeline-brain
git add app/algorithms/pedagogical_directives.py tests/algorithms/test_mode_directives.py
git commit -m "feat: track-to-mode directives for conversation streaming"
```

---

## Task 2: Stream Parser

**Files:**
- Create: `adeline-brain/app/utils/stream_parser.py`
- Create: `adeline-brain/tests/utils/__init__.py`
- Create: `adeline-brain/tests/utils/test_stream_parser.py`

- [ ] **Step 2.1: Write failing tests**

```python
# adeline-brain/tests/utils/test_stream_parser.py
import pytest
from app.utils.stream_parser import parse_stream

async def _collect(chunks: list[str]) -> list[dict]:
    """Helper: feed chunks through the parser and collect all events."""
    async def gen():
        for c in chunks:
            yield c
    return [e async for e in parse_stream(gen())]


@pytest.mark.asyncio
async def test_text_only():
    events = await _collect(["Hello ", "world."])
    assert events == [{"type": "text", "delta": "Hello world."}]


@pytest.mark.asyncio
async def test_block_only():
    block_json = '{"block_type": "PRIMARY_SOURCE", "content": "test"}'
    events = await _collect([f"<BLOCK>{block_json}</BLOCK>"])
    assert len(events) == 1
    assert events[0]["type"] == "block"
    assert events[0]["block"]["block_type"] == "PRIMARY_SOURCE"


@pytest.mark.asyncio
async def test_text_then_block_then_text():
    block_json = '{"block_type": "QUIZ", "content": "q?"}'
    events = await _collect([f"Before. <BLOCK>{block_json}</BLOCK> After."])
    types = [e["type"] for e in events]
    assert types == ["text", "block", "text"]
    assert "Before." in events[0]["delta"]
    assert "After." in events[2]["delta"]


@pytest.mark.asyncio
async def test_block_split_across_chunks():
    block_json = '{"block_type": "LAB_MISSION", "content": "do this"}'
    mid = len(block_json) // 2
    chunks = [
        "Lead-in. <BLOCK>",
        block_json[:mid],
        block_json[mid:],
        "</BLOCK> Follow-up.",
    ]
    events = await _collect(chunks)
    types = [e["type"] for e in events]
    assert types == ["text", "block", "text"]


@pytest.mark.asyncio
async def test_malformed_block_emitted_as_text():
    events = await _collect(["<BLOCK>not json</BLOCK>"])
    assert events[0]["type"] == "text"


@pytest.mark.asyncio
async def test_multiple_blocks():
    b1 = '{"block_type": "PRIMARY_SOURCE", "content": "a"}'
    b2 = '{"block_type": "QUIZ", "content": "b"}'
    events = await _collect([f"Text. <BLOCK>{b1}</BLOCK> Middle. <BLOCK>{b2}</BLOCK> End."])
    block_events = [e for e in events if e["type"] == "block"]
    assert len(block_events) == 2
```

- [ ] **Step 2.2: Run to verify they fail**

```bash
cd adeline-brain
python -m pytest tests/utils/test_stream_parser.py -v
```
Expected: `ModuleNotFoundError` — `stream_parser` doesn't exist yet.

- [ ] **Step 2.3: Create `app/utils/stream_parser.py`**

```python
# adeline-brain/app/utils/stream_parser.py
"""
Stream parser — splits Adeline's streamed response into text and block events.

Handles <BLOCK>...</BLOCK> tags that may span multiple chunks.
Yields dicts suitable for direct SSE emission:
  {"type": "text",  "delta": "..."}
  {"type": "block", "block": {...}}
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

_BLOCK_OPEN  = "<BLOCK>"
_BLOCK_CLOSE = "</BLOCK>"
_OPEN_LEN    = len(_BLOCK_OPEN)
_CLOSE_LEN   = len(_BLOCK_CLOSE)


async def parse_stream(
    chunks: AsyncIterator[str],
) -> AsyncIterator[dict]:
    """
    Async generator — consumes a stream of text chunks and yields
    {"type": "text", "delta": str} and {"type": "block", "block": dict} events.

    Safe tail: keeps the last len("<BLOCK>") - 1 chars buffered when not inside
    a block tag, so partial opening tags are never emitted prematurely.
    """
    buffer   = ""
    in_block = False

    async for chunk in chunks:
        buffer += chunk

        # Keep processing until no more complete tokens can be extracted
        while True:
            if not in_block:
                tag_start = buffer.find(_BLOCK_OPEN)
                if tag_start == -1:
                    # No block tag found — emit everything except the safe tail
                    safe_end = max(0, len(buffer) - (_OPEN_LEN - 1))
                    if safe_end > 0:
                        yield {"type": "text", "delta": buffer[:safe_end]}
                        buffer = buffer[safe_end:]
                    break  # need more chunks
                # Emit text before the tag
                if tag_start > 0:
                    yield {"type": "text", "delta": buffer[:tag_start]}
                buffer   = buffer[tag_start + _OPEN_LEN:]
                in_block = True

            else:  # inside a block
                tag_end = buffer.find(_BLOCK_CLOSE)
                if tag_end == -1:
                    break  # block not yet closed — need more chunks
                block_content = buffer[:tag_end].strip()
                buffer        = buffer[tag_end + _CLOSE_LEN:]
                in_block      = False
                try:
                    block_data = json.loads(block_content)
                    yield {"type": "block", "block": block_data}
                except json.JSONDecodeError:
                    logger.warning("[stream_parser] Malformed block JSON — emitting as text")
                    yield {"type": "text", "delta": f"{_BLOCK_OPEN}{block_content}{_BLOCK_CLOSE}"}

    # Flush remainder
    if buffer.strip() and not in_block:
        yield {"type": "text", "delta": buffer}
```

- [ ] **Step 2.4: Create `tests/utils/__init__.py`**

```bash
touch adeline-brain/tests/utils/__init__.py
```

- [ ] **Step 2.5: Run tests to verify they pass**

```bash
cd adeline-brain
python -m pytest tests/utils/test_stream_parser.py -v
```
Expected: all 6 tests pass.

- [ ] **Step 2.6: Commit**

```bash
cd adeline-brain
git add app/utils/stream_parser.py tests/utils/__init__.py tests/utils/test_stream_parser.py
git commit -m "feat: async stream parser for inline block injection"
```

---

## Task 3: Conversation Endpoint

**Files:**
- Create: `adeline-brain/app/api/conversation.py`
- Create: `adeline-brain/tests/test_conversation_api.py`

- [ ] **Step 3.1: Write failing tests**

```python
# adeline-brain/tests/test_conversation_api.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Import app after mocking deps
@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def _parse_sse(raw: bytes) -> list[dict]:
    """Parse raw SSE bytes into a list of event dicts."""
    events = []
    current_event = {}
    for line in raw.decode().splitlines():
        if line.startswith("event: "):
            current_event["event"] = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]
            if data_str.strip():
                current_event["data"] = json.loads(data_str)
        elif line == "" and current_event:
            events.append(current_event)
            current_event = {}
    return events


def test_conversation_stream_requires_auth(client):
    resp = client.post("/conversation/stream", json={
        "student_id": "test-student",
        "message": "Tell me about soil",
        "track": "HOMESTEADING",
        "grade_level": "8",
        "conversation_history": [],
    })
    assert resp.status_code == 401


def test_conversation_stream_rejects_missing_message(client):
    resp = client.post(
        "/conversation/stream",
        json={"student_id": "s1", "grade_level": "8", "conversation_history": []},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_build_conversation_prompt_includes_mode():
    from app.api.conversation import _build_conversation_prompt
    prompt = _build_conversation_prompt(
        topic="Dust Bowl",
        tracks=["TRUTH_HISTORY"],
        grade_level="9",
        zpd_directives="ZPD: IN_ZPD",
    )
    assert "INVESTIGATOR" in prompt
    assert "Dust Bowl" in prompt
    assert "ZPD: IN_ZPD" in prompt


@pytest.mark.asyncio
async def test_build_conversation_prompt_blends_modes():
    from app.api.conversation import _build_conversation_prompt
    prompt = _build_conversation_prompt(
        topic="Soap making",
        tracks=["CREATIVE_ECONOMY", "HOMESTEADING"],
        grade_level="10",
        zpd_directives="",
    )
    assert "WORKSHOP" in prompt
    assert "LAB" in prompt
```

- [ ] **Step 3.2: Run to verify they fail**

```bash
cd adeline-brain
python -m pytest tests/test_conversation_api.py -v
```
Expected: `ImportError` — `app.api.conversation` doesn't exist yet.

- [ ] **Step 3.3: Create `app/api/conversation.py`**

```python
# adeline-brain/app/api/conversation.py
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

import anthropic
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.middleware import get_current_user_id
from app.algorithms.pedagogical_directives import (
    get_mode_directives,
    get_quick_directives,
)
from app.agents.pedagogy import detect_zpd_zone, ZPDZone
from app.models.student import load_student_state, MasteryBand
from app.utils.stream_parser import parse_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversation", tags=["conversation"])

_MODEL = os.getenv("ADELINE_MODEL", "claude-sonnet-4-6")

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


class ConversationRequest(BaseModel):
    student_id: str
    message: str
    track: Optional[str] = None
    grade_level: str
    conversation_history: list[dict] = []


def _build_conversation_prompt(
    topic: str,
    tracks: list[str],
    grade_level: str,
    zpd_directives: str,
) -> str:
    """Build the full system prompt for a conversation turn."""
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
    Uses the explicit track if provided; otherwise returns a default.
    Multi-track detection can be expanded here later.
    """
    if explicit_track:
        return [explicit_track]
    return ["TRUTH_HISTORY"]  # safe default — Investigator mode


async def _stream_claude(
    system_prompt: str,
    messages: list[dict],
) -> AsyncIterator[str]:
    """Yield raw text chunks from Claude's streaming API."""
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    async with client.messages.stream(
        model=_MODEL,
        system=system_prompt,
        messages=messages,
        max_tokens=2000,
    ) as stream:
        async for text_chunk in stream.text_stream:
            yield text_chunk


async def _conversation_sse(
    student_id: str,
    message: str,
    track: Optional[str],
    grade_level: str,
    history: list[dict],
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
        # Load student mastery for ZPD directives
        tracks = _infer_tracks(message, track)
        try:
            student_state = await load_student_state(student_id)
            primary_track = tracks[0]
            track_mastery = student_state.get(primary_track)
            mastery_score = track_mastery.mastery_score
            mastery_band  = track_mastery.mastery_band
        except Exception:
            mastery_score = 0.3
            mastery_band  = MasteryBand.DEVELOPING

        zpd_zone       = detect_zpd_zone(message)
        zpd_directives = get_quick_directives(zpd_zone, mastery_band)

        # Emit ZPD state so the UI can update the badge immediately
        yield _sse("zpd", {
            "zone": zpd_zone.value,
            "mastery_score": mastery_score,
            "mastery_band": mastery_band.value,
        })

        system_prompt = _build_conversation_prompt(
            topic=message[:120],  # first 120 chars as topic hint
            tracks=tracks,
            grade_level=grade_level,
            zpd_directives=zpd_directives,
        )

        # Build message list for Claude
        claude_messages = []
        for h in history[-10:]:  # cap at last 10 turns
            role = "user" if h.get("role") == "user" else "assistant"
            claude_messages.append({"role": role, "content": h.get("content", "")})
        claude_messages.append({"role": "user", "content": message})

        # Stream + parse
        async for event in parse_stream(_stream_claude(system_prompt, claude_messages)):
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
    automatically based on active tracks. No student-facing mode selection.

    The student_id in the body is used for mastery lookup.
    The JWT user is verified via the Authorization header (middleware).
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
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering for SSE
        },
    )
```

- [ ] **Step 3.4: Run tests to verify they pass**

```bash
cd adeline-brain
python -m pytest tests/test_conversation_api.py::test_build_conversation_prompt_includes_mode tests/test_conversation_api.py::test_build_conversation_prompt_blends_modes -v
```
Expected: 2 tests pass. (Auth tests require full app setup — run those after Task 4.)

- [ ] **Step 3.5: Commit**

```bash
cd adeline-brain
git add app/api/conversation.py tests/test_conversation_api.py
git commit -m "feat: POST /conversation/stream SSE endpoint"
```

---

## Task 4: Register Router

**Files:**
- Modify: `adeline-brain/app/main.py`

- [ ] **Step 4.1: Add the import and router registration**

In `app/main.py`, add after the last existing router import (near line 51, after `from app.api.realtime import router as realtime_router`):

```python
from app.api.conversation import router as conversation_router
```

Then in the `app.include_router(...)` block (find the section where all routers are registered), add:

```python
app.include_router(conversation_router)
```

- [ ] **Step 4.2: Verify the server starts**

```bash
cd adeline-brain
uvicorn app.main:app --reload --port 8000
```
Expected: server starts, no import errors. Check `http://localhost:8000/docs` — `/conversation/stream` should appear.

- [ ] **Step 4.3: Run auth test**

```bash
cd adeline-brain
python -m pytest tests/test_conversation_api.py::test_conversation_stream_requires_auth -v
```
Expected: PASS (401 returned for unauthenticated request).

- [ ] **Step 4.4: Commit**

```bash
cd adeline-brain
git add app/main.py
git commit -m "feat: register conversation router in main"
```

---

## Task 5: `brain-client.ts` — `streamConversation()`

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts`

- [ ] **Step 5.1: Add types and function**

Open `adeline-ui/src/lib/brain-client.ts`. Add after the last existing export (at the bottom of the file):

```typescript
// ── Conversation Streaming ────────────────────────────────────────────────────

export interface ConversationMessage {
  role: "user" | "adeline";
  content: string;
}

export type ConversationEvent =
  | { type: "text";  delta: string }
  | { type: "block"; block_type: string; content: string; title?: string; source_url?: string; [key: string]: unknown }
  | { type: "zpd";   zone: "FRUSTRATED" | "IN_ZPD" | "BORED"; mastery_score: number; mastery_band: string }
  | { type: "done" }
  | { type: "error"; message: string }

/**
 * Stream a conversation turn from Adeline.
 * Yields ConversationEvent objects as SSE events arrive.
 *
 * Usage:
 *   for await (const event of streamConversation({ ... })) {
 *     if (event.type === 'text') appendText(event.delta)
 *     if (event.type === 'block') renderBlock(event)
 *   }
 */
export async function* streamConversation(params: {
  studentId: string;
  message: string;
  track?: Track;
  gradeLevel: string;
  history: ConversationMessage[];
}): AsyncGenerator<ConversationEvent> {
  const response = await fetch(`${BRAIN_URL}/conversation/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      student_id: params.studentId,
      message: params.message,
      track: params.track ?? null,
      grade_level: params.gradeLevel,
      conversation_history: params.history.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    }),
  });

  if (!response.ok) {
    throw new Error(`Conversation stream failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("No response body from conversation stream");
  }

  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer    = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const dataStr = line.slice(6).trim();
        if (!dataStr) continue;
        try {
          const parsed = JSON.parse(dataStr);
          yield { type: currentEvent, ...parsed } as ConversationEvent;
        } catch {
          // skip malformed SSE data line
        }
        currentEvent = "";
      }
    }
  }
}
```

- [ ] **Step 5.2: Verify TypeScript compiles**

```bash
cd adeline-ui
pnpm tsc --noEmit
```
Expected: no type errors.

- [ ] **Step 5.3: Commit**

```bash
cd adeline-ui
git add src/lib/brain-client.ts
git commit -m "feat: streamConversation() SSE client with typed events"
```

---

## Task 6: `AdelineChatPanel.tsx` — Streaming Render Loop

**Files:**
- Modify: `adeline-ui/src/components/AdelineChatPanel.tsx`

This task is the largest UI change. Read the full current file before editing.

- [ ] **Step 6.1: Add `MessageSegment` type and update `Message` type**

At the top of `AdelineChatPanel.tsx`, find the `interface Message` definition. Replace it with:

```typescript
// A single segment within an Adeline message — either streamed text or an inline block.
type MessageSegment =
  | { kind: "text";  content: string }
  | { kind: "block"; block: import("@/lib/brain-client").ConversationEvent & { type: "block" } }

interface Message {
  id:         string;
  role:       "user" | "adeline";
  content:    string;    // full text content (for history)
  segments?:  MessageSegment[]; // interleaved text + blocks for streaming render
  zpd_zone?:  string;
  rich?:      RichContent;
  streaming?: boolean;   // true while SSE is still open
}
```

- [ ] **Step 6.2: Add `streamConversation` and `ConversationMessage` to imports**

Find the import from `@/lib/brain-client` and add:

```typescript
import {
  scaffold, generateLesson, pollLessonResult, listProjects, getProject, reportActivity,
  streamConversation,   // ADD
  type ConversationMessage, // ADD
  type ConversationEvent,   // ADD
  // ... rest of existing imports
} from "@/lib/brain-client";
```

- [ ] **Step 6.3: Add `conversationHistory` state**

Inside the `AdelineChatPanel` component, after the existing state declarations, add:

```typescript
const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
```

- [ ] **Step 6.4: Replace the send handler with streaming logic**

Find the existing `handleSend` (or equivalent submit) function. Replace the section that calls `generateLesson` / `scaffold` with:

```typescript
// ── Streaming send ──────────────────────────────────────────────────────────
const handleStreamSend = async (userMessage: string) => {
  if (!userMessage.trim() || isLoading) return;

  // 1. Append user message
  const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: userMessage };
  setMessages((prev) => [...prev, userMsg]);
  setInput("");
  setIsLoading(true);

  // 2. Append empty streaming Adeline message
  const adelineId = crypto.randomUUID();
  const adelineMsg: Message = {
    id: adelineId, role: "adeline", content: "", segments: [], streaming: true,
  };
  setMessages((prev) => [...prev, adelineMsg]);

  // Build history for this turn (exclude current user message — it's the `message` param)
  const historyForTurn: ConversationMessage[] = [
    ...conversationHistory,
    { role: "user", content: userMessage },
  ];

  try {
    let fullText = "";

    for await (const event of streamConversation({
      studentId,
      message: userMessage,
      gradeLevel,
      history: conversationHistory,
    })) {
      if (event.type === "text") {
        fullText += event.delta;
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== adelineId) return m;
            const lastSeg = m.segments?.[m.segments.length - 1];
            if (lastSeg?.kind === "text") {
              // Append to last text segment
              const updated = [...(m.segments ?? [])];
              updated[updated.length - 1] = { kind: "text", content: lastSeg.content + event.delta };
              return { ...m, segments: updated, content: fullText };
            }
            // Start new text segment
            return { ...m, segments: [...(m.segments ?? []), { kind: "text", content: event.delta }], content: fullText };
          })
        );
      }

      if (event.type === "block") {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== adelineId) return m;
            return {
              ...m,
              segments: [...(m.segments ?? []), { kind: "block", block: event as any }],
            };
          })
        );
      }

      if (event.type === "zpd") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === adelineId ? { ...m, zpd_zone: event.zone } : m
          )
        );
      }

      if (event.type === "done" || event.type === "error") {
        setMessages((prev) =>
          prev.map((m) => (m.id === adelineId ? { ...m, streaming: false } : m))
        );
      }
    }

    // Update conversation history for next turn
    setConversationHistory((prev) => [
      ...prev,
      { role: "user",    content: userMessage },
      { role: "adeline", content: fullText },
    ]);

  } catch (err) {
    console.error("[AdelineChatPanel] Stream error:", err);
    setMessages((prev) =>
      prev.map((m) =>
        m.id === adelineId
          ? { ...m, content: "Something went wrong. Please try again.", streaming: false }
          : m
      )
    );
  } finally {
    setIsLoading(false);
  }
};
```

- [ ] **Step 6.5: Add `GenUIRenderer` import**

Find the existing imports at the top of `AdelineChatPanel.tsx`. Add:

```typescript
import { GenUIRenderer } from "@/components/GenUIRenderer";
```

- [ ] **Step 6.6: Update the message renderer to handle segments**

Find the JSX that renders each Adeline message bubble. Add segment rendering:

```tsx
{/* Render streaming segments (text + inline blocks interleaved) */}
{msg.segments && msg.segments.length > 0 ? (
  <div className="space-y-3">
    {msg.segments.map((seg, i) =>
      seg.kind === "text" ? (
        <MessageContent key={i} content={seg.content} />
      ) : (
        <div key={i} className="my-2">
          <GenUIRenderer block={seg.block as any} studentId={studentId} lessonId="" />
        </div>
      )
    )}
    {msg.streaming && (
      <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
    )}
  </div>
) : (
  // Fallback: render plain content (non-streaming messages)
  <MessageContent content={msg.content} />
)}
```

- [ ] **Step 6.7: Remove `LessonContext` state**

Find `const [activeLessonContext, setActiveLessonContext] = useState<LessonContext | null>(null)` and remove it. Remove any references to `LessonContext` type and `setActiveLessonContext` calls throughout the component. The conversation history state replaces it.

- [ ] **Step 6.8: Verify TypeScript compiles**

```bash
cd adeline-ui
pnpm tsc --noEmit
```
Expected: no type errors. Fix any type mismatches before proceeding.

- [ ] **Step 6.9: Manual smoke test**

```bash
# Terminal 1
cd adeline-brain && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd adeline-ui && pnpm dev
```

Open `http://localhost:3000`, log in, navigate to the dashboard, type a message to Adeline.
Expected:
- Text streams in character by character (or in chunks)
- ZPD badge updates as soon as the response starts
- If Adeline surfaces a block, it renders inline below the text that preceded it
- After the block, text continues in a new segment below

- [ ] **Step 6.10: Commit**

```bash
cd adeline-ui
git add src/components/AdelineChatPanel.tsx
git commit -m "feat: streaming render loop with inline block injection"
```

---

## Task 7: Full Integration Run

- [ ] **Step 7.1: Run the full test suite**

```bash
# Brain tests
cd adeline-brain
python -m pytest tests/ -v --tb=short

# UI type check
cd ../adeline-ui
pnpm tsc --noEmit
```

Expected: all tests pass, no type errors.

- [ ] **Step 7.2: End-to-end smoke — each mode**

With both services running, test one conversation per mode:

| Track to use | Mode expected | Test message |
|---|---|---|
| `TRUTH_HISTORY` | Investigator | "Tell me about the Trail of Tears" |
| `CREATION_SCIENCE` | Lab | "How does photosynthesis work?" |
| `DISCIPLESHIP` | Dialogue | "What does Proverbs 3 say about wisdom?" |
| `CREATIVE_ECONOMY` | Workshop | "I want to learn how to price my pottery" |
| `CREATIVE_ECONOMY` + `HOMESTEADING` | Workshop + Lab blend | "How do I make and sell goat cheese?" |

For each: verify text streams, verify Adeline's voice matches the mode, verify any surfaced blocks render inline.

- [ ] **Step 7.3: Final commit**

```bash
cd /c/Users/Aarons/dearadeline-withlove
git add -A
git commit -m "feat: streaming conversation delivery complete — LearnLM-style GenUI"
```

---

## Known Gaps (post-launch, not in scope here)

| Gap | Notes |
|---|---|
| True token-by-token streaming | Claude's streaming API yields chunks — already wired. UI renders per-chunk. Further optimization possible. |
| Conversation persistence | History is passed per-turn; cap at last 10 turns. Long sessions should load from `conversation_store.py`. |
| Multi-track auto-detection | Currently uses explicit `track` param or defaults to `TRUTH_HISTORY`. Intent detection can be added to `_infer_tracks()` later. |
| Witness Protocol on streamed blocks | Blocks are injected by Adeline directly. For PRIMARY_SOURCE blocks in history/justice tracks, a post-emission Witness check can be added in `_conversation_sse()`. |
| Activity + project intents | Still handled by existing regex detection in `AdelineChatPanel` — route those to existing `reportActivity` / `listProjects` calls before falling through to `handleStreamSend`. |
