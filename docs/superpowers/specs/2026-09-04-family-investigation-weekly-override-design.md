# Family Investigation Weekly Override — Design

**Date:** 2026-09-04
**Status:** Approved, ready for implementation
**Author:** Claude (with Amber Renfroe)

## Problem

The household's shared "family investigation" (the one science/history-flavored unit the whole family works through together each week, per `CLAUDE.md`'s "history and science are family-shared" model) is chosen entirely algorithmically today: `PersonalizedCurriculumPlannerAgent.family_investigation_cycle()` (`adeline-brain/app/agents/curriculum_planner.py:64`) builds a 36-slot rotation from the approved seed catalog, offset by `sha256(household_id)`, and `_family_investigation_suggestion()` (`adeline-brain/app/api/learning_plan.py:882`) indexes into it by `(iso.week - 1) % len(cycle)` — the real-world ISO calendar week of `plan_date`.

There is no way to say "this household's first week should be sourdough, and the second week should be the Poison Squad history unit." A parent planning an actual curriculum sequence (Week 1, Week 2, ...) has no lever to pull — only the hash-and-calendar-week formula decides.

## Goal

Add an override layer: a parent (or an operator acting on their behalf) can pin a specific canonical topic/track to a specific household + ISO year/week. When present, the pin wins. When absent, every household's experience is completely unchanged — the existing rotation still governs.

## Non-goals

- Not redefining "week" as "weeks since enrollment" instead of real ISO calendar week — that would silently reshuffle the rotation for every household already using the app who has never asked for a pin. Out of scope; pins are keyed on real ISO year/week, same as the existing `shared_id` already does at `learning_plan.py:903`.
- Not building a parent-facing "plan my year" UI in this pass — just the data model and the endpoint it would call. The endpoint is real and callable today (by me, on the user's behalf, with her real household ID) to land Week 1 immediately.
- Not touching `family_investigation_cycle()`'s algorithm itself — the override sits in front of it, doesn't replace it.

## Design

### 1. Schema: `FamilyInvestigationOverride`

```prisma
model FamilyInvestigationOverride {
  id             String   @id @default(uuid())
  householdId    String
  isoYear        Int
  isoWeek        Int
  canonicalTopic String
  track          String
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt

  @@unique([householdId, isoYear, isoWeek])
}
```

### 2. Lookup in `_family_investigation_suggestion`

Before running the algorithmic cycle, query for `(household_id, iso.year, iso.week)`. If found, build the same `LessonSuggestion` shape the function already returns (title/track/description come from the override row; `canonical_topic` = `override.canonicalTopic`), so nothing downstream (canonical authoring, Spaces) needs to know an override exists — it's the same shape either way. If not found, fall through to today's unchanged behavior.

### 3. Setting a pin

`POST /learning-plan/family-investigation-override` (parent-authenticated): body `{household_id, iso_year, iso_week, canonical_topic, track}`. Upserts on the unique key so re-pinning a week is safe. This is the endpoint I'll call directly (with the real household ID) to land Week 1 = sourdough, Week 2 = Poison Squad, right now.

## Error handling

- The override lookup is a simple keyed read; if it fails (DB hiccup), fall through to the algorithmic cycle rather than failing the whole plan — a missing override should never be worse than "the normal rotation ran instead."
- The upsert on `(householdId, isoYear, isoWeek)` makes re-pinning idempotent; no special conflict handling needed.

## Testing

- Unit test: given an override row and a `plan_date` in that ISO week, `_family_investigation_suggestion` returns a suggestion sourced from the override, not the algorithmic cycle.
- Unit test: with no override present, behavior is byte-for-byte identical to today (regression guard).
- Unit test: a `plan_date` in a *different* ISO week than the pinned one falls through to the algorithm, even if the household has other overrides.
