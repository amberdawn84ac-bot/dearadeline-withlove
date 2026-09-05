-- Track per-block evaluation outcomes and already-credited lessons on a Space,
-- so lesson-boundary completion can compute real proficiency (correct/partial
-- ratio) and never double-credit a lesson on retry/replay.
ALTER TABLE "SpaceSession"
    ADD COLUMN "blockEvaluations" JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN "creditedLessonIds" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];
