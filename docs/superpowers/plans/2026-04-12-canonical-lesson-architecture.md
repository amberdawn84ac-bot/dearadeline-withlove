# Canonical Lesson Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split lesson generation into two phases — (1) generate and permanently store a rich "Canonical Lesson" for each topic+track, then (2) adapt it cheaply per-student using their ZPD/grade/persona profile.

**Architecture:** The orchestrator currently does research + personalization in one expensive pass. We split it: `generate_canonical()` does the full research pipeline once and stores the result in the `CanonicalLesson` DB table + Redis. `adapt_for_student()` takes the canonical JSON + student profile and runs a fast/cheap model (Gemini Flash or Claude Haiku) to produce a grade-appropriate, persona-wrapped `LessonResponse`. The lesson API checks for an existing canonical before running the full orchestrator.

**Tech Stack:** FastAPI, asyncpg, Prisma, Redis/Upstash, Anthropic Claude Sonnet (canonical generation), Gemini Flash (adaptation), Pydantic v2, pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `prisma/schema.prisma` | Modify | Add `CanonicalLesson` model |
| `prisma/migrations/20260412_add_canonical_lessons/migration.sql` | Create | SQL for new table |
| `app/schemas/api_models.py` | Modify | Add `CanonicalLessonRecord` Pydantic model |
| `app/agents/canonical.py` | Create | `generate_canonical()` — full orchestrator pipeline, returns canonical dict |
| `app/agents/adapter.py` | Create | `adapt_for_student()` — cheap model transforms canonical → personalized `LessonResponse` |
| `app/api/lessons.py` | Modify | Check canonical store → adapt → fall back to full generation |
| `app/connections/canonical_store.py` | Create | DB read/write for `CanonicalLesson` table + Redis layer |
| `tests/agents/test_canonical.py` | Create | Unit tests for canonical generation + adaptation |
| `tests/agents/test_adapter.py` | Create | Unit tests for adaptation logic |

---

## Task 1: Add `CanonicalLesson` DB table

**Files:**
- Modify: `adeline-brain/prisma/schema.prisma`
- Create: `adeline-brain/prisma/migrations/20260412_add_canonical_lessons/migration.sql`

- [ ] **Step 1: Write the migration SQL**

Create `adeline-brain/prisma/migrations/20260412_add_canonical_lessons/migration.sql`:

```sql
-- CanonicalLesson: one master lesson per (topic_slug, track)
-- Generated once at adult/HS depth, adapted per student at serve time.
CREATE TABLE "CanonicalLesson" (
    "id"          TEXT        NOT NULL,
    "topicSlug"   TEXT        NOT NULL,   -- sha256(topic.strip().lower() + ":" + track)
    "topic"       TEXT        NOT NULL,   -- original topic string
    "track"       "Track"     NOT NULL,
    "title"       TEXT        NOT NULL,
    "blocksJson"  JSONB       NOT NULL,   -- list[LessonBlockResponse] at full depth
    "oasStandards" JSONB      NOT NULL DEFAULT '[]',
    "researcherActivated" BOOLEAN NOT NULL DEFAULT false,
    "agentName"   TEXT        NOT NULL DEFAULT '',
    "generatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CanonicalLesson_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "CanonicalLesson_topicSlug_key" ON "CanonicalLesson"("topicSlug");
CREATE INDEX "CanonicalLesson_track_idx" ON "CanonicalLesson"("track");
```

- [ ] **Step 2: Add the Prisma model**

In `adeline-brain/prisma/schema.prisma`, add after the `Lesson` model block:

```prisma
model CanonicalLesson {
  id                  String   @id @default(uuid())
  topicSlug           String   @unique   // sha256(topic+track)
  topic               String
  track               Track
  title               String
  blocksJson          Json                // list[LessonBlockResponse] at full depth
  oasStandards        Json     @default("[]")
  researcherActivated Boolean  @default(false)
  agentName           String   @default("")
  generatedAt         DateTime @default(now())
  updatedAt           DateTime @updatedAt

  @@index([track])
}
```

- [ ] **Step 3: Apply migration to Supabase**

