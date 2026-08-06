-- Town & Player Systems foundation: a joinable Town entity, dual-layer
-- (town-pooled + individual) resources for money/property/inventory, and
-- individual reputation/achievements. See
-- docs/superpowers/specs/2026-08-05-town-player-systems-design.md
-- (Adelinemobile repo) for the full design.

CREATE TABLE IF NOT EXISTS "Town" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name        TEXT NOT NULL,
    "joinCode"  TEXT NOT NULL UNIQUE,
    treasury    INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "townId" TEXT REFERENCES "Town"(id);
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS reputation INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS "TownBuilding" (
    id            TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "townId"      TEXT NOT NULL REFERENCES "Town"(id) ON DELETE CASCADE,
    "buildingKey" TEXT NOT NULL,
    "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE ("townId", "buildingKey")
);

CREATE TABLE IF NOT EXISTS "Item" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,
    description TEXT,
    "iconUrl"   TEXT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "TownSupply" (
    id        TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "townId"  TEXT NOT NULL REFERENCES "Town"(id) ON DELETE CASCADE,
    "itemId"  TEXT NOT NULL REFERENCES "Item"(id),
    quantity  INTEGER NOT NULL DEFAULT 0,
    UNIQUE ("townId", "itemId")
);

CREATE TABLE IF NOT EXISTS "PlayerInventory" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "studentId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "itemId"    TEXT NOT NULL REFERENCES "Item"(id),
    quantity    INTEGER NOT NULL DEFAULT 0,
    UNIQUE ("studentId", "itemId")
);

CREATE TABLE IF NOT EXISTS "Achievement" (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    key         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    icon        TEXT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "PlayerAchievement" (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    "studentId"     TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "achievementId" TEXT NOT NULL REFERENCES "Achievement"(id),
    "earnedAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE ("studentId", "achievementId")
);
