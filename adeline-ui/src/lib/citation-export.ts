/**
 * citation-export.ts
 *
 * Lesson citation export helpers.
 * Supports MLA format. Chicago and APA stubs reserved for future tracks.
 *
 * formatMLA / formatMLAWork are pure functions — no DOM, safe for SSR / tests.
 * downloadCitation is browser-only (uses Blob + URL.createObjectURL).
 */

import type { LessonResponse, LessonBlockResponse, Evidence } from "@/lib/brain-client";

// Re-export the brain-client types so consumers can import from one place.
export type { LessonResponse, LessonBlockResponse, Evidence };

// ── MLA formatting ────────────────────────────────────────────────────────────

/**
 * Format a single Evidence record as an MLA works-cited entry.
 *
 * Pattern: Author. "Title." Year. Retrieved from URL
 */
// ASCII double-quote constant — avoids editor smart-quote substitution
const Q = String.fromCharCode(34); // "

export function formatMLAWork(evidence: Evidence): string {
  const author = evidence.witness_citation?.author || "Unknown Author";
  const year   = evidence.witness_citation?.year   ?? "n.d.";
  const title  = evidence.source_title;
  const url    = evidence.source_url;

  return `${author}. ${Q}${title}.${Q} ${year}. Retrieved from ${url}`;
}

/**
 * Format a full lesson's verified and mission blocks as an MLA works-cited page.
 *
 * Deduplicates identical entries (same author + title + year may appear in
 * multiple blocks).  Returns a plain-text string safe for .txt download.
 */
export function formatMLA(lesson: LessonResponse): string {
  const citedWorks = lesson.blocks
    .filter((b: LessonBlockResponse) => b.evidence.length > 0 && b.evidence[0])
    .map((b: LessonBlockResponse) => formatMLAWork(b.evidence[0]));

  const uniqueCitations = [...new Set(citedWorks)];

  if (uniqueCitations.length === 0) {
    return `${lesson.title}\n\nWorks Cited:\n\n(No cited sources found in this lesson.)`;
  }

  return `${lesson.title}\n\nWorks Cited:\n\n${uniqueCitations.join("\n")}`;
}

// ── Download (browser-only) ───────────────────────────────────────────────────

export type CitationFormat = "mla";

/**
 * Trigger a browser file-download of the lesson's citations.
 *
 * @param lesson  - Full LessonResponse from adeline-brain
 * @param format  - Citation format; currently only "mla" is supported
 */
export function downloadCitation(
  lesson: LessonResponse,
  format: CitationFormat = "mla",
): void {
  const text = formatMLA(lesson); // only mla for now; extend when Chicago/APA land
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `${lesson.title.replace(/[^a-z0-9]/gi, "-").toLowerCase()}-citations.txt`;
  a.click();
  // Clean up the object URL after the click so there's no memory leak
  setTimeout(() => URL.revokeObjectURL(url), 100);
}
