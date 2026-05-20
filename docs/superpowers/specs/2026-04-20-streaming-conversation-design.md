# Spec: Streaming Conversation — LearnLM-Style Delivery for Dear Adeline

**Date:** 2026-04-20
**Status:** Approved — ready for implementation planning
**Scope:** `adeline-brain` (new endpoint) + `adeline-ui` (`AdelineChatPanel`, `brain-client`)

---

## 1. Vision

Replace the batch generate → render → scaffold flow with a single streaming conversation.
Adeline talks. Blocks surface mid-sentence, like reaching for something off the shelf.
The conversation IS the lesson.

Nothing about Adeline's soul, worldview, persona, or the visual design changes.
The science (BKT, ZPD, SM-2, Witness Protocol, GraphRAG) stays intact.
Only the *delivery path* changes.

---

## 2. What Does Not Change

The following are preserved exactly:

- `adeline.config.toml` — persona, epistemology, Witness Protocol, all track definitions
- Witness Protocol (0.82 cosine threshold) — still gates all history/justice blocks
- BKT + ZPD engine — still runs on every turn
- SM-2 spaced repetition — still runs post-session
- GraphRAG (Neo4j) — still powers ZPD candidate selection
- pgvector Hippocampus — still provides semantic memory
- RegistrarAgent — still runs after every turn to log xAPI + CASE credits
- CognitiveTwin — still tracks working memory load, frustration, engagement
- ManagerAgent — still coordinates cognitive state routing
- All GenUI block components (`gen-ui/patterns/*`) — unchanged
- All dashboard, reading-nook, parent, projects, daily-bread components — unchanged
- `lessons/BlockRenderer.tsx` + `BlockWrapper.tsx` — unchanged
- Highlight & Ask (`TextSelectionMenu`, `/lesson/ask-context`) — unchanged
- ZPD badge — unchanged

---

## 3. Track → Mode Mapping

Modes are automatic. The student's agency is in *what* they explore, not *how*.
Adeline never names the mode — she just teaches that way.

| Track | Mode | Adeline's teaching voice |
|---|---|---|
| `TRUTH_HISTORY` | **Investigator** | Lead with a question or a discrepancy. Show the raw archive. "What do you notice?" |
| `JUSTICE_CHANGEMAKING` | **Investigator** | Follow the power. Name the capture tactic. Flip it for the changemaker. |
| `CREATION_SCIENCE` | **Lab** | Frame as prediction. "What would you expect?" Reveal through experiment. |
| `HOMESTEADING` | **Lab** | "What would this look like on your land?" Connect every concept to the homestead. |
| `HEALTH_NATUROPATHY` | **Dialogue** | "What does the body actually do here?" Reason together. |
| `GOVERNMENT_ECONOMICS` | **Investigator** | Follow the money. Trace incentives. Who profits? |
| `DISCIPLESHIP` | **Dialogue** | Reason through scripture together. Pull Fox translation when relevant. |
| `ENGLISH_LITERATURE` | **Dialogue** | Read carefully. Name what you see honestly. Speak into it with precision and courage. |
| `APPLIED_MATHEMATICS` | **Lab** | Real numbers. Real problem. Work it. |
| `CREATIVE_ECONOMY` | **Workshop** | What would you make? What would you charge? Connect to hands, market, margin. |

### Mode Blending

Modes are **not rules — they are voices**. When a conversation touches multiple tracks
(e.g., soap-making = Workshop + Lab + Applied Math), all relevant mode directives
are injected and Adeline moves between them as the conversation calls for it.
No hierarchy. No "primary fires first." She follows the thread.

The available block palette expands to cover all active tracks' block types.

---

## 4. Brain Changes (`adeline-brain`)

### 4.1 New Endpoint: `POST /conversation/stream`

**Replaces** the generate + scaffold pair as the primary student delivery path.
`/lesson/generate` and `/lesson/status/{job_id}` remain for legacy/background use.

**Request:**
```json
{
  "student_id": "...",
  "message": "I want to learn about the Dust Bowl",
  "track": "TRUTH_HISTORY",
  "grade_level": "9",
  "conversation_history": [
    { "role": "user",    "content": "..." },
    { "role": "adeline", "content": "..." }
  ]
}
```

Track is auto-detected from the message if not provided (using existing orchestrator
intent logic). If multiple tracks are detected, all are passed for mode blending.

**Response:** `text/event-stream` (SSE)

