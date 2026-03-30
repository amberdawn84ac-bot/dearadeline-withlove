-- Add Track 9 (APPLIED_MATHEMATICS) and Track 10 (CREATIVE_ECONOMY) to the Track enum.
-- Postgres requires adding enum values with ALTER TYPE … ADD VALUE.
-- These are safe, additive changes — no data is touched.

ALTER TYPE "Track" ADD VALUE IF NOT EXISTS 'APPLIED_MATHEMATICS';
ALTER TYPE "Track" ADD VALUE IF NOT EXISTS 'CREATIVE_ECONOMY';
