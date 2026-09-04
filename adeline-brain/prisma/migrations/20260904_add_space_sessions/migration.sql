CREATE TABLE "SpaceSession" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    "studentId" TEXT NOT NULL,
    "planItemId" TEXT NOT NULL,
    "experienceId" TEXT NOT NULL,
    "currentBlockIndex" INTEGER NOT NULL DEFAULT 0,
    "completedBlockIds" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    "messagesJson" JSONB NOT NULL DEFAULT '[]',
    "status" TEXT NOT NULL DEFAULT 'active',
    "version" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "SpaceSession_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "SpaceSession_studentId_planItemId_key"
    ON "SpaceSession"("studentId", "planItemId");
CREATE INDEX "SpaceSession_studentId_status_idx"
    ON "SpaceSession"("studentId", "status");