```
event: text
data: {"delta": "The government promised relief."}

event: text
data: {"delta": " But the records tell a different story."}

event: block
data: {"type": "PRIMARY_SOURCE", "title": "FSA Field Report, Oklahoma 1936", "content": "..."}

event: zpd
data: {"zone": "IN_ZPD", "mastery_score": 0.42, "mastery_band": "DEVELOPING"}

event: text
data: {"delta": "What do you notice about who wrote this, and when?"}

event: done
data: {}
```

### 4.2 System Prompt Structure

Each turn builds the system prompt in this order:

```
[Adeline persona from adeline.config.toml]

TODAY'S CONVERSATION: {topic}
ACTIVE TRACKS: {track_list}

TEACHING VOICES AVAILABLE:
{mode_directives_for_active_tracks}

Follow the conversation. Use whichever voice the moment calls for.

[ZPD + cognitive load + pedagogical directives — from existing pedagogical_directives.py]
[CognitiveTwin state — from existing cognitive_twin.py]
```

### 4.3 Mode Directives

```python
MODE_DIRECTIVES = {
    "INVESTIGATOR": """
You are in INVESTIGATOR mode.
- Lead with a question or a discrepancy — never an explanation.
- Show primary sources when you have them. Surface them mid-sentence with a <BLOCK> tag.
- Never summarize what the archive says. Show the raw material and ask what the student notices.
- "Follow the money" and "Who wrote this, and why?" are always valid questions.
""",
    "LAB": """
You are in LAB mode.
- Frame everything as an experiment or a prediction before revealing anything.
- Ask: "What would you expect to happen?" Surface lab missions and experiment cards inline.
- Connect every concept back to something testable on the homestead.
- "Let's run this" is your opening move.
""",
    "DIALOGUE": """
You are in DIALOGUE mode.
- Reason together, out loud. Ask "what do you think?" before telling them what you think.
- Pull in scripture when genuinely relevant — Fox translation, never decorative.
- Read carefully. Name what you see honestly. Speak into it with precision and courage.
- Surface SocraticDebate blocks when the student is ready to defend a position.
""",
    "WORKSHOP": """
You are in WORKSHOP mode.
- Connect everything to making, pricing, and selling real things.
- "What would you make with this?" and "What would you charge?" are always valid.
- Surface ProjectBuilder blocks when appropriate.
- Math lives in the workshop: materials, margins, market pricing.
"""
}
```

### 4.4 Block Injection Protocol

Adeline's system prompt instructs her to inject blocks via `<BLOCK>` tags mid-response:

```
The records tell a different story.

<BLOCK>
{
  "block_type": "PRIMARY_SOURCE",
  "title": "FSA Field Report, Oklahoma 1936",
  "content": "Families have been reduced to eating weeds...",
  "source_url": "...",
  "witness_score": 0.91
}
</BLOCK>

What do you notice about who wrote this, and when?
```

The stream parser in the brain:
1. Emits `text` events for text chunks
2. On encountering `<BLOCK>`, pauses text emission
3. Parses and validates the block JSON
4. Runs block through Witness Protocol if `block_type` is `PRIMARY_SOURCE` or `RESEARCH_MISSION`
5. Emits a `block` event
6. Resumes text emission

### 4.5 ZPD-Aware Block Selection

The system prompt includes which block types to prefer based on CognitiveTwin state:

- ZPD = `FRUSTRATED` → prefer `ScaffoldedProblem`, bridge via Witness Anchors
- ZPD = `BORED` → prefer `HardThingChallenge`, surface harder primary sources
- ZPD = `IN_ZPD` → prefer `SocraticDebate`, `QuizCard`, `LabGuide`
- High cognitive load → suppress complex blocks (MIND_MAP, DragDropTimeline)

### 4.6 RegistrarAgent Still Runs

After each turn, the RegistrarAgent runs fire-and-forget to emit xAPI statements
and CASE credit entries — same as today. No change to the credit pipeline.

---

## 5. UI Changes (`adeline-ui`)

### 5.1 `brain-client.ts` — New Function

```typescript
export type ConversationEvent =
  | { type: "text";  delta: string }
  | { type: "block"; block: LessonBlockResponse }
  | { type: "zpd";   zone: "FRUSTRATED" | "IN_ZPD" | "BORED"; mastery_score: number; mastery_band: string }
  | { type: "done" }

export async function* streamConversation(params: {
  studentId: string
  message: string
  track?: Track
  gradeLevel: string
  history: { role: "user" | "adeline"; content: string }[]
}): AsyncGenerator<ConversationEvent>
```

