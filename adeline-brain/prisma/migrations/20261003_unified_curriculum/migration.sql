-- Additive migration: legacy queues/evidence remain available for rollback.
CREATE TABLE "FamilyUnit" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE "FamilyUnitQueue" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 "householdId" TEXT NOT NULL, "unitId" TEXT NOT NULL REFERENCES "FamilyUnit"(id),
 position INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'queued'
 CHECK (status IN ('queued','active','completed')),
 "startedAt" TIMESTAMP(3), "completedAt" TIMESTAMP(3),
 "legacyQueueId" TEXT UNIQUE,
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE ("householdId", position)
);
CREATE UNIQUE INDEX "FamilyUnitQueue_one_active" ON "FamilyUnitQueue"("householdId") WHERE status='active';
CREATE TABLE "FamilyUnitExperience" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 "unitId" TEXT NOT NULL REFERENCES "FamilyUnit"(id), position INTEGER NOT NULL,
 "canonicalTopic" TEXT NOT NULL, track TEXT NOT NULL,
 UNIQUE ("unitId", position)
);
CREATE TABLE "FamilyUnitExperienceProgress" (
 "queueId" TEXT NOT NULL REFERENCES "FamilyUnitQueue"(id),
 "experienceId" TEXT NOT NULL REFERENCES "FamilyUnitExperience"(id),
 "completedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY ("queueId", "experienceId")
);
-- Merge unfinished science/history in original creation order. A legacy unit
-- retains its whole canonical; it is not silently split into invented lessons.
WITH ordered AS (
 SELECT *, row_number() OVER (PARTITION BY "householdId" ORDER BY "createdAt",slot,position,id)-1 AS ordinal
 FROM "FamilyInvestigationQueue" WHERE "completedAt" IS NULL
), units AS (
 INSERT INTO "FamilyUnit"(id,title)
 SELECT 'legacy-unit-'||id,"canonicalTopic" FROM ordered RETURNING id
)
INSERT INTO "FamilyUnitQueue"(id,"householdId","unitId",position,status,"startedAt","legacyQueueId")
SELECT 'legacy-queue-'||o.id,o."householdId",u.id,o.ordinal,
 CASE WHEN o.ordinal=0 THEN 'active' ELSE 'queued' END,
 CASE WHEN o.ordinal=0 THEN CURRENT_TIMESTAMP END,o.id
FROM ordered o JOIN units u ON u.id='legacy-unit-'||o.id;
INSERT INTO "FamilyUnitExperience"(id,"unitId",position,"canonicalTopic",track)
SELECT 'legacy-experience-'||q.id,'legacy-unit-'||q.id,0,q."canonicalTopic",q.track
FROM "FamilyInvestigationQueue" q JOIN "FamilyUnit" u ON u.id='legacy-unit-'||q.id;
ALTER TABLE "CanonicalLesson" ADD COLUMN "contentRevision" TEXT NOT NULL DEFAULT '',
 ADD COLUMN "contractVersion" INTEGER NOT NULL DEFAULT 1,
 ADD COLUMN "stagesJson" JSONB NOT NULL DEFAULT '[]',
 ADD COLUMN "skillOpportunitiesJson" JSONB NOT NULL DEFAULT '[]',
 ADD COLUMN "sharedFactsJson" JSONB NOT NULL DEFAULT '[]',
 ADD COLUMN "sharedSourcesJson" JSONB NOT NULL DEFAULT '[]',
 ADD COLUMN "realWorldContractJson" JSONB;
UPDATE "CanonicalLesson" SET "contentRevision"=COALESCE("blocksJson"->0->'metadata'->>'content_revision','');
CREATE TABLE "StudentCharacter" (
 "studentId" TEXT PRIMARY KEY REFERENCES "User"(id),
 name TEXT NOT NULL, identity TEXT NOT NULL DEFAULT '',
 "rolePreferences" JSONB NOT NULL DEFAULT '[]',
 "persistentTraits" JSONB NOT NULL DEFAULT '[]',
 "visualData" JSONB NOT NULL DEFAULT '{}',
 "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE "EvidenceAttempt" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 "studentId" TEXT NOT NULL REFERENCES "User"(id),
 "canonicalSlug" TEXT NOT NULL, "canonicalRevision" TEXT NOT NULL DEFAULT '',
 "lessonId" TEXT NOT NULL, "skillId" TEXT,
 "parentAttemptId" TEXT REFERENCES "EvidenceAttempt"(id),
 kind TEXT NOT NULL, content JSONB NOT NULL,
 "submissionKey" TEXT NOT NULL,
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE ("studentId", "submissionKey")
);
CREATE INDEX "EvidenceAttempt_student_lesson" ON "EvidenceAttempt"("studentId","lessonId");
CREATE TABLE "EvidenceEvaluation" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 "attemptId" TEXT NOT NULL REFERENCES "EvidenceAttempt"(id),
 "evaluatorId" TEXT NOT NULL, "skillId" TEXT NOT NULL,
 result TEXT NOT NULL CHECK (result IN ('developing','demonstrated','secure')),
 reasoning TEXT NOT NULL,
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE ("attemptId","skillId")
);
CREATE TABLE "StudentSkillState" (
 "studentId" TEXT NOT NULL REFERENCES "User"(id), "skillId" TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'developing', "workingLevel" TEXT NOT NULL DEFAULT '',
 "nextSkillReady" BOOLEAN NOT NULL DEFAULT FALSE,
 "lastEvidenceId" TEXT REFERENCES "EvidenceAttempt"(id),
 "evidenceCount" INTEGER NOT NULL DEFAULT 0,
 "lastDemonstratedAt" TIMESTAMP(3),
 PRIMARY KEY ("studentId","skillId")
);
CREATE TABLE "TimelineCard" (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
 "attemptId" TEXT NOT NULL REFERENCES "EvidenceAttempt"(id),
 "studentId" TEXT NOT NULL REFERENCES "User"(id),
 "dateStart" TEXT NOT NULL, "dateEnd" TEXT,
 claim TEXT NOT NULL, sources JSONB NOT NULL,
 perspectives JSONB NOT NULL DEFAULT '[]',
 "omittedPerspectives" JSONB NOT NULL DEFAULT '[]',
 "conflictingEvidence" JSONB NOT NULL DEFAULT '[]',
 uncertainty TEXT NOT NULL DEFAULT '',
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE ("attemptId")
);
-- Evidence is a ledger. Corrections create new attempts and evaluations.
CREATE FUNCTION reject_evidence_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Evidence is append-only; submit a revision'; END $$;
CREATE TRIGGER "EvidenceAttempt_immutable" BEFORE UPDATE OR DELETE ON "EvidenceAttempt"
 FOR EACH ROW EXECUTE FUNCTION reject_evidence_mutation();
CREATE TRIGGER "EvidenceEvaluation_immutable" BEFORE UPDATE OR DELETE ON "EvidenceEvaluation"
 FOR EACH ROW EXECUTE FUNCTION reject_evidence_mutation();
