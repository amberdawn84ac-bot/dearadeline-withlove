-- FamilyInvestigationOverride pinned topics to real-calendar ISO weeks; that
-- shipped same-day as a stopgap and is superseded by a pace-driven,
-- two-concurrent-slot queue before anything else came to depend on it.
DROP TABLE IF EXISTS "FamilyInvestigationOverride";

CREATE TABLE "FamilyInvestigationQueue" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "householdId" TEXT NOT NULL,
    "slot" TEXT NOT NULL,
    "position" INTEGER NOT NULL,
    "canonicalTopic" TEXT NOT NULL,
    "track" TEXT NOT NULL,
    "completedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "FamilyInvestigationQueue_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "FamilyInvestigationQueue_householdId_slot_position_key"
    ON "FamilyInvestigationQueue"("householdId", "slot", "position");
CREATE INDEX "FamilyInvestigationQueue_householdId_slot_completedAt_idx"
    ON "FamilyInvestigationQueue"("householdId", "slot", "completedAt");
