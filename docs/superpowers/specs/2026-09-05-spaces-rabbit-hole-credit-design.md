# Spaces: Always-Open Chat + Live Rabbit-Hole Credit — Design (Phase 2)

**Date:** 2026-09-05
**Status:** Approved, ready for implementation
**Author:** Claude (with Amber Renfroe)
**Builds on:** `2026-09-04-spaces-automatic-mastery-credit-design.md` (lesson-boundary credit) and Phase 1 (concurrent pace-driven slots).

## Problem

Two related gaps in how Spaces handle conversation:

1. Once a Space's activities are all completed, `SpacePlayer.tsx` hides the chat input entirely — the family can't ask follow-up questions or keep exploring in that same Space.
2. Credit is only ever tied to the pre-authored lesson plan's `concept_ids`. If a family's real conversation — mid-lesson or after completion — wanders into a genuine question that touches a different concept or standard, nothing notices or credits it. Adeline is supposed to give credit as concepts are mastered, not just as pre-planned blocks are checked off.

## Goal

- The Space's chat stays open indefinitely, even after every activity is finished.
- Every turn (not just lesson-boundary turns), the existing per-turn LLM evaluation also flags when the conversation surfaced something beyond the current planned activity, at one of two tiers:
  - **demonstrated** — a real question got a real, correct answer → full mastery credit, same pipeline as planned concepts.
  - **encountered** — a substantive question and answer, but not demonstrated to correctness → logged as encountered, never written to `StandardMastery`/BKT (would violate the non-exposure-alone rule).

## Non-goals

- No second LLM call. The existing per-turn evaluation call (`/api/spaces/turn`) already runs every turn; this adds one optional field to its existing output schema instead of a separate detection pass.
- No change to the lesson-boundary credit mechanism built in the prior design — this is additive, independent of it.
- Not building a UI to review/browse `ConceptEncounter` rows yet — just recording them so the capability exists.

## Design

### 1. Extend the per-turn evaluation schema

`adeline-ui/src/lib/spaces/schema.ts` (`spaceEvaluationSchema`) and the backend `SpaceEvaluation` Pydantic model (`spaces.py`) both gain:

```ts
off_plan_topic: z.object({
  concept_name: z.string(),
  track: z.string().optional(),  // falls back to the unit's own track if omitted
  tier: z.enum(["encountered", "demonstrated"]),
}).nullable().optional()
```

The `/api/spaces/turn` system prompt is updated to instruct the LLM: only set this when the conversation genuinely went beyond the current activity (a passing mention doesn't count); `"demonstrated"` requires the same correctness bar already used for planned concepts; `"encountered"` requires a real question and a real, substantive answer — not just a mention.

### 2. Backend: generalize the standards-matching helper

`spaces.py::_lesson_oas_standards(track, grade, lesson_content)` is renamed/generalized to `_topic_oas_standards(track, grade, topic_text)` — same pgvector query, just decoupled from "must come from pre-authored lesson blocks." `_lesson_oas_standards` becomes a thin wrapper calling it with the lesson's block content, so lesson-boundary crediting is unchanged.

### 3. Backend: handle `off_plan_topic` in `/transition`

After the existing lesson-boundary check, independently:

```
if body.off_plan_topic:
    standards = await _topic_oas_standards(
        body.off_plan_topic.track or experience_track, grade, body.off_plan_topic.concept_name,
    )
    if body.off_plan_topic.tier == "demonstrated":
        await record_mastery_credit(
            student_id=..., track=..., lesson_id=f"rabbit-hole-{slug(concept_name)}-{student_id}",
            oas_standards=standards, proficiency="APPROACHING",
            concept_credits=[ConceptCredit(concept_id=f"rabbit-hole:{slug(concept_name)}", concept_name=concept_name, quality=4)],
            evidence_sources=[{"type": "rabbit_hole_conversation", "concept": concept_name, "excerpt": ...}],
        )
    else:  # "encountered"
        await concept_encounter_store.record(student_id, concept_name, track, space_session_id)
```

Both legs are best-effort (logged, not raised) — same posture as lesson-boundary credit; a detection/credit hiccup must never block the turn the family is waiting on.

`lesson_id` for a rabbit-hole credit is synthesized from the concept name (not the planned lesson's id), so it lands as its own distinct portfolio/journal entry rather than overwriting the planned lesson's credit record.

### 4. New table: `ConceptEncounter`

```prisma
model ConceptEncounter {
  id             String   @id @default(uuid())
  studentId      String
  conceptName    String
  track          String
  spaceSessionId String
  encounteredAt  DateTime @default(now())

  @@index([studentId])
}
```

Purely observational — never read by any mastery/credit calculation. A future parent-facing view could list these ("introduced but not yet mastered") but that's out of scope here.

### 5. Frontend: keep the Space open past completion

`SpacePlayer.tsx`: the `status === 'completed'` branch currently replaces the chat input with a static paragraph. It instead renders the credited-concepts summary *and* keeps the chat input below it, unconditionally. No SpaceSession schema change needed — the backend already tolerates continued turns once pinned at the last block index (verified against the existing `/transition` advancement logic: `if index < len(blocks) - 1: index += 1` is simply a no-op once at the end).

`/api/spaces/turn`'s system prompt gains a branch: when `space.status === 'completed'`, stop instructing the LLM to pin itself to "activity N of N" and instead describe open-conversation mode — answer genuinely, keep watching for `off_plan_topic`.

## Error handling

- Both credit legs (`demonstrated` and `encountered`) are wrapped in try/except, logged on failure, never raised — consistent with lesson-boundary credit's posture.
- A malformed or missing `track` on `off_plan_topic` falls back to the unit's own track rather than failing.

## Testing

- Unit tests for `_topic_oas_standards` extraction being callable with arbitrary text (not just lesson blocks) — reuse existing pgvector-mock patterns from `_lesson_oas_standards` tests.
- Unit test: `off_plan_topic.tier == "demonstrated"` triggers `record_mastery_credit` with a synthesized rabbit-hole concept id and lesson id.
- Unit test: `off_plan_topic.tier == "encountered"` calls `concept_encounter_store.record` and does **not** call `record_mastery_credit` or touch `StandardMastery`/BKT.
- Unit test: no `off_plan_topic` present → neither path fires (regression guard, matches today's behavior).
- Frontend: `SpacePlayer` renders the chat input even when `status === 'completed'`.
