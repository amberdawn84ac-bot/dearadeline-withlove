-- Hard prerequisite gates must be auditable.  Relationship rows now retain
-- the exact progression source and review state that justified the edge.

ALTER TABLE "CurriculumConceptPrerequisite"
    ADD COLUMN "sourceTitle" TEXT NOT NULL DEFAULT 'Dear Adeline foundational concept graph',
    ADD COLUMN "sourceUrl" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "sourceVersion" TEXT NOT NULL DEFAULT '2026-08-26',
    ADD COLUMN "evidenceNote" TEXT NOT NULL DEFAULT 'Internally curated foundational concept relationship.',
    ADD COLUMN "reviewStatus" TEXT NOT NULL DEFAULT 'INTERNAL_CURATED',
    ADD COLUMN "reviewedAt" TIMESTAMP(3);

ALTER TABLE "OASStandardRelation"
    ADD COLUMN "sourceTitle" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "sourceUrl" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "sourceVersion" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "evidenceNote" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "reviewStatus" TEXT NOT NULL DEFAULT 'PENDING',
    ADD COLUMN "reviewedAt" TIMESTAMP(3);

CREATE INDEX "OASStandardRelation_type_review_idx"
    ON "OASStandardRelation"("relationType", "reviewStatus");
