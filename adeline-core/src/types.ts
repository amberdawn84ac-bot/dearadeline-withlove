/**
 * adeline-core/src/types.ts
 * ─────────────────────────────────────────────────────────────────
 * THE GOSPEL — DNA for the entire Dear Adeline 2.0 ecosystem.
 * Every service (adeline-brain, adeline-ui) imports from here.
 * ─────────────────────────────────────────────────────────────────
 */
import { z } from "zod";

// ══════════════════════════════════════════════════════════════════
// 1. THE 10-TRACK CONSTITUTION
// ══════════════════════════════════════════════════════════════════

export enum Track {
  CREATION_SCIENCE      = "CREATION_SCIENCE",      // 1. God's Creation & Science
  HEALTH_NATUROPATHY    = "HEALTH_NATUROPATHY",     // 2. Health / Naturopathy
  HOMESTEADING          = "HOMESTEADING",           // 3. Homesteading & Stewardship
  GOVERNMENT_ECONOMICS  = "GOVERNMENT_ECONOMICS",   // 4. Government / Economics
  JUSTICE_CHANGEMAKING  = "JUSTICE_CHANGEMAKING",   // 5. Justice / Change-making
  DISCIPLESHIP          = "DISCIPLESHIP",           // 6. Discipleship & Discernment
  TRUTH_HISTORY         = "TRUTH_HISTORY",          // 7. Truth-Based History
  ENGLISH_LITERATURE    = "ENGLISH_LITERATURE",     // 8. English Language & Literature
  APPLIED_MATHEMATICS   = "APPLIED_MATHEMATICS",    // 9. Applied Mathematics (real-world math)
  CREATIVE_ECONOMY      = "CREATIVE_ECONOMY",       // 10. Creative Economy (making, crafting, selling)
}

export const TRACK_LABELS: Record<Track, string> = {
  [Track.CREATION_SCIENCE]:     "God's Creation & Science",
  [Track.HEALTH_NATUROPATHY]:   "Health & Naturopathy",
  [Track.HOMESTEADING]:         "Homesteading & Stewardship",
  [Track.GOVERNMENT_ECONOMICS]: "Government & Economics",
  [Track.JUSTICE_CHANGEMAKING]: "Justice & Change-making",
  [Track.APPLIED_MATHEMATICS]:  "Applied Mathematics",
  [Track.CREATIVE_ECONOMY]:     "Creative Economy",
  [Track.DISCIPLESHIP]:         "Discipleship & Discernment",
  [Track.TRUTH_HISTORY]:        "Truth-Based History",
  [Track.ENGLISH_LITERATURE]:   "English Language & Literature",
};

// ══════════════════════════════════════════════════════════════════
// 2. TRACK THEME — Sketchnote Color Palette
// ══════════════════════════════════════════════════════════════════

export const COLORS = {
  PAPAYA:  "#BD6809",
  PARADISE: "#9A3F4A",
  FUSCHIA:  "#3D1419",
} as const;

export type TrackThemeEntry = {
  primary: string;
  label: string;
};

/**
 * Maps each of the 10 Tracks to its Sketchnote accent color.
 * Used by GenUIRenderer and any styled track badge in adeline-ui.
 */
