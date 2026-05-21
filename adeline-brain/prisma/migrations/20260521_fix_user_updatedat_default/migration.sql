-- Fix: Add DEFAULT CURRENT_TIMESTAMP to "User"."updatedAt"
--
-- The original init migration created this column as NOT NULL with no default.
-- Any INSERT that omits updatedAt (e.g. a Supabase auth trigger or direct insert)
-- would fail with a not-null constraint violation.
-- This migration adds the default so the column is always populated automatically.

ALTER TABLE "User"
  ALTER COLUMN "updatedAt" SET DEFAULT CURRENT_TIMESTAMP;
