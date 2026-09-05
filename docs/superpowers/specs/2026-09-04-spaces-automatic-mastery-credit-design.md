# Spaces: Automatic Mastery Credit — Design

**Date:** 2026-09-04
**Status:** Approved, ready for implementation planning
**Author:** Claude (with Amber Renfroe)

## Problem

Dear Adeline's "Spaces" feature (`adeline-brain/app/api/spaces.py`, `adeline-ui/src/components/spaces/SpacePlayer.tsx`) is a persistent, server-paced unit walkthrough modeled on SchoolAI Spaces: a family enters a Space for a unit, chats through activities one at a time, and an LLM evaluation (`correct`/`partial`/`incorrect`/`not_answered`) gates advancement to the next activity via the version-guarded `POST /brain/spaces/{student_id}/{plan_item_id}/transition` endpoint.

This mechanism works end to end, but a completed Space is currently a dead end. When every block is completed (`SpaceSession.status = 'completed'`), `SpacePlayer.tsx` shows a static message — *"You reached the end of this unit Space. Record evidence to have your understanding evaluated."* — with no button, link, or call into any credit/transcript system. This contradicts Adeline's core job (per `CLAUDE.md`): crediting demonstrated mastery to the student's transcript as concepts are mastered, not leaving it to a disconnected manual step.

The parallel non-Space lesson renderer, `FamilyCanonicalLesson.tsx`, *does* have a working credit path: a `useLessonSeal` hook that collects a reflection/artifact/quiz result and calls `POST /journal/seal`, which upserts `student_journal` (portfolio + track progress), writes `StandardMastery` rows (`curriculum_graph.record_standard_mastery`), and fires a BKT/SM-2 update (`bkt_tracker.update_card_after_lesson`). None of this is wired into Spaces.

## Goal

Wire Spaces into the same mastery/transcript system — but **automatically**, not via a manual reflection form. As a family completes each lesson's worth of activities inside a Space, credit should be recorded immediately for the concepts that lesson demonstrated, using the LLM's own per-turn evaluation as the evidence. This should happen at **lesson-boundary granularity** within a unit (not per-block, and not only once at the very end) — a single unit typically covers several concepts across several lessons, and Adeline should credit each as it's actually demonstrated.

## Non-goals

- No changes to the non-Space `FamilyCanonicalLesson` / `useLessonSeal` manual-seal flow — it keeps working as-is for lessons reached outside a Space.
- No changes to how the LLM evaluates a turn (`SpaceEvaluation` schema, `/api/spaces/turn` route) — this design only adds what happens *after* a `correct` evaluation causes a lesson to become fully completed.
- Not addressing the "see/resume multiple Spaces" gap (no Spaces list/browse page) — that's explicitly a follow-up, tracked separately.
- Not addressing the missing shared TypeScript type contract for `Space`/`StudentExperience` in `adeline-core`, or the missing rate limit on `/api/spaces/turn` — both are known gaps but out of scope for this change.

## Current relevant data model

- **`CanonicalLesson`** (`adeline-brain/prisma/schema.prisma:248`) — shared authored unit; `oasStandards` (unit-level JSON array of standard dicts).
- **`StudentExperience`** (`schema.prisma:200`) — per-learner adapted rendering; `metadataJson.unit_plan` contains:
  - `concepts[]`: `{concept_id, concept, prerequisite_concept_ids, misconception_to_surface, introduced_in_lesson_id, demonstrated_in_lesson_ids, mastery_evidence}`
  - `lessons[]`: `{lesson_id, title, purpose, concept_ids[], block_ids[]}`
  - `mastery_evidence_map[]`: `{concept, discipline_or_track, acceptable_evidence[], must_be_demonstrated_by_individual, not_awarded_for_exposure_alone: true}` (enforced by `canonical_author.py::enforce_non_exposure_mastery`)
- **`SpaceSession`** (`schema.prisma:220`) — navigation-only state: `currentBlockIndex`, `completedBlockIds[]`, `messagesJson`, `status`, `version`. Explicitly documented today as *"navigation state only; it never awards credit or claims mastery"* — this design changes that.
- **`spaces.py::_lesson_for_block(metadata, block_id, block_index)`** — already resolves which lesson a given block belongs to, by matching `block_id` against each lesson's `block_ids[]`.

## Design

### 1. Schema change: track per-block evaluation outcome

Add a column to `SpaceSession`:

```prisma
model SpaceSession {
  ...
  blockEvaluations Json @default("{}")   // block_id -> {"evaluation": "correct"|"partial"|"incorrect"|"not_answered", "at": ISO8601}
  ...
}
```

