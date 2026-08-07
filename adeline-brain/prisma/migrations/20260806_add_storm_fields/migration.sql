-- World Events: The Storm. Town-level prep counter and idempotency marker
-- for the globally-scheduled, per-town-evaluated storm event. See
-- docs/superpowers/specs/2026-08-06-world-events-storm-design.md
-- (Adelinemobile repo) for the full design.
ALTER TABLE "Town" ADD COLUMN IF NOT EXISTS "stormPrepCount" INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "Town" ADD COLUMN IF NOT EXISTS "lastStormCycleEvaluated" INTEGER NOT NULL DEFAULT -1;
