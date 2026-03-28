// ── THE GOSPEL — primary DNA export ──────────────────────────────
// All consumers should import from here. types.ts is the source of truth.
export * from "./types";

// ── Legacy schema modules (kept for internal use by adeline-brain) ─
// Do not import these directly in adeline-ui — use ./types instead.
export * from "./schemas/studentProfile";
