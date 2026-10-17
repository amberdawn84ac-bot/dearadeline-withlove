-- Authorized content reset: remove prior generated teaching content, not accounts,
-- standards, characters or the append-only records of learners' submitted work.
-- New classroom documents use contractVersion=100 and their own plan-item namespace.
UPDATE "CanonicalLesson" SET "blocksJson"='[]'::jsonb, "stagesJson"='[]'::jsonb,
 "sharedFactsJson"='[]'::jsonb,"sharedSourcesJson"='[]'::jsonb,
 "skillOpportunitiesJson"='[]'::jsonb,"realWorldContractJson"=NULL,
 "pendingApproval"=TRUE,"updatedAt"=NOW()
WHERE "contractVersion"<>100;
UPDATE "StudentExperience" SET "blocksJson"='[]'::jsonb,"metadataJson"='{}'::jsonb,
 status='failed',"errorMessage"='Retired by the fresh classroom reset.',"updatedAt"=NOW()
WHERE "planItemId" NOT LIKE 'openmaic-classroom-v1:%';
DELETE FROM "DailyPlan";
