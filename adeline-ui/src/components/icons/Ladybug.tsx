interface LadybugProps {
  size?: number;
  className?: string;
}

export default function Ladybug({ size = 64, className = "" }: LadybugProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* ── Shell shadow (depth) ────────────────────────────────── */}
      <ellipse cx="33" cy="40" rx="18" ry="15" fill="#3D1419" opacity="0.12" />

      {/* ── Wing cases (elytra) ────────────────────────────────── */}
      {/* Left wing */}
      <path
        d="M32 26
           C26 26 16 30 15 38
           C14 46 20 52 28 53
           C30 53 32 52 32 52 Z"
        fill="#9A3F4A"
        stroke="#3D1419"
        strokeWidth="1.25"
        strokeLinejoin="round"
      />
      {/* Right wing */}
      <path
        d="M32 26
           C38 26 48 30 49 38
           C50 46 44 52 36 53
           C34 53 32 52 32 52 Z"
        fill="#9A3F4A"
        stroke="#3D1419"
        strokeWidth="1.25"
        strokeLinejoin="round"
      />

      {/* ── Center dividing line (scutellum seam) ──────────────── */}
      <path d="M32 26 C32 35 32 44 32 52"
        stroke="#3D1419" strokeWidth="1.25" strokeLinecap="round" opacity="0.8" />

      {/* ── Spots — 3 per side ──────────────────────────────────── */}
      {/* Left side */}
      <circle cx="24" cy="32" r="3.2" fill="#3D1419" opacity="0.85" />
      <circle cx="22" cy="41" r="2.8" fill="#3D1419" opacity="0.85" />
      <circle cx="26" cy="49" r="2.4" fill="#3D1419" opacity="0.8" />

      {/* Right side */}
      <circle cx="40" cy="32" r="3.2" fill="#3D1419" opacity="0.85" />
      <circle cx="42" cy="41" r="2.8" fill="#3D1419" opacity="0.85" />
      <circle cx="38" cy="49" r="2.4" fill="#3D1419" opacity="0.8" />

      {/* ── Pronotum (shoulder plate) — white with black spots ──── */}
      <path
        d="M25 27 C26 22 38 22 39 27 C38 29 35 30 32 30 C29 30 26 29 25 27Z"
        fill="#FDF8F0"
        stroke="#3D1419"
        strokeWidth="1"
      />
      {/* Pronotum spots */}
      <circle cx="29" cy="26" r="1.8" fill="#3D1419" opacity="0.75" />
      <circle cx="35" cy="26" r="1.8" fill="#3D1419" opacity="0.75" />

      {/* ── Head ────────────────────────────────────────────────── */}
      <ellipse cx="32" cy="21" rx="6.5" ry="5.5" fill="#3D1419" />

      {/* Eyes — two small white circles */}
      <circle cx="29" cy="19.5" r="1.8" fill="#FDF8F0" opacity="0.9" />
      <circle cx="35" cy="19.5" r="1.8" fill="#FDF8F0" opacity="0.9" />
      <circle cx="29.5" cy="19.5" r="0.7" fill="#3D1419" />
      <circle cx="35.5" cy="19.5" r="0.7" fill="#3D1419" />
      {/* Eye shine */}
      <circle cx="29" cy="19" r="0.4" fill="#FDF8F0" opacity="0.9" />
      <circle cx="35" cy="19" r="0.4" fill="#FDF8F0" opacity="0.9" />

      {/* ── Antennae ────────────────────────────────────────────── */}
      <path d="M28 16 C26 12 23 9 21 7"
        stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
      <circle cx="21" cy="7" r="1.2" fill="#3D1419" />

      <path d="M36 16 C38 12 41 9 43 7"
        stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
      <circle cx="43" cy="7" r="1.2" fill="#3D1419" />

      {/* ── Tiny legs (3 per side) ──────────────────────────────── */}
      <path d="M19 34 C16 33 13 32 11 31" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.55" />
      <path d="M17 40 C14 40 11 41 10 42" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.55" />
      <path d="M19 47 C16 48 13 50 12 52" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.5" />

      <path d="M45 34 C48 33 51 32 53 31" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.55" />
      <path d="M47 40 C50 40 53 41 54 42" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.55" />
      <path d="M45 47 C48 48 51 50 52 52" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.5" />

      {/* ── Highlight on shell (hand-pressed sheen) ─────────────── */}
      <path d="M22 31 C23 28 28 27 30 28"
        stroke="#FDF8F0" strokeWidth="1.2" strokeLinecap="round" opacity="0.3" />
    </svg>
  );
}
