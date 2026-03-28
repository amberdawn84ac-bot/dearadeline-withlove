/**
 * VerifiedSeal — botanical hand-pressed leaf icon.
 * Renders ONLY when similarityScore >= 0.85 (Witness Protocol cleared).
 * Color: Paradise (#9A3F4A).
 */

interface VerifiedSealProps {
  similarityScore: number;
  size?: number;
  /** Show the score alongside the seal */
  showScore?: boolean;
  className?: string;
}

const TRUTH_THRESHOLD = 0.85;

export default function VerifiedSeal({
  similarityScore,
  size = 48,
  showScore = false,
  className = "",
}: VerifiedSealProps) {
  if (similarityScore < TRUTH_THRESHOLD) return null;

  return (
    <span
      className={`inline-flex items-center gap-1.5 ${className}`}
      title={`Witness Verified — similarity score: ${similarityScore.toFixed(2)}`}
      aria-label="Witness verified primary source"
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* ── Outer pressed-seal ring (hand-drawn imperfect circle) ── */}
        <path
          d="M32 4
             C44 3.5 59 14 60 28
             C61 43 51 60 35 61
             C19 62 4 50 3.5 35
             C3 19 14 4.5 32 4Z"
          stroke="#9A3F4A"
          strokeWidth="1.5"
          strokeDasharray="3 2"
          fill="#FDF8F0"
          opacity="0.95"
        />

        {/* ── Inner seal ring ── */}
        <circle
          cx="32"
          cy="32"
          r="22"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeDasharray="2 3"
          fill="none"
          opacity="0.5"
        />

        {/* ── Main leaf body ── */}
        <path
          d="M32 14
             C38 18 46 24 44 33
             C42 41 36 48 32 50
             C28 48 22 41 20 33
             C18 24 26 18 32 14Z"
          fill="#9A3F4A"
          opacity="0.15"
          stroke="#9A3F4A"
          strokeWidth="1.25"
          strokeLinejoin="round"
        />

        {/* ── Central midrib (spine of the leaf) ── */}
        <path
          d="M32 14 C31.5 25 31.8 38 32 50"
          stroke="#9A3F4A"
          strokeWidth="1"
          strokeLinecap="round"
          opacity="0.85"
        />

        {/* ── Left lateral veins ── */}
        <path
          d="M31.5 22 C27 23 24 25 22 27"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeLinecap="round"
          opacity="0.6"
        />
        <path
          d="M31.5 28 C26 29 22 31 21 34"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeLinecap="round"
          opacity="0.6"
        />
        <path
          d="M31.8 34 C27 36 23 38 22 41"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeLinecap="round"
          opacity="0.5"
        />

        {/* ── Right lateral veins ── */}
        <path
          d="M32.5 22 C37 23 40 25 42 27"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeLinecap="round"
          opacity="0.6"
        />
        <path
          d="M32.5 28 C38 29 42 31 43 34"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeLinecap="round"
          opacity="0.6"
        />
        <path
          d="M32.2 34 C37 36 41 38 42 41"
          stroke="#9A3F4A"
          strokeWidth="0.75"
          strokeLinecap="round"
          opacity="0.5"
        />

        {/* ── Small stem ── */}
        <path
          d="M32 50 C31.5 53 30.5 55 30 57"
          stroke="#9A3F4A"
          strokeWidth="1"
          strokeLinecap="round"
          opacity="0.7"
        />

        {/* ── Tiny flourish marks (hand-pressed feel) ── */}
        <path
          d="M10 20 C11 19 12 20 11 21"
          stroke="#9A3F4A"
          strokeWidth="0.6"
          opacity="0.35"
        />
        <path
          d="M52 42 C53 41 54 42 53 43"
          stroke="#9A3F4A"
          strokeWidth="0.6"
          opacity="0.35"
        />
      </svg>

      {showScore && (
        <span
          className="font-mono text-xs tabular-nums"
          style={{ color: "#9A3F4A" }}
        >
          {similarityScore.toFixed(2)}
        </span>
      )}
    </span>
  );
}
