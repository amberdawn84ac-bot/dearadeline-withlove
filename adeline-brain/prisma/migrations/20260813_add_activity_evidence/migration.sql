CREATE TABLE IF NOT EXISTS "ActivityEvidence" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "activityId" TEXT NOT NULL,
    "fileUrl" TEXT NOT NULL,
    "contentType" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ActivityEvidence_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "ActivityEvidence_studentId_idx" ON "ActivityEvidence"("studentId");
CREATE INDEX IF NOT EXISTS "ActivityEvidence_activityId_idx" ON "ActivityEvidence"("activityId");
