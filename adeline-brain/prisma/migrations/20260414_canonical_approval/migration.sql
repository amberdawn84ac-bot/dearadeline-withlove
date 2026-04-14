-- Add human-in-the-loop review columns to CanonicalLesson.
-- pendingApproval: TRUE means the canonical is saved but not yet served to students.
-- needsReviewReason: why it needs review ("researcher_activated" | "high_stakes_track").

ALTER TABLE "CanonicalLesson"
  ADD COLUMN IF NOT EXISTS "pendingApproval"    BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS "needsReviewReason"  TEXT;

CREATE INDEX IF NOT EXISTS "CanonicalLesson_pending_idx"
  ON "CanonicalLesson" ("pendingApproval")
  WHERE "pendingApproval" = TRUE;
