"use client";

/**
 * BlockWrapper — the outer shell for every lesson block.
 *
 * PRIMARY_SOURCE   → Paradise (#9A3F4A) left-border + Verified Seal badge
 * RESEARCH_MISSION → Papaya (#BD6809) dashed sticky-note border
 * NARRATIVE / rest → Standard sketch-card with fuschia border
 */

import VerifiedSeal from "@/components/icons/VerifiedSeal";
import type { LessonBlockResponse } from "@/lib/brain-client";

interface BlockWrapperProps {
  block: LessonBlockResponse;
  children: React.ReactNode;
  showScores?: boolean;
}

type BlockStyle = {
  wrapper: React.CSSProperties;
  label: string;
  labelStyle: React.CSSProperties;
};

function getBlockStyle(type: string): BlockStyle {
  switch (type) {
    case "PRIMARY_SOURCE":
      return {
        wrapper: {
          background: "#FDF8F0",
          border: "2px solid #9A3F4A",       // Paradise
          borderLeft: "6px solid #9A3F4A",
          boxShadow: "3px 4px 0 #9A3F4A44",
          padding: "1.25rem 1.5rem",
          position: "relative",
        },
        label: "Primary Source",
        labelStyle: { background: "#9A3F4A", color: "#FDF8F0" },
      };
    case "RESEARCH_MISSION":
      return {
        wrapper: {
          background: "#FDF4E8",
          border: "2px dashed #BD6809",      // Papaya
          boxShadow: "3px 4px 0 #BD680933",
          padding: "1.25rem 1.5rem",
          position: "relative",
          transform: "rotate(-0.4deg)",
          transformOrigin: "top left",
        },
        label: "Research Mission",
        labelStyle: { background: "#BD6809", color: "#FDF8F0" },
      };
    default:
      return {
        wrapper: {
          background: "#FDF8F0",
          border: "2px solid #3D1419",
          boxShadow: "3px 4px 0 #3D141933",
          padding: "1.25rem 1.5rem",
        },
        label: type.replace(/_/g, " "),
        labelStyle: { background: "#3D1419", color: "#FDF8F0" },
      };
  }
}

export default function BlockWrapper({
  block,
  children,
  showScores = false,
}: BlockWrapperProps) {
  const style = getBlockStyle(block.block_type);
  const topEvidence = block.evidence[0];
  const score = topEvidence?.similarity_score;
  const isPrimarySource = block.block_type === "PRIMARY_SOURCE";

  return (
    <div style={style.wrapper}>
      {/* ── Header row ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-3">
        <span
          className="font-sketch text-xs uppercase tracking-widest px-2 py-0.5 rounded-sm"
          style={style.labelStyle}
        >
          {style.label}
        </span>

        {isPrimarySource && topEvidence?.verdict === "VERIFIED" && score !== undefined && (
          <VerifiedSeal similarityScore={score} size={36} showScore={showScores} />
        )}
      </div>

      {/* ── Block content ─────────────────────────────────────────── */}
      {children}

      {/* ── Citation footer (PRIMARY_SOURCE only) ─────────────────── */}
      {isPrimarySource && topEvidence && (
        <div className="mt-4 pt-3 border-t border-paradise/20">
          <p className="font-mono text-xs text-fuschia/60">
            {topEvidence.source_title}
            {topEvidence.witness_citation?.author && (
              <>
                {" "}— {topEvidence.witness_citation.author}
                {topEvidence.witness_citation.year && `, ${topEvidence.witness_citation.year}`}
              </>
            )}
          </p>
          {topEvidence.source_url && (
            <a
              href={topEvidence.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-papaya hover:underline"
            >
              {topEvidence.source_url}
            </a>
          )}
          {showScores && (
            <p className="font-mono text-xs text-paradise/60 mt-1">
              similarity: {score?.toFixed(4)} &ge; 0.85
            </p>
          )}
        </div>
      )}
    </div>
  );
}
