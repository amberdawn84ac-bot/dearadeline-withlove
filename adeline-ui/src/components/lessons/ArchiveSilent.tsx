"use client";

/**
 * ArchiveSilent — marginalia-style callout rendered when the Witness Protocol
 * returns ARCHIVE_SILENT (similarityScore < 0.85).
 *
 * Design: handwritten callout with slight tilt, faint Papaya background,
 * sketch border — evokes a field note written in the margin of a primary source.
 */

interface ArchiveSilentProps {
  /** Optional topic that triggered the silence — used to personalize the message */
  topic?: string;
  /** The actual similarity score that failed the threshold */
  similarityScore?: number;
  /** Show the score for educator/parent transparency mode */
  showScore?: boolean;
  className?: string;
}

export default function ArchiveSilent({
  topic,
  similarityScore,
  showScore = false,
  className = "",
}: ArchiveSilentProps) {
  return (
    <div
      className={`relative my-6 ${className}`}
      role="note"
      aria-label="Archive silent — content withheld pending verified sources"
    >
      {/* ── Tilt wrapper (marginalia feel) ── */}
      <div
        style={{
          transform: "rotate(-1.2deg)",
          transformOrigin: "top left",
        }}
      >
        {/* ── Main callout box ── */}
        <div
          style={{
            backgroundColor: "#FDF4E8",      // faint Papaya wash
            border: "2px solid #BD6809",     // Papaya border
            boxShadow: "3px 4px 0px #BD6809", // sketch shadow offset
            padding: "1.25rem 1.5rem",
            position: "relative",
          }}
        >
          {/* ── Corner fold mark (top-right) ── */}
          <div
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              width: 0,
              height: 0,
              borderStyle: "solid",
              borderWidth: "0 18px 18px 0",
              borderColor: `transparent #BD6809 transparent transparent`,
              opacity: 0.4,
            }}
            aria-hidden="true"
          />

          {/* ── Header row ── */}
          <div className="flex items-start gap-3 mb-3">
            {/* Hand-drawn silence glyph */}
            <svg
              width="28"
              height="28"
              viewBox="0 0 28 28"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
              style={{ flexShrink: 0, marginTop: "2px" }}
            >
              {/* Quill / pen nib shape */}
              <path
                d="M14 3 C18 6 24 10 22 18 C20 24 15 26 14 26 C13 26 8 24 6 18 C4 10 10 6 14 3Z"
                stroke="#BD6809"
                strokeWidth="1.25"
                fill="none"
              />
              <path
                d="M14 3 C14 10 14 18 14 26"
                stroke="#BD6809"
                strokeWidth="0.85"
                strokeDasharray="2 2"
              />
              {/* Small crossed lines — the 'silent' mark */}
              <path
                d="M10 22 L18 22"
                stroke="#BD6809"
                strokeWidth="1"
                strokeLinecap="round"
              />
              <path
                d="M11 19 L17 25"
                stroke="#BD6809"
                strokeWidth="0.75"
                strokeLinecap="round"
                opacity="0.5"
              />
            </svg>

            <div>
              <p
                className="font-sketch text-base leading-tight"
                style={{ color: "#BD6809" }}
              >
                The Archives Are Silent
                {topic && (
                  <span className="font-body italic font-normal">
                    {" "}on{" "}
                    <span className="font-sketch">&ldquo;{topic}&rdquo;</span>
                  </span>
                )}
              </p>

              {showScore && similarityScore !== undefined && (
                <p
                  className="font-mono text-xs mt-0.5 opacity-60"
                  style={{ color: "#BD6809" }}
                >
                  similarity: {similarityScore.toFixed(3)} &lt; 0.85 threshold
                </p>
              )}
            </div>
          </div>

          {/* ── Body copy ── */}
          <p
            className="font-body text-sm leading-relaxed"
            style={{ color: "#3D1419" }}
          >
            The archives are silent on this specific detail. We are prioritizing
            primary source accuracy over AI assumptions.
          </p>

          {/* ── Divider rule (hand-drawn style) ── */}
          <div className="mt-3 mb-2">
            <svg width="100%" height="6" viewBox="0 0 300 6" preserveAspectRatio="none" aria-hidden="true">
              <path
                d="M0 3 C30 1 60 5 90 3 C120 1 150 5 180 3 C210 1 240 5 270 3 C285 2 295 4 300 3"
                stroke="#BD6809"
                strokeWidth="1"
                fill="none"
                opacity="0.4"
              />
            </svg>
          </div>

          {/* ── Research mission prompt ── */}
          <p
            className="font-sketch text-xs"
            style={{ color: "#BD6809", opacity: 0.8 }}
          >
            &#8594; A Research Mission has been assigned. Seek the primary source.
          </p>
        </div>
      </div>

      {/* ── Subtle second-shadow for depth (slightly offset, not rotated) ── */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          transform: "rotate(-1.2deg) translate(6px, 6px)",
          border: "1.5px solid #BD6809",
          opacity: 0.12,
          zIndex: -1,
          transformOrigin: "top left",
        }}
      />
    </div>
  );
}
