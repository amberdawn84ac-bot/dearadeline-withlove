CREATE INDEX IF NOT EXISTS "User_parentId_idx" ON "User"("parentId");
CREATE INDEX IF NOT EXISTS "User_role_idx" ON "User"("role");

CREATE UNIQUE INDEX IF NOT EXISTS "InviteCode_code_key" ON "InviteCode"("code");

CREATE INDEX IF NOT EXISTS "LearningRecord_studentId_timestamp_idx"
  ON "LearningRecord"("studentId", "timestamp" DESC);
CREATE INDEX IF NOT EXISTS "LearningRecord_lessonId_idx" ON "LearningRecord"("lessonId");
CREATE INDEX IF NOT EXISTS "LearningRecord_studentId_lessonId_idx"
  ON "LearningRecord"("studentId", "lessonId");

CREATE INDEX IF NOT EXISTS "TranscriptEntry_studentId_completedAt_idx"
  ON "TranscriptEntry"("studentId", "completedAt" DESC);
CREATE INDEX IF NOT EXISTS "TranscriptEntry_studentId_sealedAt_idx"
  ON "TranscriptEntry"("studentId", "sealedAt" DESC);
CREATE INDEX IF NOT EXISTS "TranscriptEntry_lessonId_idx" ON "TranscriptEntry"("lessonId");

CREATE INDEX IF NOT EXISTS "SpacedRepetitionCard_studentId_dueAt_idx"
  ON "SpacedRepetitionCard"("studentId", "dueAt");
CREATE UNIQUE INDEX IF NOT EXISTS "SpacedRepetitionCard_studentId_conceptId_key"
  ON "SpacedRepetitionCard"("studentId", "conceptId");

DO $$
BEGIN
  IF to_regclass('public.conversation_messages') IS NOT NULL THEN
    CREATE INDEX IF NOT EXISTS "conversation_messages_student_created_idx"
      ON conversation_messages(student_id, created_at DESC);
  END IF;
END $$;

-- Convert Dear Adeline's former public Supabase object URLs into private keys.
-- Third-party URLs are intentionally untouched.
UPDATE "ActivityEvidence"
SET "fileUrl" = regexp_replace(
  "fileUrl",
  '^https://[^/]+/storage/v1/object/public/mastery-evidence/',
  ''
)
WHERE "fileUrl" ~ '^https://[^/]+/storage/v1/object/public/mastery-evidence/';
