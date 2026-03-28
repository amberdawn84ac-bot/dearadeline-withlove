/**
 * HeartMagnifier — a heart-shaped magnifying glass.
 * The INVESTIGATING truth state icon: looking closely, with love.
 * "Seek and you will find." — Matthew 7:7
 */

interface HeartMagnifierProps {
  size?: number;
  className?: string;
}

export default function HeartMagnifier({ size = 64, className = "" }: HeartMagnifierProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 72"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* ── Heart lens — outer ring (hand-drawn weight) ───────────── */}
      <path
        d="M32 46
           C20 36 8 28 8 18
           C8 10 14 6 20 6
           C25 6 29 9 32 13
           C35 9 39 6 44 6
           C50 6 56 10 56 18
           C56 28 44 36 32 46Z"
        fill="#FDF4E8"
        stroke="#9A3F4A"
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* ── Inner heart fill — faint jewel wash ───────────────────── */}
      <path
        d="M32 42
           C22 33 12 26 12 18
           C12 13 16 10 20 10
           C24 10 28 13 32 17
           C36 13 40 10 44 10
           C48 10 52 13 52 18
           C52 26 42 33 32 42Z"
        fill="#9A3F4A"
        opacity="0.1"
      />

      {/* ── Lens glare — top left highlight ───────────────────────── */}
      <path
        d="M18 12 C17 14 16 17 17 20"
        stroke="#FDF8F0"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.6"
      />
      <path
        d="M21 10 C20 11 19 12 19 13"
        stroke="#FDF8F0"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.45"
      />

      {/* ── Small search lines inside — the 'looking' detail ─────── */}
      <path
        d="M24 22 C26 20 29 19 32 19"
        stroke="#9A3F4A"
        strokeWidth="0.75"
        strokeLinecap="round"
        opacity="0.35"
      />
      <path
        d="M22 26 C25 24 29 23 33 23"
        stroke="#9A3F4A"
        strokeWidth="0.75"
        strokeLinecap="round"
        opacity="0.25"
      />

      {/* ── Handle — from bottom heart tip, angled down-right ────── */}
      {/* Handle shaft */}
      <path
        d="M35 44 L54 63"
        stroke="#6B4E6B"
        strokeWidth="4.5"
        strokeLinecap="round"
        opacity="0.85"
      />
      {/* Handle highlight */}
      <path
        d="M34 45 L52 62"
        stroke="#FDF8F0"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.25"
      />
      {/* Handle end cap */}
      <circle cx="54" cy="63" r="2.5" fill="#6B4E6B" opacity="0.7" />

      {/* ── Tiny botanical flourish on handle ─────────────────────── */}
      <path
        d="M42 52 C39 50 37 47 38 45"
        stroke="#9A3F4A"
        strokeWidth="0.75"
        strokeLinecap="round"
        opacity="0.4"
        fill="none"
      />
      <path
        d="M38 45 C37 43 38 41 40 42"
        stroke="#9A3F4A"
        strokeWidth="0.75"
        strokeLinecap="round"
        opacity="0.35"
        fill="none"
      />

      {/* ── Outer hand-drawn ring (slightly imperfect) ────────────── */}
      <path
        d="M32 48
           C19 37 6 29 6 18
           C6 8 13 3 20 3
           C26 3 30 7 32 11
           C34 7 38 3 44 3
           C51 3 58 8 58 18
           C58 29 45 37 32 48Z"
        stroke="#9A3F4A"
        strokeWidth="0.6"
        strokeDasharray="2 3"
        fill="none"
        opacity="0.3"
      />
    </svg>
  );
}
