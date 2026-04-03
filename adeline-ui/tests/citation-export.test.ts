/**
 * tests/citation-export.test.ts
 *
 * Unit tests for the MLA citation formatter.
 * downloadCitation uses browser APIs (Blob, URL.createObjectURL) and is
 * covered by a separate jsdom-environment test if needed.
 */

import { describe, it, expect } from "vitest";
import { formatMLA, formatMLAWork } from "@/lib/citation-export";
import type { LessonResponse, Evidence } from "@/lib/citation-export";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const mockEvidence: Evidence = {
  source_id: "e1",
  source_title: "Declaration of Independence",
  source_url: "https://archive.org/declaration",
  witness_citation: {
    author: "Jefferson, Thomas",
    year: 1776,
    archive_name: "National Archives",
  },
  similarity_score: 0.95,
  verdict: "VERIFIED",
  chunk: "We hold these truths to be self-evident...",
};

const makeLesson = (overrides: Partial<LessonResponse> = {}): LessonResponse => ({
  lesson_id: "l1",
  title: "Independence",
  track: "TRUTH_HISTORY",
  blocks: [
    {
      block_id: "b1",
      block_type: "PRIMARY_SOURCE",
      content: "We hold these truths...",
      evidence: [mockEvidence],
      is_silenced: false,
    },
  ],
  has_research_missions: false,
  researcher_activated: false,
  agent_name: "HistorianAgent",
  xapi_statements: [],
  credits_awarded: [],
  oas_standards: [],
  ...overrides,
});

// ── formatMLAWork ─────────────────────────────────────────────────────────────

describe("formatMLAWork", () => {
  it("formats a complete evidence record in MLA style", () => {
    const result = formatMLAWork(mockEvidence);
    expect(result).toContain("Jefferson, Thomas");
    expect(result).toContain("1776");
    expect(result).toContain("Declaration of Independence");
    expect(result).toContain("https://archive.org/declaration");
    // Title should be wrapped in ASCII double-quotes
    const q = String.fromCharCode(34);
    expect(result).toContain(`${q}Declaration of Independence.${q}`);
  });

  it("falls back to 'Unknown Author' when witness_citation.author is missing", () => {
    const evidence: Evidence = {
      ...mockEvidence,
      witness_citation: { author: "", year: null, archive_name: "" },
    };
    const result = formatMLAWork(evidence);
    expect(result).toContain("Unknown Author");
  });

  it("falls back to 'n.d.' when citation year is null", () => {
    const evidence: Evidence = {
      ...mockEvidence,
      witness_citation: { author: "Jefferson, Thomas", year: null, archive_name: "" },
    };
    const result = formatMLAWork(evidence);
    expect(result).toContain("n.d.");
  });
});

// ── formatMLA ─────────────────────────────────────────────────────────────────

describe("formatMLA", () => {
  it("formats MLA citations correctly for a lesson with evidence", () => {
    const lesson = makeLesson();
    const mla = formatMLA(lesson);

    expect(mla).toContain("Jefferson, Thomas");
    expect(mla).toContain("1776");
    expect(mla).toContain("Works Cited:");
    expect(mla).toContain("Independence");
  });

  it("includes the lesson title at the top", () => {
    const lesson = makeLesson({ title: "The Civil War" });
    const mla = formatMLA(lesson);
    expect(mla.startsWith("The Civil War")).toBe(true);
  });

  it("deduplicates identical citations", () => {
    const lesson = makeLesson({
      blocks: [
        {
          block_id: "b1",
          block_type: "PRIMARY_SOURCE",
          content: "First block",
          evidence: [mockEvidence],
          is_silenced: false,
        },
        {
          block_id: "b2",
          block_type: "PRIMARY_SOURCE",
          content: "Second block with same source",
          evidence: [mockEvidence],
          is_silenced: false,
        },
      ],
    });
    const mla = formatMLA(lesson);
    // The same citation string should only appear once
    const occurrences = (mla.match(/Jefferson, Thomas/g) ?? []).length;
    expect(occurrences).toBe(1);
  });

  it("handles lessons with no evidence gracefully", () => {
    const lesson = makeLesson({
      blocks: [
        {
          block_id: "b1",
          block_type: "RESEARCH_MISSION",
          content: "Go find a primary source.",
          evidence: [],
          is_silenced: false,
        },
      ],
    });
    const mla = formatMLA(lesson);
    expect(mla).toContain("No cited sources found");
  });

  it("handles an empty blocks array", () => {
    const lesson = makeLesson({ blocks: [] });
    const mla = formatMLA(lesson);
    expect(mla).toContain("Works Cited:");
    expect(mla).toContain("No cited sources found");
  });
});
