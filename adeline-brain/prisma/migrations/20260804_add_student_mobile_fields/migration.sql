-- Adelinemobile kid accounts: username+PIN auth, XP/coins/avatar/season-pass
-- state, and the parent link code, all stored directly on User (role=STUDENT).
ALTER TABLE "User"
  ADD COLUMN IF NOT EXISTS "xp"          INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS "adeCoins"    INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS "avatarData"  JSONB,
  ADD COLUMN IF NOT EXISTS "seasonPass"  JSONB,
  ADD COLUMN IF NOT EXISTS "username"    TEXT,
  ADD COLUMN IF NOT EXISTS "pinHash"     TEXT,
  ADD COLUMN IF NOT EXISTS "linkCode"    TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS "User_username_key"
  ON "User" ("username")
  WHERE "username" IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS "User_linkCode_key"
  ON "User" ("linkCode")
  WHERE "linkCode" IS NOT NULL;
