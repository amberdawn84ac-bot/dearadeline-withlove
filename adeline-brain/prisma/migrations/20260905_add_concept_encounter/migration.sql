-- Purely observational log of concepts a Space conversation engaged with but
-- did not demonstrate to correctness. Never read by mastery/credit logic.
CREATE TABLE "ConceptEncounter" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "studentId" TEXT NOT NULL,
    "conceptName" TEXT NOT NULL,
    "track" TEXT NOT NULL,
    "spaceSessionId" TEXT NOT NULL,
    "encounteredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ConceptEncounter_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "ConceptEncounter_studentId_idx" ON "ConceptEncounter"("studentId");
