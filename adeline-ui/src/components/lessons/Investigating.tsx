"use client";

/**
 * Investigating — field-note callout for the middle truth state.
 * Score >= 0.65 but < 0.85: sources found, not yet fully witnessed.
 *
 * Design: mason jar illustration in the margin, slight rightward lean,
 * Papaya wash with a dashed sketch border — feels like a pencil annotation.
 */

import HeartMagnifier from "@/components/icons/HeartMagnifier";

interface InvestigatingProps {
  topic?: string;
  similarityScore?: number;
  showScore?: boolean;
  className?: string;
}

export default function Investigating({
  topic,
  similarityScore,
  showScore = false,
  className = "",
}: InvestigatingProps) {
  return (
    <div
      className={`relative my-5 ${className}`}
      role="note"
      aria-label="Investigating — source found, awaiting full witness verification"
    >
      {/* ── Slight rightward lean — opposite tilt from ArchiveSilent ── */}
      <div style={{ transform: "rotate(0.8deg)", transformOrigin: "top right" }}>
        <div
          style={{
            backgroundColor: "#FDF4E8",
            border: "2px dashed #BD6809",       // dashed = provisional, not final
            boxShadow: "2px 3px 0px #BD6809",
            padding: "1rem 1.25rem 1rem 1rem",
            display: "flex",
            gap: "1rem",
            alignItems: "flex-start",
            position: "relative",
          }}
        >
          {/* ── Heart magnifier in the left margin ── */}
          <div style={{ flexShrink: 0 }}>
            <HeartMagnifier size={56} />
          </div>

          {/* ── Text content ── */}
          <div className="space-y-2 pt-1">
            {/* Header */}
            <div>
              <p
                className="font-sketch text-base leading-tight"
                style={{ color: "#BD6809" }}
              >
                Still Gathering
                {topic && (
                  <span className="font-body italic font-normal text-sm">
                    {" "}— notes on{" "}
                    <span className="font-sketch">&ldquo;{topic}&rdquo;</span>
                  </span>
                )}
              </p>

              {showScore && similarityScore !== undefined && (
                <p
                  className="font-mono text-xs mt-0.5"
                  style={{ color: "#BD6809", opacity: 0.6 }}
                >
                  similarity: {similarityScore.toFixed(3)} &nbsp;·&nbsp; threshold: 0.85
                </p>
              )}
            </div>

            {/* Body */}
            <p className="font-body text-sm leading-relaxed" style={{ color: "#3D1419" }}>
              We found sources related to this, but they haven&rsquo;t fully cleared
              the Witness threshold yet. Read with curiosity — and check the citations
              before you take notes.
            </p>

            {/* Divider */}
            <svg width="100%" height="5" viewBox="0 0 200 5" preserveAspectRatio="none" aria-hidden="true">
              <path
                d="M0 2.5 C20 1 40 4 60 2.5 C80 1 100 4 120 2.5 C140 1 160 4 180 2.5 C190 2 196 3 200 2.5"
                stroke="#BD6809" strokeWidth="0.85" fill="none" opacity="0.35"
              />
            </svg>

            {/* Footer prompt */}
            <p className="font-sketch text-xs" style={{ color: "#BD6809", opacity: 0.75 }}>
              &#128269; Keep looking — a primary source may still be out there.
            </p>
          </div>

          {/* ── Small pencil mark corner decoration ── */}
          <svg
            width="18" height="18"
            viewBox="0 0 18 18"
            style={{ position: "absolute", bottom: 6, right: 8 }}
            aria-hidden="true"
          >
            <path d="M2 16 L14 4 L16 6 L4 18Z" fill="#BD6809" opacity="0.2" />
            <path d="M14 4 L16 2 L17 3 L16 6Z" fill="#BD6809" opacity="0.35" />
            <path d="M2 16 L1 17 L3 17 L4 18 L2 16Z" fill="#3D1419" opacity="0.25" />
          </svg>
        </div>
      </div>
    </div>
  );
}