export const TRACK_THEME: Record<Track, TrackThemeEntry> = {
  [Track.CREATION_SCIENCE]:     { primary: COLORS.PAPAYA,   label: TRACK_LABELS[Track.CREATION_SCIENCE] },
  [Track.HEALTH_NATUROPATHY]:   { primary: COLORS.PARADISE, label: TRACK_LABELS[Track.HEALTH_NATUROPATHY] },
  [Track.HOMESTEADING]:         { primary: COLORS.PAPAYA,   label: TRACK_LABELS[Track.HOMESTEADING] },
  [Track.GOVERNMENT_ECONOMICS]: { primary: COLORS.FUSCHIA,  label: TRACK_LABELS[Track.GOVERNMENT_ECONOMICS] },
  [Track.JUSTICE_CHANGEMAKING]: { primary: COLORS.PARADISE, label: TRACK_LABELS[Track.JUSTICE_CHANGEMAKING] },
  [Track.DISCIPLESHIP]:         { primary: COLORS.FUSCHIA,  label: TRACK_LABELS[Track.DISCIPLESHIP] },
  [Track.TRUTH_HISTORY]:        { primary: COLORS.PARADISE, label: TRACK_LABELS[Track.TRUTH_HISTORY] },
  [Track.ENGLISH_LITERATURE]:   { primary: COLORS.PAPAYA,   label: TRACK_LABELS[Track.ENGLISH_LITERATURE] },
  [Track.APPLIED_MATHEMATICS]:  { primary: COLORS.PARADISE, label: TRACK_LABELS[Track.APPLIED_MATHEMATICS] },
  [Track.CREATIVE_ECONOMY]:     { primary: COLORS.PAPAYA,   label: TRACK_LABELS[Track.CREATIVE_ECONOMY] },
};

/** Convenience array of all 10 track values. */
export const ALL_TRACKS = Object.values(Track);

// ══════════════════════════════════════════════════════════════════
// 3. THE WITNESS THRESHOLD
// ══════════════════════════════════════════════════════════════════

/**
 * If a vector similarity search returns a score below this value,
 * adeline-brain MUST return ARCHIVE_SILENT — no content is generated.
 */
export const TRUTH_THRESHOLD = 0.82; // calibrated for text-embedding-3-small

export enum EvidenceVerdict {
  VERIFIED         = "VERIFIED",          // score >= 0.85 — safe to present
  ARCHIVE_SILENT   = "ARCHIVE_SILENT",    // score <  0.85 — do NOT generate
  RESEARCH_MISSION = "RESEARCH_MISSION",  // pivot to student inquiry
}

// ══════════════════════════════════════════════════════════════════
// 4. ZOD SCHEMAS
// ══════════════════════════════════════════════════════════════════

// ── 4a. EvidenceSchema ─────────────────────────────────────────────

export const WitnessCitationSchema = z.object({
  author:      z.string().min(1).describe("Full name of the primary author or institution"),
  year:        z.number().int().min(1000).max(new Date().getFullYear()).describe("Year of publication or original record"),
  archiveName: z.string().min(1).describe("Name of the archive, library, or repository holding this source"),
});

export type WitnessCitation = z.infer<typeof WitnessCitationSchema>;

export const EvidenceSchema = z.object({
  sourceId:        z.string().uuid(),
  sourceTitle:     z.string().min(1),
  sourceUrl:       z.string().url(),
  witnessCitation: WitnessCitationSchema,
  similarityScore: z.number().min(0).max(1),
  verdict:         z.nativeEnum(EvidenceVerdict),
  chunk:           z.string().describe("Raw text passage retrieved from the Hippocampus"),
  retrievedAt:     z.string().datetime(),
}).superRefine((data, ctx) => {
  // Chain of Custody: verdict must be strictly consistent with similarityScore.
  // adeline-brain cannot set a verdict that contradicts the measured score.
  if (data.similarityScore < TRUTH_THRESHOLD && data.verdict !== EvidenceVerdict.ARCHIVE_SILENT) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["verdict"],
      message:
        `similarityScore ${data.similarityScore} is below TRUTH_THRESHOLD (${TRUTH_THRESHOLD}). ` +
        `verdict must be ARCHIVE_SILENT — got "${data.verdict}".`,
    });
  }
  if (data.similarityScore >= TRUTH_THRESHOLD && data.verdict === EvidenceVerdict.ARCHIVE_SILENT) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["verdict"],
      message:
        `similarityScore ${data.similarityScore} meets TRUTH_THRESHOLD (${TRUTH_THRESHOLD}). ` +
        `verdict cannot be ARCHIVE_SILENT.`,
    });
  }
});

