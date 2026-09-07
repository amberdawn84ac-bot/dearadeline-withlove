-- One-time, narrowly scoped repair requested by the family.
-- Reset only Cash's saved sourdough Space. Permanent learning, mastery,
-- transcript, and portfolio tables are intentionally untouched.
DO $$
DECLARE
    target_count integer;
    target_student_id text;
    target_canonical_slug text;
BEGIN
    SELECT count(*), min(se."studentId"), min(se."canonicalSlug")
      INTO target_count, target_student_id, target_canonical_slug
      FROM "StudentExperience" se
      JOIN "User" u ON u.id = se."studentId"
     WHERE lower(trim(u.name)) = 'cash'
       AND se."planItemId" = 'family-7458cc83ebf4-science-0';

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

        RAISE NOTICE 'Reset Cash sourdough Space for reauthoring';
    ELSE
        RAISE NOTICE 'Cash sourdough reset skipped: expected exactly 1 target, found %', target_count;
    END IF;
END $$;
