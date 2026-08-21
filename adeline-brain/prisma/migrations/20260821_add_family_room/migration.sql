CREATE TABLE IF NOT EXISTS "FamilyPost" (
  "id" TEXT NOT NULL,
  "householdId" TEXT NOT NULL,
  "authorId" TEXT NOT NULL,
  "authorName" TEXT NOT NULL,
  "kind" TEXT NOT NULL DEFAULT 'MESSAGE',
  "title" TEXT,
  "body" TEXT NOT NULL,
  "resourceUrl" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "FamilyPost_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "FamilyPost_householdId_createdAt_idx"
  ON "FamilyPost"("householdId", "createdAt");