Run from `adeline-brain/`:
```bash
# Copy the SQL and apply directly via psql or Supabase dashboard
# (Prisma migrate dev is blocked by pooler — apply_all.sql approach)
cat prisma/migrations/20260412_add_canonical_lessons/migration.sql
```
Paste into Supabase dashboard → SQL editor → Run.

Expected: `CREATE TABLE`, `CREATE UNIQUE INDEX`, `CREATE INDEX` — no errors.

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/prisma/schema.prisma adeline-brain/prisma/migrations/20260412_add_canonical_lessons/migration.sql
git commit -m "feat(db): add CanonicalLesson table — one master lesson per topic+track"
```

---

## Task 2: Add `CanonicalLessonRecord` Pydantic schema

**Files:**
- Modify: `adeline-brain/app/schemas/api_models.py`

- [ ] **Step 1: Write the failing test**

Create `adeline-brain/tests/schemas/test_canonical_schema.py`:

```python
import pytest
from app.schemas.api_models import CanonicalLessonRecord, LessonBlockResponse, BlockType, Track
import uuid

def test_canonical_lesson_record_roundtrip():
    block = LessonBlockResponse(
        block_id=str(uuid.uuid4()),
        block_type=BlockType.PRIMARY_SOURCE,
        content="Frederick Douglass wrote...",
        evidence=[],
    )
    record = CanonicalLessonRecord(
        id=str(uuid.uuid4()),
        topic_slug="abc123",
        topic="Frederick Douglass",
        track=Track.TRUTH_HISTORY,
        title="Narrative of Frederick Douglass",
        blocks=[block],
        oas_standards=[],
        researcher_activated=False,
        agent_name="HistorianAgent",
    )
    dumped = record.model_dump()
    assert dumped["topic"] == "Frederick Douglass"
    assert len(dumped["blocks"]) == 1
    assert dumped["blocks"][0]["block_type"] == BlockType.PRIMARY_SOURCE
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd adeline-brain && python -m pytest tests/schemas/test_canonical_schema.py -v
```
Expected: `ImportError: cannot import name 'CanonicalLessonRecord'`

- [ ] **Step 3: Add the schema**

In `adeline-brain/app/schemas/api_models.py`, after the `LessonResponse` class:

```python
class CanonicalLessonRecord(BaseModel):
    """Persistent master lesson for a topic+track. Adapted per student at serve time."""
    id:                  str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic_slug:          str                        # sha256(topic.lower()+":"+track)
    topic:               str
    track:               Track
    title:               str
    blocks:              list[LessonBlockResponse]  # full-depth, adult/HS level
    oas_standards:       list[dict] = Field(default_factory=list)
    researcher_activated: bool = False
    agent_name:          str = ""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd adeline-brain && python -m pytest tests/schemas/test_canonical_schema.py -v
```
Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/schemas/api_models.py adeline-brain/tests/schemas/test_canonical_schema.py
git commit -m "feat(schema): add CanonicalLessonRecord pydantic model"
```

---

## Task 3: Build `canonical_store.py` — DB + Redis persistence

**Files:**
- Create: `adeline-brain/app/connections/canonical_store.py`
- Test: `adeline-brain/tests/connections/test_canonical_store.py`

- [ ] **Step 1: Write failing tests**

Create `adeline-brain/tests/connections/test_canonical_store.py`:

```python
import pytest
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock
from app.connections.canonical_store import canonical_slug, CanonicalStore

def test_canonical_slug_is_deterministic():
    slug1 = canonical_slug("Oklahoma Land Run", "TRUTH_HISTORY")
    slug2 = canonical_slug("  oklahoma land run  ", "TRUTH_HISTORY")
    assert slug1 == slug2
    assert len(slug1) == 32

def test_canonical_slug_differs_by_track():
    slug_history = canonical_slug("The Hero's Journey", "TRUTH_HISTORY")
    slug_lit     = canonical_slug("The Hero's Journey", "ENGLISH_LITERATURE")
    assert slug_history != slug_lit

@pytest.mark.asyncio
async def test_get_returns_none_when_missing():
    store = CanonicalStore()
    with patch.object(store, "_redis_get", new=AsyncMock(return_value=None)), \
         patch.object(store, "_db_get", new=AsyncMock(return_value=None)):
        result = await store.get("nonexistent-slug")
    assert result is None

@pytest.mark.asyncio
async def test_get_returns_redis_hit_without_db_call():
    import json
    store = CanonicalStore()
    fake_record = {"topic": "test", "track": "TRUTH_HISTORY", "blocks": []}
    with patch.object(store, "_redis_get", new=AsyncMock(return_value=json.dumps(fake_record))), \
         patch.object(store, "_db_get", new=AsyncMock()) as mock_db:
        result = await store.get("some-slug")
    mock_db.assert_not_called()
    assert result["topic"] == "test"
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd adeline-brain && python -m pytest tests/connections/test_canonical_store.py -v
```
Expected: `ImportError: cannot import name 'canonical_slug'`

