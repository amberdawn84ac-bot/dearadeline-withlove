-- Parent-created and PIN learners skip WelcomeFlow. The schema default left
-- onboardingComplete false, so Settings offered "Go to Onboarding" and that
-- page immediately returned the existing session to Today.

UPDATE "User"
SET "onboardingComplete" = TRUE,
    "updatedAt" = NOW()
WHERE role = 'STUDENT'
  AND "onboardingComplete" = FALSE
  AND (username IS NOT NULL OR "parentId" IS NOT NULL);
