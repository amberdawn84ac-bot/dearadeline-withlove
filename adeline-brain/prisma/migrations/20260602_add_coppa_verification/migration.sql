-- COPPA Verifiable Parental Consent
-- Adds parent contact info and email-verification state to User.
-- Grades K-7 (~under 13) require coppaVerified = true before accessing the app.

ALTER TABLE "User"
  ADD COLUMN IF NOT EXISTS "parentName"          TEXT,
  ADD COLUMN IF NOT EXISTS "parentEmail"         TEXT,
  ADD COLUMN IF NOT EXISTS "coppaVerified"       BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS "coppaPendingToken"   TEXT,
  ADD COLUMN IF NOT EXISTS "coppaTokenExpiresAt" TIMESTAMPTZ;

-- Index for fast token lookups during parent verification clicks
CREATE UNIQUE INDEX IF NOT EXISTS "User_coppaPendingToken_key"
  ON "User" ("coppaPendingToken")
  WHERE "coppaPendingToken" IS NOT NULL;
