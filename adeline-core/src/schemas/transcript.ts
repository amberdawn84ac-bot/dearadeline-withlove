/**
 * adeline-core/src/schemas/transcript.ts
 * ─────────────────────────────────────────────────────────────────
 * CASE-compatible transcript entries.
 * Each sealed journal lesson generates TranscriptEntry records
 * via the RegistrarAgent.
 *
 * CASE = Credential and Achievement Standards for Education
 * ─────────────────────────────────────────────────────────────────
 */
import { z } from "zod";
import { Track, EvidenceSchema } from "../types";

export enum CreditType {
  CORE        = "CORE",
  ELECTIVE    = "ELECTIVE",
  PHYSICAL_ED = "PHYSICAL_ED",
  FINE_ARTS   = "FINE_ARTS",
  HOMESTEAD   = "HOMESTEAD",  // Real-world homestead activity converted to credit
}

export enum GradeLetter {
  A_PLUS  = "A+",
  A       = "A",
  A_MINUS = "A-",
  B_PLUS  = "B+",
  B       = "B",
  B_MINUS = "B-",
  C_PLUS  = "C+",
  C       = "C",
  C_MINUS = "C-",
  D       = "D",
  F       = "F",
  PASS    = "PASS",
  FAIL    = "FAIL",
}

export const TranscriptEntrySchema = z.object({
  id:                  z.string().uuid(),
  studentId:           z.string().uuid(),
  courseTitle:         z.string().min(1),
  track:               z.nativeEnum(Track),

  /** Oklahoma Academic Standards code, e.g. "OK-US-8.3" */
  oasStandard:         z.string().optional(),

  /** Free-text description of what the student actually did (not a textbook summary) */
  activityDescription: z.string().min(1),

  /** Fractional Carnegie credit, e.g. 0.25 for 1 week of focused study */
  creditHours:         z.number().min(0).max(2),
  creditType:          z.nativeEnum(CreditType).default(CreditType.CORE),

  gradeLetter:         z.nativeEnum(GradeLetter).optional(),
  percentScore:        z.number().min(0).max(100).optional(),

  completedAt:         z.string().datetime(),
  sealedAt:            z.string().datetime(),

  /** Evidence citations attached to this credit — Witness Protocol chain of custody */
  evidence:            z.array(EvidenceSchema).default([]),

  /** UUID of the xAPI LearningActivity that generated this entry */
  xapiStatementId:     z.string().uuid().optional(),

  isHomesteadCredit:   z.boolean().default(false).describe(
    "True when credit was earned through a real homestead or farm activity"
  ),
});

export type TranscriptEntry = z.infer<typeof TranscriptEntrySchema>;
