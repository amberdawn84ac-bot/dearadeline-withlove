# Family Investigation Concurrent Slots — Design (Phase 1)

**Date:** 2026-09-05
**Status:** Approved, ready for implementation
**Author:** Claude (with Amber Renfroe)
**Supersedes:** `2026-09-04-family-investigation-weekly-override-design.md` — that design's calendar-ISO-week keying didn't fit; replaced entirely by this one before it was used for anything but a same-day stopgap.

## Problem

The previous design (shipped same day, `FamilyInvestigationOverride`) pinned one topic per household per real-calendar ISO week. Actual usage doesn't match that model at all:

1. The family wants **two concurrent investigations** running side by side — one science-flavored, one history-flavored — not one at a time.
2. **Units aren't time-boxed.** A unit runs until the family actually finishes its activities, however long that takes — "we set the pace," not the calendar.
3. When a unit finishes, the **next one in that track's queue begins** — there's no fixed schedule to advance through.

## Goal

Replace the calendar-keyed override with a **per-household, per-slot ordered queue**. Two named slots exist per household — `"science"` and `"history"` — each holding an ordered list of (topic, track) entries. The current item in a slot is whichever queued entry hasn't been marked complete yet; when its Space finishes, the queue silently advances to the next entry, with no calendar involved anywhere.

## Non-goals (this phase)

- Rabbit-hole / live off-plan concept crediting, and keeping a Space's chat open indefinitely after completion — that's Phase 2, deliberately deferred.
- A parent-facing UI to reorder/curate the queue — this phase adds the data model and an enqueue endpoint; I'll call it directly for now, same as the previous phase.
- Removing the underlying single-item-per-day family_investigation *concept* — CLAUDE.md's "history and science are family-shared, one investigation each" model stays; this phase just makes each of those two spines pace-driven and independently queued instead of calendar-bound.

## Design

### 1. Schema: replace `FamilyInvestigationOverride` with `FamilyInvestigationQueue`

```prisma
model FamilyInvestigationQueue {
  id             String    @id @default(uuid())
  householdId    String
  slot           String    // "science" | "history" — a label, not an enforced track whitelist
  position       Int
  canonicalTopic String
  track          String
  completedAt    DateTime?
  createdAt      DateTime  @default(now())

  @@unique([householdId, slot, position])
  @@index([householdId, slot, completedAt])
}
```

The **current item** for a (household, slot) is the lowest-`position` row where `completedAt IS NULL`. No separate pointer column needed — advancing is just stamping `completedAt` on the current row; the next `SELECT ... WHERE completedAt IS NULL ORDER BY position LIMIT 1` naturally returns the next one.

`FamilyInvestigationOverride` (and its store/endpoint from the superseded design) is dropped — it was shipped and used only as a same-day stopgap, nothing else depends on it.

### 2. Lazy completion check, same pattern as before

On every plan load, for each slot with a current row: if a `SpaceSession` tied to that queue item's shared investigation id exists and has `status == 'completed'`, stamp `completedAt = NOW()` on the queue row (so the *next* read returns the next item). No push/webhook needed — this mirrors how `_family_investigation_suggestion` already worked, just checking Space completion instead of computing an ISO week index.

### 3. `_family_investigation_suggestions()` (plural) replaces `_family_investigation_suggestion()`

Returns a list of up to two `LessonSuggestion`s — one per slot that has a current item — instead of one. Each suggestion's `shared_investigation_id`/`canonical_slug` is now derived from `(household_key, slot, position)` instead of `(iso.year, iso.week)`, so it stays stable for the entire time that queue item is current, however long that takes.

### 4. API/response shape

`LearningPlanResponse` gains `family_investigations: list[LessonSuggestion]` (0–2 items). The existing singular `family_investigation` field is kept, set to the first of the two (or `None`), so anything still reading the old field doesn't outright break — but the dashboard is updated to read the new plural field and render both cards.

### 5. Enqueuing

`POST /learning-plan/family-investigation-queue` (parent/admin-authenticated, same posture as the superseded design's endpoint): `{household_id, slot, canonical_topic, track}` appends a new entry at the end of that slot's queue (`position = current max + 1`). I'll call this directly today to seed sourdough (science, position 0) and Poison Squad (history, position 0) for every household, replacing the override rows written under the previous design.

## Error handling

- Completion-check failures (Space lookup errors) log and leave the queue row as-is — a failed check just means the family stays on the current item one more read, never a hard error surfaced to the plan.
- Enqueue is a straightforward append; no conflict handling needed beyond the unique `(householdId, slot, position)` constraint.

## Testing

- Unit test: a slot with no completed items returns position 0 as current.
- Unit test: a slot whose current item's Space is completed advances to the next position on the next read.
- Unit test: a slot with an empty queue returns no suggestion (not an error).
- Unit test: two slots (science + history) both present in `family_investigations` simultaneously, independent of each other's completion state.
