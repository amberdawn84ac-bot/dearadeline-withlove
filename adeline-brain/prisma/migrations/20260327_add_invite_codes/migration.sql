-- CreateTable: InviteCode
-- Founder invite codes — pre-seed for Alpha launch (50 codes via generate_founder_codes.py)
-- Redeemed at POST /auth/register when JWT auth is wired up.

CREATE TABLE "InviteCode" (
    "id"             TEXT      NOT NULL,
    "code"           TEXT      NOT NULL,
    "isUsed"         BOOLEAN   NOT NULL DEFAULT false,
    "claimedByEmail" TEXT,
    "createdAt"      TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "InviteCode_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "InviteCode_code_key" ON "InviteCode"("code");
CREATE INDEX "InviteCode_code_idx" ON "InviteCode"("code");
