/**
 * adeline-core/src/schemas/spacedRepetition.ts
 * ─────────────────────────────────────────────────────────────────
 * SM-2 spaced repetition state for a student-concept pair.
 *
 * SM-2 quality scale (0–5):
 *   0 — Complete blackout
 *   1 — Wrong; remembered on seeing answer
 *   2 — Wrong; answer seemed easy
 *   3 — Correct with serious difficulty
 *   4 — Correct after hesitation
 *   5 — Perfect instant recall
 *
 * Quality ≥ 3 = pass (interval grows).
 * Quality < 3 = fail (interval resets to 1 day).
 * ─────────────────────────────────────────────────────────────────
 */
import { z } from "zod";
import { Track } from "../types";

export const SpacedRepetitionCardSchema = z.object({
  id:          z.string().uuid(),
  studentId:   z.string().uuid(),

  /** Matches KnowledgeNode.id in Neo4j */
  conceptId:   z.string(),
  conceptName: z.string().min(1),
  track:       z.nativeEnum(Track),

  // SM-2 state
  interval:    z.number().int().min(1).default(1).describe("Days until next review"),
  easeFactor:  z.number().min(1.3).default(2.5).describe("SM-2 ease factor (floor 1.3)"),
  repetitions: z.number().int().min(0).default(0).describe("Consecutive successful review count"),
  lastQuality: z.number().min(0).max(5).optional(),

  /** BKT P(L) from zpd_engine — probability of mastery (0–1) */
  masteryLevel:   z.number().min(0).max(1).default(0),

  dueAt:          z.string().datetime(),
  lastReviewedAt: z.string().datetime().optional(),
  createdAt:      z.string().datetime(),
});

export type SpacedRepetitionCard = z.infer<typeof SpacedRepetitionCardSchema>;

export const SM2ResultSchema = z.object({
  interval:    z.number().int().min(1),
  easeFactor:  z.number().min(1.3),
  repetitions: z.number().int().min(0),
  nextDueAt:   z.string().datetime(),
});

export type SM2Result = z.infer<typeof SM2ResultSchema>;
