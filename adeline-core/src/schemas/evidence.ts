import { z } from "zod";
import { EvidenceVerdict, TRUTH_THRESHOLD } from "../types";

/**
 * Witness Protocol Threshold
 * If a historical search similarity score falls below this value,
 * adeline-brain must return ARCHIVE_SILENT instead of generating content.
 * MUST match TRUTH_THRESHOLD in types.ts (0.82 canonical).
 */
export const WITNESS_THRESHOLD = TRUTH_THRESHOLD;

export enum SourceType {
  PRIMARY_SOURCE = "PRIMARY_SOURCE",
  DECLASSIFIED_GOV = "DECLASSIFIED_GOV",
  ARCHIVE_ORG = "ARCHIVE_ORG",
  ACADEMIC_JOURNAL = "ACADEMIC_JOURNAL",
  PERSONAL_COLLECTION = "PERSONAL_COLLECTION",
}

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  [SourceType.PRIMARY_SOURCE]: "Primary Source",
  [SourceType.DECLASSIFIED_GOV]: "Declassified Document",
  [SourceType.ARCHIVE_ORG]: "Archive.org",
  [SourceType.ACADEMIC_JOURNAL]: "Academic Journal",
  [SourceType.PERSONAL_COLLECTION]: "Personal Collection",
};

export const DECLASSIFIED_COLLECTIONS: Record<string, string> = {
  NARA: "https://catalog.archives.gov/search",
  CIA_FOIA: "https://www.cia.gov/information-freedom/records-available-online/",
  FBI_VAULT: "https://vault.fbi.gov/",
  CONGRESSIONAL_RECORD: "https://www.congress.gov/congressional-record/",
  FEDERAL_REGISTER: "https://www.federalregister.gov/",
  DNSA: "https://nsarchive.gwu.edu/",
};

export const WitnessCitationSchema = z.object({
  author:      z.string().min(1).describe("Full name of the primary author or institution"),
  year:        z.number().int().min(1000).max(new Date().getFullYear()).describe("Year of publication or original record"),
  archiveName: z.string().min(1).describe("Name of the archive, library, or repository holding this source"),
});

export type WitnessCitation = z.infer<typeof WitnessCitationSchema>;

export const EvidenceSchema = z.object({
  sourceId:        z.string().uuid().describe("Unique ID of the source document in the vector store"),
  sourceTitle:     z.string().min(1),
  sourceUrl:       z.string().url(),
  witnessCitation: WitnessCitationSchema,
  sourceType:      z.nativeEnum(SourceType).default(SourceType.PRIMARY_SOURCE),
  similarityScore: z.number().min(0).max(1),
  verdict:         z.nativeEnum(EvidenceVerdict),
  retrievedAt:     z.string().datetime(),
  chunk:           z.string().describe("Raw text passage retrieved from the Hippocampus"),
}).superRefine((data, ctx) => {
  // Chain of Custody: verdict must be strictly consistent with similarityScore.
  // adeline-brain cannot set a verdict that contradicts the measured score.
  if (data.similarityScore < WITNESS_THRESHOLD && data.verdict !== EvidenceVerdict.ARCHIVE_SILENT) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["verdict"],
      message:
        `similarityScore ${data.similarityScore} is below WITNESS_THRESHOLD (${WITNESS_THRESHOLD}). ` +
        `verdict must be ARCHIVE_SILENT — got "${data.verdict}".`,
    });
  }
  if (data.similarityScore >= WITNESS_THRESHOLD && data.verdict === EvidenceVerdict.ARCHIVE_SILENT) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["verdict"],
      message:
        `similarityScore ${data.similarityScore} meets WITNESS_THRESHOLD (${WITNESS_THRESHOLD}). ` +
        `verdict cannot be ARCHIVE_SILENT.`,
    });
  }
});

export type Evidence = z.infer<typeof EvidenceSchema>;

/**
 * Evaluate a similarity score against the Witness Protocol threshold.
 * Returns the correct EvidenceVerdict.
 */
export function evaluateWitnessThreshold(score: number): EvidenceVerdict {
  if (score >= WITNESS_THRESHOLD) return EvidenceVerdict.VERIFIED;
  return EvidenceVerdict.ARCHIVE_SILENT;
}