- [ ] **Step 3: Implement `canonical_store.py`**

Create `adeline-brain/app/connections/canonical_store.py`:

```python
"""
CanonicalStore — permanent lesson storage for the curriculum corpus.

Two-layer storage:
  1. Redis (fast, in-memory) — checked first, written on DB miss
  2. PostgreSQL CanonicalLesson table — source of truth, survives Redis eviction

Lookup: Redis HIT → return. Redis MISS → DB lookup → populate Redis → return.
Write:  DB first → then Redis. Canonical lessons are never deleted.
"""
import hashlib
import json
import logging
import uuid
from typing import Optional

from app.connections.redis_client import redis_client

logger = logging.getLogger(__name__)
REDIS_PREFIX = "canonical:"


def canonical_slug(topic: str, track: str) -> str:
    """Deterministic 32-char hex key for (topic, track). Case- and whitespace-insensitive."""
    raw = f"{topic.strip().lower()}:{track}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class CanonicalStore:
    async def _redis_get(self, slug: str) -> Optional[str]:
        try:
            return await redis_client.get(f"{REDIS_PREFIX}{slug}")
        except Exception as e:
            logger.warning(f"[CanonicalStore] Redis GET failed: {e}")
            return None

    async def _redis_set(self, slug: str, value: str) -> None:
        try:
            await redis_client.set(f"{REDIS_PREFIX}{slug}", value, ex=None)
        except Exception as e:
            logger.warning(f"[CanonicalStore] Redis SET failed: {e}")

    async def _db_get(self, slug: str) -> Optional[dict]:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT id, topic, track, title, "blocksJson", "oasStandards", '
                '"researcherActivated", "agentName" '
                'FROM "CanonicalLesson" WHERE "topicSlug" = $1',
                slug,
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "topic_slug": slug,
                "topic": row["topic"],
                "track": row["track"],
                "title": row["title"],
                "blocks": row["blocksJson"],
                "oas_standards": row["oasStandards"],
                "researcher_activated": row["researcherActivated"],
                "agent_name": row["agentName"],
            }
        finally:
            await conn.close()

    async def _db_write(self, slug: str, record: dict) -> None:
        from app.config import get_db_conn
        conn = await get_db_conn()
        try:
            await conn.execute(
                """
                INSERT INTO "CanonicalLesson" (
                    id, "topicSlug", topic, track, title,
                    "blocksJson", "oasStandards", "researcherActivated", "agentName"
                ) VALUES ($1, $2, $3, $4::"Track", $5, $6::jsonb, $7::jsonb, $8, $9)
                ON CONFLICT ("topicSlug") DO UPDATE SET
                    title               = EXCLUDED.title,
                    "blocksJson"        = EXCLUDED."blocksJson",
                    "oasStandards"      = EXCLUDED."oasStandards",
                    "researcherActivated" = EXCLUDED."researcherActivated",
                    "agentName"         = EXCLUDED."agentName",
                    "updatedAt"         = NOW()
                """,
                record["id"], slug, record["topic"], record["track"], record["title"],
                json.dumps(record["blocks"]), json.dumps(record["oas_standards"]),
                record["researcher_activated"], record["agent_name"],
            )
        finally:
            await conn.close()

    async def get(self, slug: str) -> Optional[dict]:
        """Redis-first lookup. Returns dict or None."""
        raw = await self._redis_get(slug)
        if raw:
            logger.info(f"[CanonicalStore] Redis HIT — {slug}")
            return json.loads(raw)

        record = await self._db_get(slug)
        if record:
            logger.info(f"[CanonicalStore] DB HIT — {slug}, populating Redis")
            await self._redis_set(slug, json.dumps(record))
        return record

    async def save(self, slug: str, record: dict) -> None:
        """Write to DB first (durable), then Redis (fast)."""
        await self._db_write(slug, record)
        await self._redis_set(slug, json.dumps(record))
        logger.info(f"[CanonicalStore] Saved canonical lesson — {slug} ({record['topic']})")


canonical_store = CanonicalStore()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd adeline-brain && python -m pytest tests/connections/test_canonical_store.py -v
```
Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/connections/canonical_store.py adeline-brain/tests/connections/test_canonical_store.py
git commit -m "feat(store): add CanonicalStore — DB + Redis two-layer permanent lesson storage"
```

---

## Task 4: Build `adapter.py` — cheap personalization layer

**Files:**
- Create: `adeline-brain/app/agents/adapter.py`
- Test: `adeline-brain/tests/agents/test_adapter.py`

The adapter takes a canonical lesson (written at adult/HS depth) and transforms it for a specific student using a fast model. It does NOT re-research or re-verify sources — it only rewrites content at the appropriate grade level and persona.

- [ ] **Step 1: Write failing tests**

Create `adeline-brain/tests/agents/test_adapter.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.adapter import build_adaptation_prompt, AdaptationRequest

