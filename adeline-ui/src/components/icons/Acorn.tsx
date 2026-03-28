/**
 * Acorn — botanical field-note acorn with oak leaves.
 * Use for: lesson seeds, growth milestones, "this is just the beginning" moments,
 * or as a Track badge icon for Creation Science / Homesteading.
 */

interface AcornProps {
  size?: number;
  className?: string;
}

export default function Acorn({ size = 64, className = "" }: AcornProps) {
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
      {/* ── Oak leaf — left ───────────────────────────────────────── */}
      <path
        d="M20 28
           C17 24 14 20 16 16
           C17 13 20 13 22 15
           C21 12 22 9 25 10
           C27 11 27 14 26 16
           C29 13 32 13 33 16
           C34 19 31 22 28 24
           C26 26 23 27 20 28Z"
        fill="#9A3F4A"
        opacity="0.2"
        stroke="#9A3F4A"
        strokeWidth="1"
        strokeLinejoin="round"
      />
      {/* Leaf veins — left */}
      <path d="M20 28 C22 23 25 18 27 14" stroke="#9A3F4A" strokeWidth="0.6" opacity="0.5" strokeLinecap="round" />
      <path d="M22 24 C19 22 16 20 15 18" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.35" strokeLinecap="round" />
      <path d="M24 21 C22 19 21 16 21 14" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.35" strokeLinecap="round" />
      <path d="M26 18 C24 16 23 14 24 12" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.3" strokeLinecap="round" />

      {/* ── Oak leaf — right ──────────────────────────────────────── */}
      <path
        d="M44 28
           C47 24 50 20 48 16
           C47 13 44 13 42 15
           C43 12 42 9 39 10
           C37 11 37 14 38 16
           C35 13 32 13 31 16
           C30 19 33 22 36 24
           C38 26 41 27 44 28Z"
        fill="#9A3F4A"
        opacity="0.18"
        stroke="#9A3F4A"
        strokeWidth="1"
        strokeLinejoin="round"
      />
      {/* Leaf veins — right */}
      <path d="M44 28 C42 23 39 18 37 14" stroke="#9A3F4A" strokeWidth="0.6" opacity="0.5" strokeLinecap="round" />
      <path d="M42 24 C45 22 48 20 49 18" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.35" strokeLinecap="round" />
      <path d="M40 21 C42 19 43 16 43 14" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.35" strokeLinecap="round" />
      <path d="M38 18 C40 16 41 14 40 12" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.3" strokeLinecap="round" />

      {/* ── Acorn cap (cupule) with crosshatch texture ────────────── */}
      <path
        d="M20 38 C20 32 24 28 32 28 C40 28 44 32 44 38 Z"
        fill="#BD6809"
        stroke="#3D1419"
        strokeWidth="1.1"
      />
      {/* Crosshatch on cap */}
      <path d="M21 33 C25 32 30 32 35 32 C38 32 41 33 43 34"
        stroke="#3D1419" strokeWidth="0.5" opacity="0.3" strokeLinecap="round" />
      <path d="M20 36 C24 35 29 35 34 35 C38 35 41 36 44 37"
        stroke="#3D1419" strokeWidth="0.5" opacity="0.3" strokeLinecap="round" />
      <path d="M23 30 C23 32 23 35 23 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />
      <path d="M27 29 C27 32 27 35 27 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />
      <path d="M32 28 C32 32 32 35 32 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />
      <path d="M37 29 C37 32 37 35 37 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />
      <path d="M41 30 C41 32 41 35 41 38" stroke="#3D1419" strokeWidth="0.4" opacity="0.25" strokeLinecap="round" />

      {/* ── Cap stem ─────────────────────────────────────────────── */}
      <path d="M32 28 C32 24 33 21 33 18"
        stroke="#3D1419" strokeWidth="1.1" strokeLinecap="round" />
      {/* Small curl at top of stem */}
      <path d="M33 18 C34 16 36 15 37 16 C38 17 37 19 35 19"
        stroke="#3D1419" strokeWidth="0.75" strokeLinecap="round" fill="none" />

      {/* ── Acorn body ───────────────────────────────────────────── */}
      <path
        d="M20 38 C20 50 24 60 32 62 C40 60 44 50 44 38 Z"
        fill="#BD6809"
        opacity="0.8"
        stroke="#3D1419"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
      {/* Body highlight */}
      <path d="M24 40 C23 46 23 52 25 58"
        stroke="#FDF8F0" strokeWidth="2" strokeLinecap="round" opacity="0.3" />

      {/* ── Acorn tip ────────────────────────────────────────────── */}
      <path d="M32 62 C31 64 31 67 32 68 C33 67 33 64 32 62Z"
        fill="#3D1419" opacity="0.6" />

      {/* ── Small acorn — companion, left ────────────────────────── */}
      <g transform="translate(8, 48) scale(0.5)">
        <path d="M0 16 C0 10 4 6 12 6 C20 6 24 10 24 16Z"
          fill="#BD6809" opacity="0.7" stroke="#3D1419" strokeWidth="1.1" />
        <path d="M0 16 C0 26 4 34 12 36 C20 34 24 26 24 16Z"
          fill="#BD6809" opacity="0.65" stroke="#3D1419" strokeWidth="1.1" />
        <path d="M12 6 C12 3 12 1 13 0" stroke="#3D1419" strokeWidth="1" strokeLinecap="round" />
      </g>

      {/* ── Tiny fallen leaf — ground right ──────────────────────── */}
      <path
        d="M44 65 C46 62 50 61 52 63 C50 65 47 66 44 65Z"
        fill="#9A3F4A"
        opacity="0.2"
        stroke="#9A3F4A"
        strokeWidth="0.6"
      />
      <path d="M44 65 C47 63 50 62 52 63" stroke="#9A3F4A" strokeWidth="0.4" opacity="0.35" strokeLinecap="round" />
    </svg>
  );
}
