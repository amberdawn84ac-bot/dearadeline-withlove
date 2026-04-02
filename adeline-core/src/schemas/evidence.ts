import { z } from "zod";

/**
 * Witness Protocol Threshold
 * If a historical search similarity score falls below this value,
 * adeline-brain must return ARCHIVE_SILENT instead of generating content.
 */
export const WITNESS_THRESHOLD = 0.85;

export enum EvidenceVerdict {
  VERIFIED = "VERIFIED",           // similarity >= 0.85, safe to present
  ARCHIVE_SILENT = "ARCHIVE_SILENT", // similarity < 0.85, do NOT hallucinate
  RESEARCH_MISSION = "RESEARCH_MISSION", // pivot: assign student a research task
}

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

export const EvidenceSchema = z.object({
  sourceId: z.string().uuid().describe("Unique ID of the source document in the vector store"),
  sourceTitle: z.string(),
  sourceUrl: z.string().url().optional(),
  sourceType: z.nativeEnum(SourceType).default(SourceType.PRIMARY_SOURCE),
  similarityScore: z.number().min(0).max(1),
  verdict: z.nativeEnum(EvidenceVerdict),
  retrievedAt: z.string().datetime(),
  chunk: z.string().describe("The raw text chunk retrieved from the Hippocampus"),
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