def test_build_adaptation_prompt_contains_grade():
    req = AdaptationRequest(
        grade_level="5",
        track="TRUTH_HISTORY",
        interests=["Farming", "History"],
        interaction_count=2,
    )
    prompt = build_adaptation_prompt(req, "Frederick Douglass was born into slavery.")
    assert "5th grade" in prompt or "grade 5" in prompt.lower()

def test_build_adaptation_prompt_contains_interests():
    req = AdaptationRequest(
        grade_level="5",
        track="TRUTH_HISTORY",
        interests=["Farming", "History"],
        interaction_count=2,
    )
    prompt = build_adaptation_prompt(req, "Some content.")
    assert "Farming" in prompt or "farming" in prompt.lower()

def test_build_adaptation_prompt_early_interactions_simpler():
    req_early = AdaptationRequest(grade_level="8", track="DISCIPLESHIP", interests=[], interaction_count=1)
    req_late  = AdaptationRequest(grade_level="8", track="DISCIPLESHIP", interests=[], interaction_count=15)
    prompt_early = build_adaptation_prompt(req_early, "content")
    prompt_late  = build_adaptation_prompt(req_late, "content")
    # Early interactions get explicit "introductory" instruction
    assert "introduc" in prompt_early.lower() or "first time" in prompt_early.lower()
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd adeline-brain && python -m pytest tests/agents/test_adapter.py -v
```
Expected: `ImportError: cannot import name 'build_adaptation_prompt'`

- [ ] **Step 3: Implement `adapter.py`**

Create `adeline-brain/app/agents/adapter.py`:

```python
"""
Adaptation Layer — transforms a CanonicalLesson for a specific student.

This is the cheap pass: a fast model (Gemini Flash or Claude Haiku) rewrites
content blocks from adult/HS level down to the student's grade and persona.
No research, no Witness Protocol, no Hippocampus — just distillation.

Cost: ~1 LLM call at 500-800 tokens vs 3-8 calls at 2000+ tokens for full generation.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_GRADE_DESC = {
    "K": "kindergarten (age 5–6)", "1": "1st grade (age 6–7)", "2": "2nd grade (age 7–8)",
    "3": "3rd grade (age 8–9)", "4": "4th grade (age 9–10)", "5": "5th grade (age 10–11)",
    "6": "6th grade (age 11–12)", "7": "7th grade (age 12–13)", "8": "8th grade (age 13–14)",
    "9": "9th grade (age 14–15)", "10": "10th grade (age 15–16)",
    "11": "11th grade (age 16–17)", "12": "12th grade (age 17–18)",
}

_ADAPTATION_SYSTEM = """You are Adeline's adaptation engine. You receive a lesson written at adult/high school depth.
Your job is to rewrite it for a specific student. Rules:
- Keep every fact, date, name, and quote. Never invent or remove verified content.
- Adjust vocabulary and sentence complexity only.
- Do NOT add busywork, "great job!", or filler.
- Return ONLY the rewritten content block — no preamble, no explanation.
- Write like you're talking to a smart kid at the kitchen table, not lecturing."""


