-- The family-facing name is not the User.name stored for this learner.
-- Retry the one-time repair using the exact plan item ID from the Space URL.
DO $$
DECLARE
    target_count integer;
    target_student_id text;
    target_canonical_slug text;
BEGIN
    SELECT count(*), min("studentId"), min("canonicalSlug")
      INTO target_count, target_student_id, target_canonical_slug
      FROM "StudentExperience"
     WHERE "planItemId" = 'family-7458cc83ebf4-science-0';

    IF target_count = 1 THEN
        UPDATE "CanonicalLesson"
           SET "pendingApproval" = TRUE,
               "needsReviewReason" = 'family_requested_terminology_rewrite',
               "updatedAt" = NOW()
         WHERE "topicSlug" = target_canonical_slug;

        DELETE FROM "SpaceSession"
         WHERE "studentId" = target_student_id
           AND "planItemId" = 'family-7458cc83ebf4-science-0';

        UPDATE "StudentExperience"
           SET status = 'failed',
               title = NULL,
               track = NULL,
               "blocksJson" = '[]'::jsonb,
               "metadataJson" = '{}'::jsonb,
               "errorMessage" = 'Rewrite requested 2026-09-07: terminology correction',
               "failureCount" = 0,
               "updatedAt" = NOW()
         WHERE "studentId" = target_student_id
           AND "planItemId" = 'family-7458cc83ebf4-science-0';

        RAISE NOTICE 'Reset the requested sourdough Space for reauthoring';
    ELSE
        RAISE NOTICE 'Sourdough reset skipped: expected exactly 1 plan item, found %', target_count;
    END IF;
END $$;