### 5.2 `AdelineChatPanel.tsx` — Three Changes Only

**Change 1: Replace API calls**
```typescript
// Remove:
const lesson = await generateLesson(...)
const reply  = await scaffold(...)

// Add:
const stream = streamConversation({ studentId, message, track, gradeLevel, history })
for await (const event of stream) { ... }
```

**Change 2: Streaming render loop**
```typescript
for await (const event of stream) {
  if (event.type === 'text') {
    appendToCurrentBubble(event.delta)       // streams text with cursor
  }
  if (event.type === 'block') {
    sealCurrentBubble()                       // freeze current text
    renderBlock(event.block)                  // BlockRenderer — unchanged
    openNewBubble()                           // new bubble below the block
  }
  if (event.type === 'zpd') {
    updateZPDBadge(event.zone)               // existing ZPDBadge — unchanged
  }
  if (event.type === 'done') {
    sealCurrentBubble()
  }
}
```

**Change 3: Remove `LessonContext` state**
Conversation history array replaces it. Each turn appends user message +
Adeline's full response (text + block references) to history.

### 5.3 What Is NOT Changed in the UI

- `GenUIRenderer.tsx` — unchanged
- `lessons/BlockRenderer.tsx` + `BlockWrapper.tsx` — unchanged
- `gen-ui/AgentThinkingState.tsx` — shows while stream starts, unchanged
- `gen-ui/TextSelectionMenu.tsx` — Highlight & Ask, unchanged
- All `gen-ui/patterns/*` — unchanged, now have natural path to surface mid-conversation
- ZPD badge — unchanged
- Project intent detection (`PROJECT_LIST_RE`) — unchanged
- Activity credit intent (`ACTIVITY_RE`) — unchanged
- `StudentStatusBar.tsx` — unchanged
- All dashboard, reading-nook, parent, projects, daily-bread components — unchanged

---

## 6. Block Palette by Mode

Which components surface naturally in each mode:

| Mode | Primary blocks | Secondary blocks |
|---|---|---|
| **Investigator** | `PRIMARY_SOURCE`, `RESEARCH_MISSION`, `Timeline`, `DragDropTimeline` | `MindMap`, `QuizCard` |
| **Lab** | `LabGuide`, `ExperimentCard`, `ScaffoldedProblem` | `QuizCard`, `LiveChart` |
| **Dialogue** | `SocraticDebate`, `Flashcard`, `PRIMARY_SOURCE` | `MindMap`, `QuizCard` |
| **Workshop** | `ProjectBuilder`, `ScaffoldedProblem` | `LiveChart`, `QuizCard` |

ZPD overrides apply across all modes:
- FRUSTRATED → `ScaffoldedProblem` promoted regardless of mode
- BORED → `HardThingChallenge` promoted regardless of mode

---

## 7. Files Modified

### `adeline-brain`
| File | Change |
|---|---|
| `app/api/conversation.py` | **New** — SSE streaming endpoint |
| `app/main.py` | Register new `/conversation` router |
| `app/algorithms/pedagogical_directives.py` | Add mode directive injection |

### `adeline-ui`
| File | Change |
|---|---|
| `src/lib/brain-client.ts` | Add `streamConversation()` + `ConversationEvent` types |
| `src/components/AdelineChatPanel.tsx` | Replace API calls, add streaming render loop, remove `LessonContext` |

**Total files changed: 5**

---

## 8. What This Is Not

- Not a redesign of the visual identity
- Not a change to Adeline's persona or worldview
- Not a new block type (all components already exist)
- Not a replacement of the lesson generation pipeline (legacy path preserved)
- Not a change to auth, billing, parent dashboard, bookshelf, transcript, or any other feature
- Not an override of the Witness Protocol

---

## 9. Known Gaps (Post-Launch)

| Gap | Notes |
|---|---|
| Streaming upgrade | SSE is the right foundation; true token-by-token streaming requires Anthropic streaming API integration in the conversation endpoint |
| Mode blending UI hint | Consider a subtle track badge showing active tracks (not modes) so students know what they're exploring |
| Conversation persistence | History is currently passed per-turn; long conversations should be stored in `conversation_store.py` and loaded by session |
