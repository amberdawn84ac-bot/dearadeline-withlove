-- Production ReadingSession was created by the IF NOT EXISTS book migration,
-- which has no createdAt and no studentReflection. 20260404 was recorded as
-- applied without adding those columns, so POST /api/reading-session dies with
-- UndefinedColumnError. The API also reads minutesRead, which that older
-- migration named readingMinutes.

ALTER TABLE "ReadingSession" ADD COLUMN IF NOT EXISTS "studentReflection" TEXT;
ALTER TABLE "ReadingSession" ADD COLUMN IF NOT EXISTS "minutesRead" INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "ReadingSession" ADD COLUMN IF NOT EXISTS "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP;
