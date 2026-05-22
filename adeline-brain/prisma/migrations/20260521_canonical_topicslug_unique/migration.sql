-- Ensure CanonicalLesson.topicSlug has a proper unique constraint (not just index)
-- so that ON CONFLICT ("topicSlug") DO UPDATE works correctly.
-- The original migration created a unique index; this promotes it to a constraint.

DROP INDEX IF EXISTS "CanonicalLesson_topicSlug_key";

DO $$ BEGIN
  ALTER TABLE "CanonicalLesson"
    ADD CONSTRAINT "CanonicalLesson_topicSlug_key" UNIQUE ("topicSlug");
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
