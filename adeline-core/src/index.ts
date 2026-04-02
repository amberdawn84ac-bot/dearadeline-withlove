// ── THE GOSPEL — primary DNA export ──────────────────────────────
// All consumers should import from "@adeline/core".
// types.ts is the canonical source of truth for all base types.
export * from "./types";

// ── Schema modules ──────────────────────────────────────────────
export * from "./schemas/studentProfile";
export * from "./schemas/transcript";
export * from "./schemas/learningActivity";
export * from "./schemas/spacedRepetition";
export * from "./schemas/knowledgeGraph";
export * from "./schemas/agentResponse";
export * from "./schemas/standards";
// ── Evidence schema (declassified docs support) ────────────────────
// Note: EvidenceSchema, WitnessCitationSchema, EvidenceVerdict, and WitnessCitation
// are canonical from types.ts (exported above). evidence.ts provides domain-specific
// extensions: SourceType, SOURCE_TYPE_LABELS, DECLASSIFIED_COLLECTIONS, and ensures
// WITNESS_THRESHOLD stays in sync with TRUTH_THRESHOLD.
export {
  SourceType,
  SOURCE_TYPE_LABELS,
  DECLASSIFIED_COLLECTIONS,
  WITNESS_THRESHOLD,
  evaluateWitnessThreshold
} from "./schemas/evidence";

// ── Config modules ──────────────────────────────────────────────
export * from "./config/tracks";
