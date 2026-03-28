interface WildflowerProps {
  size?: number;
  className?: string;
  /** Rotate the whole flower for variety */
  rotate?: number;
}

export default function Wildflower({ size = 64, className = "", rotate = 0 }: WildflowerProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={rotate ? { transform: `rotate(${rotate}deg)` } : undefined}
      aria-hidden="true"
    >
      {/* ── Petals (8, hand-irregular) ─────────────────────────── */}

      {/* Top */}
      <path d="M32 22 C30 17 29 12 32 8 C35 12 34 17 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Top-right */}
      <path d="M32 22 C36 18 40 15 44 13 C43 18 40 21 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Right */}
      <path d="M32 22 C37 22 42 20 46 22 C42 25 37 24 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Bottom-right */}
      <path d="M32 22 C36 26 40 29 42 33 C37 33 34 29 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Bottom */}
      <path d="M32 22 C30 27 31 32 32 36 C33 32 34 27 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Bottom-left */}
      <path d="M32 22 C28 26 24 29 22 33 C26 33 30 29 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Left */}
      <path d="M32 22 C27 22 22 20 18 22 C22 25 27 24 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* Top-left */}
      <path d="M32 22 C28 18 24 15 20 13 C21 18 24 21 32 22Z"
        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="1" strokeLinejoin="round" />

      {/* ── Flower center ──────────────────────────────────────── */}
      <circle cx="32" cy="22" r="6.5" fill="#9A3F4A" />
      <circle cx="32" cy="22" r="4"   fill="#BD6809" opacity="0.7" />
      {/* Pollen dots */}
      <circle cx="31" cy="21" r="0.8" fill="#FDF8F0" opacity="0.8" />
      <circle cx="33" cy="21" r="0.8" fill="#FDF8F0" opacity="0.8" />
      <circle cx="32" cy="23" r="0.8" fill="#FDF8F0" opacity="0.8" />

      {/* ── Stem ───────────────────────────────────────────────── */}
      <path d="M32 36 C31 44 33 52 32 64"
        stroke="#3D1419" strokeWidth="1.25" strokeLinecap="round" opacity="0.75" />

      {/* ── Left leaf ──────────────────────────────────────────── */}
      <path d="M31 50 C26 46 20 44 18 42 C21 46 26 50 31 50Z"
        fill="#9A3F4A" opacity="0.25" stroke="#9A3F4A" strokeWidth="0.75" />
      {/* Leaf midrib */}
      <path d="M31 50 C26 47 21 44 18 42"
        stroke="#9A3F4A" strokeWidth="0.5" opacity="0.5" strokeLinecap="round" />

      {/* ── Right leaf ─────────────────────────────────────────── */}
      <path d="M33 43 C38 40 44 39 46 38 C43 42 38 44 33 43Z"
        fill="#9A3F4A" opacity="0.2" stroke="#9A3F4A" strokeWidth="0.75" />
      <path d="M33 43 C38 41 43 39 46 38"
        stroke="#9A3F4A" strokeWidth="0.5" opacity="0.4" strokeLinecap="round" />

      {/* ── Small grass blades at base ─────────────────────────── */}
      <path d="M29 72 C28 68 27 65 26 62"
        stroke="#3D1419" strokeWidth="0.75" strokeLinecap="round" opacity="0.4" />
      <path d="M34 72 C35 67 36 64 37 61"
        stroke="#3D1419" strokeWidth="0.75" strokeLinecap="round" opacity="0.3" />
    </svg>
  );
}
