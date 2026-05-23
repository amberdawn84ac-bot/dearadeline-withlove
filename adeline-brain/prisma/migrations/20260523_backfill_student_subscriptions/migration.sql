-- Migration: backfill STUDENT tier subscriptions for all existing users
-- Every user who has completed onboarding is treated as a paid (STUDENT) account.
-- Users who later downgrade will have their row updated via the Stripe webhook.

INSERT INTO "Subscription" ("id", "userId", "tier", "status", "createdAt", "updatedAt")
SELECT
    gen_random_uuid()::text,
    "id",
    'STUDENT',
    'ACTIVE',
    NOW(),
    NOW()
FROM "User"
WHERE "onboardingComplete" = true
ON CONFLICT ("userId") DO NOTHING;