export type Evidence = z.infer<typeof EvidenceSchema>;

// ── 4b. UserSchema ─────────────────────────────────────────────────

export enum UserRole {
  STUDENT = "STUDENT",
  PARENT  = "PARENT",
  ADMIN   = "ADMIN",
}

export const UserSchema = z.object({
  id:          z.string().uuid(),
  name:        z.string().min(1),
  email:       z.string().email(),
  role:        z.enum(["STUDENT", "PARENT", "ADMIN"]),
  isHomestead: z.boolean().default(false).describe(
    "When true, all lesson content adapts to land-based, self-sufficient application"
  ),
  gradeLevel:  z.string().optional().describe("Required when role is STUDENT (e.g. '4', 'K')"),
  createdAt:   z.string().datetime(),
  updatedAt:   z.string().datetime(),
}).refine(
  (data) => data.role !== "STUDENT" || data.gradeLevel !== undefined,
  { message: "gradeLevel is required for STUDENT role", path: ["gradeLevel"] }
);

export type User = z.infer<typeof UserSchema>;

// ── 4c. REALITY LAYER SCHEMAS (needed before LessonBlockSchema) ─────

export enum WeightTier {
  CORE_TRUTH        = 1,
  WORKING_KNOWLEDGE = 2,
  EXPOSURE          = 3,
}

export const WEIGHT_TIER_LABELS: Record<WeightTier, string> = {
  [WeightTier.CORE_TRUTH]:        "Core Truth",
  [WeightTier.WORKING_KNOWLEDGE]: "Working Knowledge",
  [WeightTier.EXPOSURE]:          "Exposure",
};

export const WEIGHT_TIER_COLORS: Record<WeightTier, { bg: string; text: string; accent: string }> = {
  [WeightTier.CORE_TRUTH]:        { bg: "#FEE2E2", text: "#991B1B", accent: "#DC2626" },
  [WeightTier.WORKING_KNOWLEDGE]: { bg: "#FEF3C7", text: "#92400E", accent: "#F59E0B" },
  [WeightTier.EXPOSURE]:          { bg: "#F3F4F6", text: "#374151", accent: "#9CA3AF" },
};

export const DistortionFlagSchema = z.object({
  id:                  z.string().uuid(),
  commonClaim:         z.string().min(10),
  whatsHidden:         z.string().min(10),
  whatActuallyHappens: z.string().min(10),
  whyItMatters:        z.string().min(5),
});

export type DistortionFlag = z.infer<typeof DistortionFlagSchema>;

export const KeystoneConceptSchema = z.object({
  id:               z.string().uuid(),
  concept:          z.string().min(5),
  firstIntroduced:  z.boolean().default(false),
  context:          z.string().optional(),
  repetitionNumber: z.number().int().min(1).max(4).default(1),
});

export type KeystoneConcept = z.infer<typeof KeystoneConceptSchema>;

export const DistractionBoxSchema = z.object({
  id:           z.string().uuid(),
  topic:        z.string().min(5),
  reason:       z.string().min(10),
  whenToReturn: z.string().optional(),
});

export type DistractionBox = z.infer<typeof DistractionBoxSchema>;

export const RealityLayerMetadataSchema = z.object({
  weightTier:       z.nativeEnum(WeightTier),
  distortionFlags:  z.array(DistortionFlagSchema).default([]),
  keystoneConcept:  KeystoneConceptSchema.optional(),
  distractionBoxes: z.array(DistractionBoxSchema).default([]),
  importanceFilter: z.object({
    survivalFunction: z.boolean(),
    powerSystems:     z.boolean(),
    permanence:       z.boolean(),
  }),
});

export type RealityLayerMetadata = z.infer<typeof RealityLayerMetadataSchema>;

// ── 4d. LessonBlockSchema ──────────────────────────────────────────

