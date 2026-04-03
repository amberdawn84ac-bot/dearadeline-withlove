/**
 * Three-tier truth status for the Field Note UI.
 *
 *  VERIFIED      — score >= 0.82  → VerifiedSeal renders, content is shown
 *  INVESTIGATING — score >= 0.65  → Caution state, content renders with warning
 *  ARCHIVE_SILENT — score <  0.65  → ArchiveSilent component replaces content
 *
 * The hard gate (TRUTH_THRESHOLD = 0.82) from adeline-core is the boundary
 * between VERIFIED and INVESTIGATING. ARCHIVE_SILENT is a deeper silence —
 * not just uncertain, but genuinely unwitnessed.
 */

const TRUTH_THRESHOLD = 0.82;

export type TruthStatus = "VERIFIED" | "INVESTIGATING" | "ARCHIVE_SILENT";

const INVESTIGATING_FLOOR = 0.65;

export function getTruthStatus(score: number): TruthStatus {
  if (score >= TRUTH_THRESHOLD)    return "VERIFIED";
  if (score >= INVESTIGATING_FLOOR) return "INVESTIGATING";
  return "ARCHIVE_SILENT";
}

export const TRUTH_STATUS_META: Record<
  TruthStatus,
  { label: string; color: string; description: string }
> = {
  VERIFIED: {
    label: "Verified",
    color: "#9A3F4A",   // Paradise
    description: "Primary source confirmed. Similarity score meets the Witness threshold.",
  },
  INVESTIGATING: {
    label: "Investigating",
    color: "#BD6809",   // Papaya
    description: "Source found but confidence is below the Witness threshold. Treat with discernment.",
  },
  ARCHIVE_SILENT: {
    label: "Archive Silent",
    color: "#3D1419",   // Fuschia
    description: "No sufficient primary source located. Content withheld per the Witness Protocol.",
  },
};

/** Convenience — returns true only when the Witness Protocol clears the block for display. */
export function isWitnessVerified(score: number): boolean {
  return getTruthStatus(score) === "VERIFIED";
}