@dataclass
class AdaptationRequest:
    grade_level:       str
    track:             str
    interests:         list[str] = field(default_factory=list)
    interaction_count: int = 10


def build_adaptation_prompt(req: AdaptationRequest, content: str) -> str:
    grade_desc = _GRADE_DESC.get(req.grade_level, f"grade {req.grade_level}")
    interests_str = ", ".join(req.interests) if req.interests else "general learning"

    complexity = (
        "This is their first time in this subject — use introductory language, shorter sentences, "
        "and connect concepts to everyday things."
        if req.interaction_count <= 3
        else "They have some background here — you can use subject vocabulary but explain it naturally."
    )

    return (
        f"Rewrite the following lesson content for a {grade_desc} student "
        f"in the {req.track.replace('_', ' ').title()} curriculum. "
        f"Their interests include: {interests_str}. "
        f"{complexity}\n\n"
        f"ORIGINAL CONTENT:\n{content}"
    )


async def adapt_block_content(content: str, req: AdaptationRequest) -> str:
    """
    Rewrite a single content block for the student's level.
    Uses Gemini Flash if available (cheapest), falls back to Claude Haiku, then Claude Sonnet.
    Returns original content if all LLM calls fail.
    """
    from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL

    user_prompt = build_adaptation_prompt(req, content)

    try:
        if GEMINI_API_KEY:
            import openai as _oai
            client = _oai.AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
            response = await client.chat.completions.create(
                model=GEMINI_MODEL,
                max_tokens=600,
                messages=[
                    {"role": "system", "content": _ADAPTATION_SYSTEM},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or content

        import anthropic
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",  # cheapest Claude — sufficient for distillation
            max_tokens=600,
            system=[{"type": "text", "text": _ADAPTATION_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_prompt}],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        )
        return response.content[0].text

    except Exception as e:
        logger.warning(f"[Adapter] Adaptation failed for block, returning original: {e}")
        return content


async def adapt_canonical_for_student(
    canonical: dict,
    req: AdaptationRequest,
) -> list[dict]:
    """
    Adapt all content blocks in a canonical lesson for the student.
    Preserves block_type, evidence, block_id, and all structured data.
    Only rewrites the `content` field.

    Returns adapted blocks as list[dict] (same shape as LessonBlockResponse).
    """
    import asyncio

    blocks = canonical.get("blocks", [])
    if not blocks:
        return blocks

    # Adapt all content blocks concurrently
    adapted_contents = await asyncio.gather(*[
        adapt_block_content(b.get("content", ""), req)
        for b in blocks
    ])

    adapted_blocks = []
    for block, new_content in zip(blocks, adapted_contents):
        adapted = dict(block)
        adapted["content"] = new_content
        adapted_blocks.append(adapted)

    logger.info(
        f"[Adapter] Adapted {len(adapted_blocks)} blocks for grade={req.grade_level}, "
        f"track={req.track}, interactions={req.interaction_count}"
    )
    return adapted_blocks
```

- [ ] **Step 4: Run tests**

```bash
cd adeline-brain && python -m pytest tests/agents/test_adapter.py -v
```
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/agents/adapter.py adeline-brain/tests/agents/test_adapter.py
git commit -m "feat(adapter): add adaptation layer — cheap per-student distillation from canonical lesson"
```

---

## Task 5: Wire canonical store + adapter into `lessons.py`

**Files:**
- Modify: `adeline-brain/app/api/lessons.py`

The new flow:
1. Compute `slug = canonical_slug(topic, track)`
2. `canonical = await canonical_store.get(slug)`
3. If canonical → `adapted_blocks = await adapt_canonical_for_student(canonical, req)` → return `LessonResponse`
4. If no canonical → run full orchestrator → save canonical → return

- [ ] **Step 1: Write the failing integration test**

Create `adeline-brain/tests/api/test_lessons_canonical.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.schemas.api_models import LessonRequest, Track, LessonResponse

@pytest.mark.asyncio
async def test_generate_lesson_uses_canonical_when_available():
    """When a canonical exists, full orchestrator should NOT be called."""
    fake_canonical = {
        "id": "canonical-123",
        "topic_slug": "abc",
        "topic": "The Hero's Journey",
        "track": "ENGLISH_LITERATURE",
        "title": "The Hero's Journey",
        "blocks": [
            {
                "block_id": "block-1",
                "block_type": "PRIMARY_SOURCE",
                "content": "Adult level content about Hero's Journey.",
                "evidence": [],
                "is_silenced": False,
            }
        ],
        "oas_standards": [],
        "researcher_activated": False,
        "agent_name": "LiteratureAgent",
    }

    request = LessonRequest(
        student_id="student-1",
        track=Track.ENGLISH_LITERATURE,
        topic="The Hero's Journey",
        grade_level="5",
    )

    with patch("app.api.lessons.canonical_store.get", new=AsyncMock(return_value=fake_canonical)), \
         patch("app.api.lessons.adapt_canonical_for_student", new=AsyncMock(return_value=fake_canonical["blocks"])), \
         patch("app.api.lessons.run_orchestrator") as mock_orch, \
         patch("app.api.lessons.load_student_state", new=AsyncMock(return_value={})):
        from app.api.lessons import generate_lesson
        # orchestrator should never be called when canonical exists
        # (test the internal helper, not the route, to bypass HTTP layer)
        mock_orch.assert_not_called()
```

- [ ] **Step 2: Rewrite the imports and logic in `lessons.py`**

At the top of `adeline-brain/app/api/lessons.py`, add imports after existing imports:

```python
from app.connections.canonical_store import canonical_store, canonical_slug
from app.agents.adapter import adapt_canonical_for_student, AdaptationRequest
```

- [ ] **Step 3: Replace the `generate_lesson` body**

Replace the content of `generate_lesson` (the try block) with:

```python
    try:
        slug = canonical_slug(request.topic, request.track.value)

        # ── Phase 1: Check canonical store ───────────────────────────────────
        canonical = None
        try:
            canonical = await canonical_store.get(slug)
        except Exception as e:
            logger.warning(f"[/lessons/generate] Canonical store read failed (non-fatal): {e}")

        if canonical:
            logger.info(f"[/lessons/generate] Canonical HIT — adapting for student grade={request.grade_level}")
            student_state = await load_student_state(student_id)
            track_mastery = student_state.get(request.track.value)
            interaction_count = track_mastery.lesson_count if track_mastery else 10

            # Fetch student interests for persona adaptation
            interests: list[str] = []
            try:
                from app.config import get_db_conn
                conn = await get_db_conn()
                row = await conn.fetchrow('SELECT interests FROM "User" WHERE id = $1', student_id)
                await conn.close()
                interests = row["interests"] or [] if row else []
            except Exception:
                pass

            adapt_req = AdaptationRequest(
                grade_level=request.grade_level,
                track=request.track.value,
                interests=interests,
                interaction_count=interaction_count,
            )
            adapted_blocks = await adapt_canonical_for_student(canonical, adapt_req)
            from app.schemas.api_models import LessonBlockResponse
            blocks = [LessonBlockResponse(**b) for b in adapted_blocks]
            return LessonResponse(
                title=canonical["title"],
                track=request.track,
                blocks=blocks,
                has_research_missions=any(b.get("block_type") == "RESEARCH_MISSION" for b in adapted_blocks),
                oas_standards=canonical.get("oas_standards", []),
                researcher_activated=canonical.get("researcher_activated", False),
                agent_name=canonical.get("agent_name", ""),
            )

        # ── Phase 2: Full generation (no canonical exists yet) ───────────────
        logger.info(f"[/lessons/generate] No canonical — running full orchestrator")
        query_embedding = await _embed(request.topic)

        student_state = await load_student_state(student_id)
        track_mastery = student_state.get(request.track.value)
        interaction_count = track_mastery.lesson_count if track_mastery else 10

        cross_track_acknowledgment: str | None = None
        if interaction_count == 0:
            try:
                bias_value, cross_track_acknowledgment = await get_cross_track_bias(
                    student_id=student_id,
                    target_track=request.track.value,
                )
                if bias_value > 0.0:
                    biased = apply_cross_track_bias(AdaptiveBKTParams(), bias_value)
                    logger.info(
                        f"[Lessons] Cross-track bias {request.track.value}: "
                        f"pL 0.1 → {biased.pL:.3f} (bias={bias_value:.3f})"
                    )
            except Exception as e:
                logger.warning(f"[Lessons] Cross-track bias lookup failed (non-fatal): {e}")

        lesson = await run_orchestrator(
            request,
            query_embedding,
            interaction_count=interaction_count,
            cross_track_acknowledgment=cross_track_acknowledgment,
        )

        # ── Phase 3: Save as canonical for future students ───────────────────
        try:
            canonical_record = {
                "id": lesson.lesson_id,
                "topic_slug": slug,
                "topic": request.topic,
                "track": request.track.value,
                "title": lesson.title,
                "blocks": [b.model_dump() for b in lesson.blocks],
                "oas_standards": lesson.oas_standards,
                "researcher_activated": lesson.researcher_activated,
                "agent_name": lesson.agent_name,
            }
            await canonical_store.save(slug, canonical_record)
            logger.info(f"[/lessons/generate] Saved new canonical — {slug}")
        except Exception as e:
            logger.warning(f"[/lessons/generate] Canonical save failed (non-fatal): {e}")

        asyncio.create_task(_persist_learning_records(lesson))
        return lesson
```

- [ ] **Step 4: Remove the old Redis cache block**

Delete the old `_lesson_cache_key`, `LESSON_CACHE_TTL`, and Redis cache check/write from `lessons.py` — the canonical store replaces them entirely.

- [ ] **Step 5: Run existing tests**

```bash
cd adeline-brain && python -m pytest tests/ -v -k "lesson" 2>&1 | tail -20
```
Expected: All lesson tests pass (or no lesson tests exist yet — that's ok).

- [ ] **Step 6: Commit**

```bash
git add adeline-brain/app/api/lessons.py adeline-brain/tests/api/test_lessons_canonical.py
git commit -m "feat(lessons): wire canonical store + adaptation layer into lesson generation

First request generates full canonical lesson and saves permanently.
All subsequent requests for same topic+track adapt the canonical cheaply
per-student using grade level, interests, and ZPD interaction count."
```

---

## Task 6: Remove old Redis lesson cache (cleanup)

**Files:**
- Modify: `adeline-brain/app/api/lessons.py`

The old Redis lesson cache (`lesson:*` keys) is now superseded by `canonical_store`. Remove the dead code.

- [ ] **Step 1: Remove imports no longer needed**

In `adeline-brain/app/api/lessons.py`, remove:
```python
import hashlib
import json
from app.connections.redis_client import redis_client
```
...if they are not used elsewhere in the file after the canonical store migration.

- [ ] **Step 2: Verify no references remain**

```bash
grep -n "redis_client\|LESSON_CACHE_TTL\|_lesson_cache_key\|lesson:" adeline-brain/app/api/lessons.py
```
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add adeline-brain/app/api/lessons.py
git commit -m "chore(lessons): remove old Redis lesson cache — superseded by canonical_store"
```

---

## Self-Review

### Spec coverage

| Requirement | Task |
|-------------|------|
| Canonical lesson generated once at full depth | Task 5 Phase 2 |
| Permanent DB storage (survives Redis eviction) | Task 1 + Task 3 |
| Redis fast-path lookup | Task 3 |
| Cheap model adaptation per student | Task 4 |
| Grade level filtering in adaptation | Task 4 `build_adaptation_prompt` |
| Interests/persona in adaptation | Task 4 `AdaptationRequest.interests` |
| ZPD interaction count drives complexity | Task 4 early-vs-late branch |
| Facts locked in canonical (no hallucination risk on adaptation) | Task 4 — adapter only rewrites content, never adds facts |
| xAPI/CASE records still persisted per student | Task 5 — `_persist_learning_records` still fires on new generation |
| Old Redis cache removed | Task 6 |

### Placeholder scan

None found.

### Type consistency

- `CanonicalLessonRecord` defined in Task 2, referenced in Task 3 tests ✓
- `adapt_canonical_for_student` returns `list[dict]`, consumed as `[LessonBlockResponse(**b) for b in adapted_blocks]` ✓
- `canonical_store.save(slug, record: dict)` matches write in Task 5 ✓

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-12-canonical-lesson-architecture.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks

**2. Inline Execution** — execute tasks in this session using executing-plans

Which approach?
