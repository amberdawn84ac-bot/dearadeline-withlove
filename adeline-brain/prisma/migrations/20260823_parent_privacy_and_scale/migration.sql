-- Parent-dashboard scale and child-privacy consent audit trail.

-- This legacy learning-profile projection is still consumed by the planning
-- engine. Create it through deployment migrations, never in a request path.
CREATE TABLE IF NOT EXISTS student_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '',
  email TEXT UNIQUE,
  grade_level TEXT NOT NULL DEFAULT 'K',
  is_homestead BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "ChildPrivacyConsent" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "studentId" TEXT NOT NULL,
  "parentId" TEXT,
  "parentEmail" TEXT NOT NULL,
  "method" TEXT NOT NULL,
  "privacyNoticeVersion" TEXT NOT NULL,
  "consentedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  "revokedAt" TIMESTAMPTZ,
  CONSTRAINT "ChildPrivacyConsent_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "ChildPrivacyConsent_studentId_consentedAt_idx"
  ON "ChildPrivacyConsent"("studentId", "consentedAt" DESC);
CREATE INDEX IF NOT EXISTS "ChildPrivacyConsent_parentId_consentedAt_idx"
  ON "ChildPrivacyConsent"("parentId", "consentedAt" DESC);
CREATE INDEX IF NOT EXISTS "User_parentId_role_idx"
  ON "User"("parentId", role);
CREATE INDEX IF NOT EXISTS "ReadingSession_studentId_status_idx"
  ON "ReadingSession"("studentId", status);
CREATE INDEX IF NOT EXISTS "User_coppaTokenExpiresAt_pending_idx"
  ON "User"("coppaTokenExpiresAt")
  WHERE "coppaPendingToken" IS NOT NULL;
CREATE INDEX IF NOT EXISTS "student_journal_student_sealed_idx"
  ON student_journal(student_id, sealed_at DESC);

-- This table is backend-only. Keep it out of the browser-facing Data API.
ALTER TABLE "ChildPrivacyConsent" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "ChildPrivacyConsent" FROM anon, authenticated;
ALTER TABLE student_profiles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE student_profiles FROM anon, authenticated;
