-- Add onboarding fields to User model

-- Add subject-specific mastery level overrides (0-100)
ALTER TABLE "User" ADD COLUMN "mathLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN "elaLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN "scienceLevel" INTEGER;
ALTER TABLE "User" ADD COLUMN "historyLevel" INTEGER;

-- Add learning style and pacing preferences
ALTER TABLE "User" ADD COLUMN "interests" TEXT[] DEFAULT '{}';
ALTER TABLE "User" ADD COLUMN "learningStyle" TEXT;
ALTER TABLE "User" ADD COLUMN "pacingMultiplier" DOUBLE PRECISION;

-- Add student context (state for standards)
ALTER TABLE "User" ADD COLUMN "state" TEXT;
ALTER TABLE "User" ADD COLUMN "targetGraduationYear" INTEGER;

-- Add onboarding completion flag
ALTER TABLE "User" ADD COLUMN "onboardingComplete" BOOLEAN NOT NULL DEFAULT false;

-- Create index on onboardingComplete for filtering
CREATE INDEX "User_onboardingComplete_idx" ON "User"("onboardingComplete");
