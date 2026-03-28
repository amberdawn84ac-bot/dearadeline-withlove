interface ButterflyProps {
  size?: number;
  className?: string;
  /** Gentle sway angle in degrees */
  tilt?: number;
}

export default function Butterfly({ size = 64, className = "", tilt = 0 }: ButterflyProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 80 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={tilt ? { transform: `rotate(${tilt}deg)` } : undefined}
      aria-hidden="true"
    >
      {/* ── Upper-left wing ────────────────────────────────────── */}
      <path
        d="M38 32
           C34 26 24 18 14 16
           C10 15 7 17 8 22
           C9 28 18 32 28 34
           C33 35 37 34 38 32Z"
        fill="#BD6809"
        opacity="0.85"
        stroke="#3D1419"
        strokeWidth="0.75"
      />
      {/* Wing vein lines — upper left */}
      <path d="M38 32 C30 27 20 20 12 18" stroke="#3D1419" strokeWidth="0.5" opacity="0.4" strokeLinecap="round" />
      <path d="M36 30 C30 30 22 28 16 24" stroke="#3D1419" strokeWidth="0.4" opacity="0.3" strokeLinecap="round" />
      <path d="M37 31 C34 36 28 40 22 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />
      {/* Wing spot — upper left */}
      <circle cx="20" cy="22" r="3.5" fill="#9A3F4A" opacity="0.5" />
      <circle cx="20" cy="22" r="1.5" fill="#FDF8F0" opacity="0.6" />

      {/* ── Upper-right wing ───────────────────────────────────── */}
      <path
        d="M42 32
           C46 26 56 18 66 16
           C70 15 73 17 72 22
           C71 28 62 32 52 34
           C47 35 43 34 42 32Z"
        fill="#BD6809"
        opacity="0.85"
        stroke="#3D1419"
        strokeWidth="0.75"
      />
      {/* Wing vein lines — upper right */}
      <path d="M42 32 C50 27 60 20 68 18" stroke="#3D1419" strokeWidth="0.5" opacity="0.4" strokeLinecap="round" />
      <path d="M44 30 C50 30 58 28 64 24" stroke="#3D1419" strokeWidth="0.4" opacity="0.3" strokeLinecap="round" />
      <path d="M43 31 C46 36 52 40 58 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />
      {/* Wing spot — upper right */}
      <circle cx="60" cy="22" r="3.5" fill="#9A3F4A" opacity="0.5" />
      <circle cx="60" cy="22" r="1.5" fill="#FDF8F0" opacity="0.6" />

      {/* ── Lower-left wing ────────────────────────────────────── */}
      <path
        d="M38 34
           C32 36 22 40 16 46
           C12 50 14 56 20 55
           C28 54 36 46 39 38
           C40 36 39 34 38 34Z"
        fill="#9A3F4A"
        opacity="0.7"
        stroke="#3D1419"
        strokeWidth="0.75"
      />
      {/* Hind wing spot — lower left */}
      <circle cx="22" cy="49" r="2.5" fill="#BD6809" opacity="0.5" />

      {/* ── Lower-right wing ───────────────────────────────────── */}
      <path
        d="M42 34
           C48 36 58 40 64 46
           C68 50 66 56 60 55
           C52 54 44 46 41 38
           C40 36 41 34 42 34Z"
        fill="#9A3F4A"
        opacity="0.7"
        stroke="#3D1419"
        strokeWidth="0.75"
      />
      {/* Hind wing spot — lower right */}
      <circle cx="58" cy="49" r="2.5" fill="#BD6809" opacity="0.5" />

      {/* ── Body ───────────────────────────────────────────────── */}
      <path
        d="M40 20 C39 24 38.5 30 39 36 C39.5 42 40 46 40 50 C40 46 40.5 42 41 36 C41.5 30 41 24 40 20Z"
        fill="#3D1419"
        opacity="0.9"
      />
      {/* Body segments */}
      <ellipse cx="40" cy="23" rx="2" ry="2.5" fill="#3D1419" />
      <path d="M38.5 28 Q40 29 41.5 28" stroke="#3D1419" strokeWidth="0.5" opacity="0.6" />
      <path d="M38.5 33 Q40 34 41.5 33" stroke="#3D1419" strokeWidth="0.5" opacity="0.6" />
      <path d="M38.8 38 Q40 39 41.2 38" stroke="#3D1419" strokeWidth="0.5" opacity="0.4" />

      {/* ── Antennae ───────────────────────────────────────────── */}
      {/* Left antenna */}
      <path d="M39.5 21 C37 17 32 13 30 10"
        stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" opacity="0.85" />
      <circle cx="30" cy="10" r="1.5" fill="#9A3F4A" />

      {/* Right antenna */}
      <path d="M40.5 21 C43 17 48 13 50 10"
        stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" opacity="0.85" />
      <circle cx="50" cy="10" r="1.5" fill="#9A3F4A" />
    </svg>
  );
}
