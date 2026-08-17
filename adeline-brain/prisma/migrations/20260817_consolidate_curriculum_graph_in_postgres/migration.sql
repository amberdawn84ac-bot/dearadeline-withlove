-- Consolidate curriculum relationships in the existing Postgres database.
-- This removes the need for a second graph database while preserving
-- prerequisites, cross-track reasoning, standards progression, and mastery.

CREATE TABLE "CurriculumConcept" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "track" "Track" NOT NULL,
    "difficulty" TEXT NOT NULL,
    "standardCode" TEXT NOT NULL DEFAULT '',
    "gradeBand" TEXT NOT NULL DEFAULT '',
    "tags" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    "isPrimarySource" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "CurriculumConcept_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "CurriculumConcept_track_idx" ON "CurriculumConcept"("track");
CREATE INDEX "CurriculumConcept_standardCode_idx" ON "CurriculumConcept"("standardCode");
CREATE INDEX "CurriculumConcept_gradeBand_idx" ON "CurriculumConcept"("gradeBand");

CREATE TABLE "CurriculumConceptPrerequisite" (
    "conceptId" TEXT NOT NULL,
    "prerequisiteId" TEXT NOT NULL,
    "weight" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    CONSTRAINT "CurriculumConceptPrerequisite_pkey" PRIMARY KEY ("conceptId", "prerequisiteId"),
    CONSTRAINT "CurriculumConceptPrerequisite_conceptId_fkey"
        FOREIGN KEY ("conceptId") REFERENCES "CurriculumConcept"("id") ON DELETE CASCADE,
    CONSTRAINT "CurriculumConceptPrerequisite_prerequisiteId_fkey"
        FOREIGN KEY ("prerequisiteId") REFERENCES "CurriculumConcept"("id") ON DELETE CASCADE
);

CREATE INDEX "CurriculumConceptPrerequisite_prerequisiteId_idx"
    ON "CurriculumConceptPrerequisite"("prerequisiteId");

CREATE TABLE "CurriculumConceptEvidence" (
    "conceptId" TEXT NOT NULL,
    "evidenceId" TEXT NOT NULL,
    "chunk" TEXT NOT NULL,
    "truthScore" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    CONSTRAINT "CurriculumConceptEvidence_pkey" PRIMARY KEY ("conceptId", "evidenceId"),
    CONSTRAINT "CurriculumConceptEvidence_conceptId_fkey"
        FOREIGN KEY ("conceptId") REFERENCES "CurriculumConcept"("id") ON DELETE CASCADE
);

CREATE TABLE "CurriculumTrackLink" (
    "fromTrack" "Track" NOT NULL,
    "toTrack" "Track" NOT NULL,
    CONSTRAINT "CurriculumTrackLink_pkey" PRIMARY KEY ("fromTrack", "toTrack")
);

CREATE INDEX "CurriculumTrackLink_toTrack_idx" ON "CurriculumTrackLink"("toTrack");

CREATE TABLE "OASStandardRelation" (
    "fromStandardId" TEXT NOT NULL,
    "relationType" TEXT NOT NULL,
    "toStandardId" TEXT NOT NULL,
    "weight" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    CONSTRAINT "OASStandardRelation_pkey" PRIMARY KEY ("fromStandardId", "relationType", "toStandardId")
);

CREATE INDEX "OASStandardRelation_toStandardId_relationType_idx"
    ON "OASStandardRelation"("toStandardId", "relationType");

CREATE TABLE "StudentConceptMastery" (
    "studentId" TEXT NOT NULL,
    "conceptId" TEXT NOT NULL,
    "score" DOUBLE PRECISION NOT NULL,
    "sealedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "StudentConceptMastery_pkey" PRIMARY KEY ("studentId", "conceptId"),
    CONSTRAINT "StudentConceptMastery_conceptId_fkey"
        FOREIGN KEY ("conceptId") REFERENCES "CurriculumConcept"("id") ON DELETE CASCADE
);

CREATE INDEX "StudentConceptMastery_conceptId_idx" ON "StudentConceptMastery"("conceptId");
CREATE INDEX "StudentConceptMastery_studentId_score_idx" ON "StudentConceptMastery"("studentId", "score");
