-- Add auditability columns to CanonicalLesson.
-- lastApprovedAt: timestamp when an admin approved this canonical.
-- approvedBy: user ID of the admin who approved it.

ALTER TABLE "CanonicalLesson"
  ADD COLUMN IF NOT EXISTS "lastApprovedAt" TIMESTAMP(3),
  ADD COLUMN IF NOT EXISTS "approvedBy"     TEXT;