export enum BlockType {
  TEXT             = "TEXT",             // Plain reading passage
  NARRATIVE        = "NARRATIVE",        // Story-driven worldview content (DiscipleshipAgent)
  PRIMARY_SOURCE   = "PRIMARY_SOURCE",   // Historical/scientific primary document — evidence required
  LAB_MISSION      = "LAB_MISSION",      // Hands-on homestead/science activity
  EXPERIMENT       = "EXPERIMENT",       // Sovereign Lab — student films as portfolio evidence
  RESEARCH_MISSION = "RESEARCH_MISSION", // Assigned when Witness Protocol fires ARCHIVE_SILENT
  QUIZ             = "QUIZ",             // Knowledge check
  DATA_TRACKING    = "DATA_TRACKING",    // Applied Math / Science metric logging
  PROBLEM          = "PROBLEM",          // Applied Math contextual problem
  WRITING          = "WRITING",          // English / Creative Economy composition prompt
}

export enum DifficultyLevel {
  EMERGING   = "EMERGING",    // K–2
  DEVELOPING = "DEVELOPING",  // 3–5
  EXPANDING  = "EXPANDING",   // 6–8
  MASTERING  = "MASTERING",   // 9–12
}

const HomesteadVariantSchema = z.object({
  enabled:             z.boolean(),
  alternateContent:    z.string().describe("Land/homestead-adapted version of block content"),
  practicalApplication: z.string().optional(),
});

export const LessonBlockSchema = z.object({
  id:         z.string().uuid(),
  lessonId:   z.string().uuid(),
  track:      z.nativeEnum(Track),
  blockType:  z.nativeEnum(BlockType),
  difficulty: z.nativeEnum(DifficultyLevel),
  order:      z.number().int().min(0),

  title:   z.string().min(1),
  content: z.string().describe(
    "Block content. TRUTH_HISTORY blocks must be evidence-backed or isSilenced=true"
  ),

  evidence:         z.array(EvidenceSchema).default([]),
  homesteadVariant: HomesteadVariantSchema.optional(),

  /**
   * Reality Layer metadata: truth weights, distortion flags, keystones, distractions.
   * Applied by adeline-brain to augment educational depth and cultural literacy.
   */
  realityLayer: RealityLayerMetadataSchema.optional(),

  /**
   * Set to true by adeline-brain when the Witness Protocol fires (ARCHIVE_SILENT).
   * adeline-ui must never render a silenced block.
   */
  isSilenced: z.boolean().default(false),

  tags:      z.array(z.string()).default([]),
  createdAt: z.string().datetime(),
}).superRefine((data, ctx) => {
  // Chain of Custody: PRIMARY_SOURCE blocks must carry at least one Evidence entry.
  // If evidence is absent, adeline-brain made an error — reject at the schema layer.
  if (data.blockType === BlockType.PRIMARY_SOURCE && data.evidence.length === 0) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["evidence"],
      message:
        "A PRIMARY_SOURCE block must include at least one Evidence entry. " +
        "A Primary Source without provenance is not permitted in Adeline 2.0. " +
        "If no verified source exists, set blockType to RESEARCH_MISSION instead.",
    });
  }
});

export type LessonBlock = z.infer<typeof LessonBlockSchema>;

export const LessonSchema = z.object({
  id:               z.string().uuid(),
  title:            z.string().min(1),
  tracks:           z.array(z.nativeEnum(Track)).min(1),
  blocks:           z.array(LessonBlockSchema),
  targetGrades:     z.array(z.string()),
  estimatedMinutes: z.number().int().min(5),
  createdAt:        z.string().datetime(),
  updatedAt:        z.string().datetime(),
});

export type Lesson = z.infer<typeof LessonSchema>;

// ══════════════════════════════════════════════════════════════════
// 5. WITNESS PROTOCOL HELPER
// ══════════════════════════════════════════════════════════════════

export function evaluateWitness(score: number): EvidenceVerdict {
  return score >= TRUTH_THRESHOLD
    ? EvidenceVerdict.VERIFIED
    : EvidenceVerdict.ARCHIVE_SILENT;
}
