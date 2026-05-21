-- Migration: add Subscription table for Stripe subscription persistence
-- Replaces the in-memory _SUBS dict in app/api/subscriptions.py

CREATE TABLE IF NOT EXISTS "Subscription" (
  "id"                   TEXT        NOT NULL,
  "userId"               TEXT        NOT NULL,
  "stripeCustomerId"     TEXT,
  "stripeSubscriptionId" TEXT,
  "stripePriceId"        TEXT,
  "tier"                 TEXT        NOT NULL DEFAULT 'FREE',
  "status"               TEXT        NOT NULL DEFAULT 'ACTIVE',
  "currentPeriodEnd"     TIMESTAMPTZ,
  "cancelAtPeriodEnd"    BOOLEAN     NOT NULL DEFAULT false,
  "createdAt"            TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT "Subscription_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "Subscription_userId_key" ON "Subscription"("userId");
