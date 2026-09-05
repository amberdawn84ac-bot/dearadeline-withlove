-- A parent-pinned override for one household's shared family investigation
-- in one specific real-calendar ISO week, taking precedence over the
-- hash-and-calendar-week rotation when present.
CREATE TABLE "FamilyInvestigationOverride" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "householdId" TEXT NOT NULL,
    "isoYear" INTEGER NOT NULL,
    "isoWeek" INTEGER NOT NULL,
    "canonicalTopic" TEXT NOT NULL,
    "track" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "FamilyInvestigationOverride_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "FamilyInvestigationOverride_householdId_isoYear_isoWeek_key"
    ON "FamilyInvestigationOverride"("householdId", "isoYear", "isoWeek");
