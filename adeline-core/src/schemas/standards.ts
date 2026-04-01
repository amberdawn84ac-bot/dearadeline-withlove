import { z } from "zod";

// ── Frameworks ────────────────────────────────────────────────────────────────

export enum StandardsFramework {
  OAS        = "OAS",         // Oklahoma Academic Standards (overlay only — not a control mechanism)
  OSRHE_CORE = "OSRHE_CORE", // Oklahoma State Regents for Higher Ed — 15-unit core
  LOCAL      = "LOCAL",       // Family/co-op defined standard
}

// ── Subjects ──────────────────────────────────────────────────────────────────

export enum StandardsSubject {
  ELA            = "ELA",
  SCIENCE        = "SCIENCE",
  SOCIAL_STUDIES = "SOCIAL_STUDIES",
  HEALTH         = "HEALTH",
  WORLD_LANGUAGES = "WORLD_LANGUAGES",
  MATH           = "MATH",
  INFO_LIT       = "INFO_LIT",
}

// ── StandardsTag ──────────────────────────────────────────────────────────────

/**
 * A lightweight tag that marks which standards framework a lesson or evidence
 * entry addresses. OAS is an overlay — it never controls what gets taught.
 */
export const StandardsTagSchema = z.object({
  framework: z.nativeEnum(StandardsFramework),
  subject:   z.nativeEnum(StandardsSubject),
  code:      z.string().optional(),
  weight:    z.number().min(0).max(1),
});

export type StandardsTag = z.infer<typeof StandardsTagSchema>;

// ── Credit Buckets ────────────────────────────────────────────────────────────

/**
 * Transcript-visible credit categories. The Oklahoma OSRHE 15-unit core maps
 * to ENGLISH (4), LAB_SCIENCE (3), MATH (3), SOCIAL_STUDIES (3), plus ELECTIVE (2).
 */
export enum CreditBucket {
  ENGLISH        = "ENGLISH",
  MATH           = "MATH",
  LAB_SCIENCE    = "LAB_SCIENCE",
  SOCIAL_STUDIES = "SOCIAL_STUDIES",
  HEALTH         = "HEALTH",
  WORLD_LANGUAGE = "WORLD_LANGUAGE",
  FINE_ARTS      = "FINE_ARTS",
  ELECTIVE       = "ELECTIVE",
  PFL            = "PFL",             // Personal Financial Literacy
}

// ── Learning Evidence ─────────────────────────────────────────────────────────

/**
 * One artifact that a student produced. Evidence accumulates in the EvidenceLedger.
 * When enough weighted evidence fills a CreditBucket, the system *proposes*
 * a transcript course — human approval required before it appears on the official
 * transcript.
 */
export const LearningEvidenceSchema = z.object({
  artifactType: z.enum([
    "essay",
    "quiz",
    "lab",
    "project",
    "discussion",
    "fieldwork",
    "presentation",
  ]),
  masteryScore: z.number().min(0).max(1),
  hours:        z.number().min(0),
});

export type LearningEvidence = z.infer<typeof LearningEvidenceSchema>;
