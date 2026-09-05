-- Tracks consecutive authoring failures per (student, plan item) so repeated
-- failures can escalate instead of offering a silent retry forever.
ALTER TABLE "StudentExperience" ADD COLUMN "failureCount" INTEGER NOT NULL DEFAULT 0;
