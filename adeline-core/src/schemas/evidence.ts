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

export const EvidenceSchema = z.object({
  sourceId: z.string().uuid().describe("Unique ID of the source document in the vector store"),
  sourceTitle: z.string(),
  sourceUrl: z.string().url().optional(),
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
