CREATE TABLE "CanonicalLesson" (
 id text PRIMARY KEY, "blocksJson" jsonb, "stagesJson" jsonb, "sharedFactsJson" jsonb,
 "sharedSourcesJson" jsonb,"skillOpportunitiesJson" jsonb,"realWorldContractJson" jsonb,
 "pendingApproval" boolean,"updatedAt" timestamptz,"contractVersion" int
);
CREATE TABLE "StudentExperience" (id text,"planItemId" text,"blocksJson" jsonb,"metadataJson" jsonb,status text,"errorMessage" text,"updatedAt" timestamptz);
CREATE TABLE "DailyPlan" (id text);
CREATE TABLE "User" (id text);
CREATE TABLE "EvidenceAttempt" (id text,content jsonb);
CREATE TABLE "StudentCharacter" (id text);
INSERT INTO "CanonicalLesson" VALUES ('old','[{"content":"rejected lesson"}]','[]','[]','[]','[]','{}',false,NOW(),2),
 ('new','[{"metadata":{"classroom":{}}}]','[]','[]','[]','[]',NULL,false,NOW(),100);
INSERT INTO "StudentExperience" VALUES ('old','today-old','[{"content":"old adaptation"}]','{"unit_plan":{}}','ready',NULL,NOW()),
 ('new','openmaic-classroom-v1:new','[]','{"format_version":"openmaic-classroom-v1"}','ready',NULL,NOW());
INSERT INTO "DailyPlan" VALUES ('old-plan');
INSERT INTO "User" VALUES ('learner');
INSERT INTO "EvidenceAttempt" VALUES ('submission','{"text":"my work"}');
INSERT INTO "StudentCharacter" VALUES ('character');