Populated inside `/transition` every time a `SpaceEvaluation` is processed, regardless of whether it causes advancement. This is what lets lesson-boundary crediting compute a real proficiency signal (the ratio of `correct` to total evaluations across a lesson's blocks) instead of guessing.

### 2. Extract shared credit-writing function

Pull the three credit-writing operations currently inline in `journal.py::seal_journal` into a shared function — proposed location `adeline-brain/app/services/mastery_credit.py`:

```python
async def record_mastery_credit(
    student_id: str,
    track: str,
    concept_credits: list[ConceptCredit],   # concept_id, concept_name, oas_standards[], proficiency, evidence_sources
    lesson_id: str,                          # for student_journal upsert / portfolio identity
) -> dict:  # -> track_progress, same shape seal_journal returns today
```

This function performs, per concept credit:
- `journal_store.seal(...)`-equivalent upsert of `student_journal` (portfolio entry + `track_progress`), with `evidence_sources` built from the actual chat transcript for the completed lesson's blocks (pulled from the new `blockEvaluations` + `messagesJson`), tagged `{"type": "space_conversation_transcript", ...}`.
- `curriculum_graph.record_standard_mastery(student_id, track, oas_standards, proficiency)`.
- `asyncio.create_task(bkt_tracker.update_card_after_lesson(...))` (fire-and-forget, matching today's non-fatal posture) per `concept_id`.
- Cache invalidation: `invalidate_student_state_cache(student_id)` and `pop_completed_lesson(...)` on the learning plan, same as `seal_journal` does today.

`journal.py::seal_journal` is refactored to call this shared function instead of duplicating the logic, so the two callers (manual seal, automatic Space credit) cannot drift apart.

Idempotency: `record_standard_mastery`'s existing `ON CONFLICT ... DO UPDATE` and a similar upsert for `student_journal` mean re-firing credit for an already-credited lesson (e.g. a replayed state, a retried request) is a safe no-op, not double credit.

### 3. Lesson-boundary detection in `/transition`

Inside `spaces.py::transition_space`, after computing the updated `completedBlockIds` (existing logic, `spaces.py:117-124`):

1. Resolve the current lesson via `_lesson_for_block(metadata, current_id, index)`.
2. Check whether **every** `block_id` in that lesson's `block_ids[]` is now present in `completed`. If not, no credit fires yet (unchanged behavior).
3. If yes, and this lesson hasn't already been credited (tracked via a small in-metadata or session-level marker — e.g. append lesson_id to a `creditedLessonIds[]` list on `SpaceSession`, added alongside `blockEvaluations`):
   - Gather `concept_ids` for the lesson from `unit_plan.concepts[]` filtered by the lesson's `concept_ids[]`.
   - Compute proficiency from the `correct`/`partial`/`incorrect` ratio across this lesson's `block_ids` in `blockEvaluations` (reusing the same DEVELOPING → APPROACHING → UNDERSTANDING → EXTENDING ladder `journal.py::_evidence_proficiency` already uses, adapted to a ratio input instead of quiz results).
   - Resolve `oas_standards` for the credit from the parent `CanonicalLesson.oasStandards`, filtered/matched to this lesson's concepts where possible (fallback: full unit list if no per-concept mapping exists yet — a known imprecision, noted below).
   - Call `record_mastery_credit(...)`.
4. Credit-writing runs **outside** the `SpaceSession` row's DB transaction (after it commits), so a failure in credit-writing never blocks or rolls back the block/lesson advancement the family sees. Failures are logged with enough detail to recover manually (see Error Handling).

### 4. Frontend: replace the dead-end message

`SpacePlayer.tsx`'s end-of-Space message ("record evidence to have your understanding evaluated") no longer describes what happens. Replace it with a summary drawn from the credited concepts for this Space (e.g., "Nice work — Adeline recorded mastery for: [concept names] as you completed each part."). This requires the `/transition` (and/or `read_space`) response to include a lightweight `credited_this_session` list so the frontend can render it without a second round-trip.

## Error handling

- Credit-writing is **best-effort-but-logged**, not transactional with the block-advancement write. A family must never get stuck mid-unit because a downstream mastery write failed.
- The `StandardMastery`/journal-upsert leg is awaited and, on failure, logged with full context (student_id, lesson_id, concept_ids) to a structured log (or a small `MissedMasteryCredit` table, mirroring the existing `StudentExperience.errorMessage` pattern) so it's recoverable later — not silently swallowed.
- The BKT/SM-2 leg keeps its existing fire-and-forget, non-fatal posture (`asyncio.create_task`, caught and logged on failure) — consistent with `seal_journal` today.
- Idempotency (see above) means a retried or replayed lesson-completion is always safe to re-attempt as a recovery mechanism.

## Testing

- Unit tests for lesson-boundary detection in `spaces.py` (last block of last lesson, single-block lessons, out-of-order block completion, already-credited lesson doesn't re-fire).
- Unit tests for `record_mastery_credit` in isolation (given concept credits, assert the right `StandardMastery` / BKT / journal calls happen) — shared test coverage since both `seal_journal` and the new Space path call the same function.
- Integration test driving `/transition` through a fake multi-lesson unit: mid-unit lesson completion credits exactly once; re-completing is idempotent; a forced failure in the credit step still returns a successful transition response with advanced state.
- Manual verification: walk a real Space in the dev UI end to end, confirm the parent Learning Map / transcript reflects new `StandardMastery` rows as each lesson completes (not just at the very end), and confirm the end-of-Space UI message reflects real credited concepts.

## Known imprecision carried forward (not blocking this change)

- OAS standards are authored at the unit level (`CanonicalLesson.oasStandards`), not per-concept or per-lesson. Where a unit's standards can't be cleanly filtered to the concepts a specific lesson demonstrated, this design falls back to crediting the full unit's standard list at that lesson's proficiency level. Tightening this (per-concept standard tagging in `canonical_author.py`'s authoring contract) is a reasonable follow-up but not required to close the "Spaces gives no credit at all" gap.

## Follow-up (explicitly out of scope here)

- Spaces list/browse page — resuming or reviewing past Spaces beyond the single "today" dashboard card.
- Shared `adeline-core` TypeScript types for `Space`/`SpaceSession`/`StudentExperience`.
- Rate limiting on `/api/spaces/turn`.
