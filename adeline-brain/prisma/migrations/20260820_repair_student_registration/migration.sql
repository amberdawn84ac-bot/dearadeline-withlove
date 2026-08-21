-- Production-safe repair for username + PIN student registration.
-- Every statement is idempotent because some databases already have part of
-- the Adelinemobile schema while others were baselined at an earlier revision.
ALTER TABLE "User"
  ADD COLUMN IF NOT EXISTS "xp"         INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS "adeCoins"   INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS "avatarData" JSONB,
  ADD COLUMN IF NOT EXISTS "username"   TEXT,
  ADD COLUMN IF NOT EXISTS "pinHash"    TEXT,
  ADD COLUMN IF NOT EXISTS "linkCode"   TEXT;

ALTER TABLE "User"
  ALTER COLUMN "updatedAt" SET DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS "User_username_key"
  ON "User" ("username") WHERE "username" IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "User_linkCode_key"
  ON "User" ("linkCode") WHERE "linkCode" IS NOT NULL;
