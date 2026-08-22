CREATE TABLE IF NOT EXISTS "DailyPlan" (
  "studentId" TEXT NOT NULL,
  "forDate" DATE NOT NULL,
  "planJson" JSONB NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "DailyPlan_pkey" PRIMARY KEY ("studentId", "forDate")
);
CREATE INDEX IF NOT EXISTS "DailyPlan_date_idx" ON "DailyPlan" ("forDate");
