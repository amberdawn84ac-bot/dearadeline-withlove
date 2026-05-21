-- Row Level Security policies for User and StandardMastery tables.
--
-- HOW TO APPLY:
--   Supabase Dashboard → SQL Editor → paste and run this file.
--   Do NOT run via Prisma migrations — auth.uid() is a Supabase function
--   that is not available in the standard Postgres context Prisma uses.
--
-- This only needs to be run ONCE per environment (production, staging).
-- Re-running is safe — all policies use DROP IF EXISTS before CREATE.

-- ── User table ────────────────────────────────────────────────────────────────

ALTER TABLE "User" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own profile"         ON "User";
DROP POLICY IF EXISTS "Users can update own profile"       ON "User";
DROP POLICY IF EXISTS "Users can insert own profile"       ON "User";
DROP POLICY IF EXISTS "Onboarding insert own profile"      ON "User";
DROP POLICY IF EXISTS "Parents can view children profiles" ON "User";
DROP POLICY IF EXISTS "Service role full access"           ON "User";

CREATE POLICY "Users can view own profile"
ON "User" FOR SELECT TO authenticated
USING (id = auth.uid()::text);

CREATE POLICY "Users can update own profile"
ON "User" FOR UPDATE TO authenticated
USING (id = auth.uid()::text)
WITH CHECK (id = auth.uid()::text);

CREATE POLICY "Users can insert own profile"
ON "User" FOR INSERT TO authenticated
WITH CHECK (id = auth.uid()::text);

CREATE POLICY "Parents can view children profiles"
ON "User" FOR SELECT TO authenticated
USING (
  id = auth.uid()::text
  OR "parentId" = auth.uid()::text
);

CREATE POLICY "Service role full access"
ON "User" FOR ALL TO service_role
USING (true)
WITH CHECK (true);

-- ── StandardMastery table ─────────────────────────────────────────────────────

ALTER TABLE "StandardMastery" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students view own mastery"     ON "StandardMastery";
DROP POLICY IF EXISTS "Parents view children mastery" ON "StandardMastery";
DROP POLICY IF EXISTS "Service role mastery access"   ON "StandardMastery";

CREATE POLICY "Students view own mastery"
ON "StandardMastery" FOR SELECT TO authenticated
USING ("studentId" = auth.uid()::text);

CREATE POLICY "Parents view children mastery"
ON "StandardMastery" FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM "User"
    WHERE "User".id = "StandardMastery"."studentId"
      AND "User"."parentId" = auth.uid()::text
  )
);

CREATE POLICY "Service role mastery access"
ON "StandardMastery" FOR ALL TO service_role
USING (true)
WITH CHECK (true);

-- ── Verify ────────────────────────────────────────────────────────────────────

SELECT tablename, policyname, permissive, cmd
FROM pg_policies
WHERE tablename IN ('User', 'StandardMastery')
ORDER BY tablename, policyname;
