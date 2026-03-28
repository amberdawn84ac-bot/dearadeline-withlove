/**
 * MasonJar — wildflowers preserved in a field-note mason jar.
 * Used as the icon for the INVESTIGATING truth status:
 * sources found but not yet fully verified. Still gathering.
 */

interface MasonJarProps {
  size?: number;
  className?: string;
}

export default function MasonJar({ size = 64, className = "" }: MasonJarProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* ── Lid band (screw ring) ─────────────────────────────────── */}
      <rect x="18" y="8" width="28" height="7" rx="1.5"
        fill="#BD6809" opacity="0.85" stroke="#3D1419" strokeWidth="1" />
      {/* Lid threading lines */}
      <line x1="18" y1="10.5" x2="46" y2="10.5" stroke="#3D1419" strokeWidth="0.4" opacity="0.4" />
      <line x1="18" y1="12.5" x2="46" y2="12.5" stroke="#3D1419" strokeWidth="0.4" opacity="0.4" />

      {/* ── Lid top (flat cap) ───────────────────────────────────── */}
      <rect x="20" y="5" width="24" height="4" rx="1"
        fill="#9A3F4A" opacity="0.9" stroke="#3D1419" strokeWidth="0.85" />
      {/* Lid center button */}
      <ellipse cx="32" cy="7" rx="5" ry="1.5"
        fill="#9A3F4A" stroke="#3D1419" strokeWidth="0.5" opacity="0.7" />

      {/* ── Jar neck ────────────────────────────────────────────── */}
      <path d="M20 15 L18 20 L16 24 L16 66 L48 66 L48 24 L46 20 L44 15 Z"
        fill="#FDF8F0"
        opacity="0.6"
        stroke="#3D1419"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />

      {/* ── Glass highlight (left side) ──────────────────────────── */}
      <path d="M20 24 C19 30 18.5 44 19 60"
        stroke="#FDF8F0" strokeWidth="2.5" strokeLinecap="round" opacity="0.7" />

      {/* ── Glass highlight (right subtle) ───────────────────────── */}
      <path d="M43 26 C43.5 34 43.5 48 43 60"
        stroke="#FDF8F0" strokeWidth="1" strokeLinecap="round" opacity="0.35" />

      {/* ── Water line inside jar ────────────────────────────────── */}
      <path d="M17 52 C22 50 28 53 32 51 C36 50 42 53 47 51"
        stroke="#9A3F4A" strokeWidth="0.75" opacity="0.25" strokeLinecap="round" />

      {/* ══ FLOWERS INSIDE ══════════════════════════════════════════ */}

      {/* Stem 1 — left, tall */}
      <path d="M26 65 C25 55 24 44 25 28"
        stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
      {/* Leaf on stem 1 */}
      <path d="M25 46 C21 43 18 42 17 41 C19 44 22 46 25 46Z"
        fill="#9A3F4A" opacity="0.3" stroke="#9A3F4A" strokeWidth="0.6" />

      {/* Stem 2 — center, slightly bent */}
      <path d="M32 65 C32 55 33 44 31 28"
        stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.6" />

      {/* Stem 3 — right */}
      <path d="M38 65 C38 54 39 43 40 27"
        stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.55" />
      {/* Leaf on stem 3 */}
      <path d="M39 44 C43 41 46 40 47 40 C45 43 42 45 39 44Z"
        fill="#9A3F4A" opacity="0.25" stroke="#9A3F4A" strokeWidth="0.6" />

      {/* Stem 4 — thin wispy right-lean */}
      <path d="M35 65 C36 56 38 48 42 32"
        stroke="#3D1419" strokeWidth="0.75" strokeLinecap="round" opacity="0.4" />

      {/* ── Flower 1 (left stem) — daisy, Paradise ───────────────── */}
      <g transform="translate(25, 28)">
        <path d="M0 0 C-1 -4 -1 -7 0 -9 C1 -7 1 -4 0 0Z"   fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M0 0 C3 -2 6 -3 8 -3 C7 0 4 1 0 0Z"        fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M0 0 C4 0 6 1 8 3 C5 3 2 2 0 0Z"           fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M0 0 C2 3 2 6 1 8 C-1 6 -1 3 0 0Z"         fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M0 0 C-2 3 -2 6 -1 8 C-3 6 -3 3 0 0Z"      fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M0 0 C-4 0 -6 1 -8 3 C-5 3 -2 2 0 0Z"      fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M0 0 C-3 -2 -6 -3 -8 -3 C-7 0 -4 1 0 0Z"   fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <circle cx="0" cy="0" r="3.5" fill="#9A3F4A" />
        <circle cx="0" cy="0" r="2" fill="#BD6809" opacity="0.75" />
        <circle cx="-0.5" cy="-0.5" r="0.5" fill="#FDF8F0" opacity="0.7" />
      </g>

      {/* ── Flower 2 (center stem) — smaller, Papaya center ──────── */}
      <g transform="translate(31, 27)">
        <path d="M0 0 C-1 -3 0 -6 0 -8 C1 -6 1 -3 0 0Z"    fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.7" />
        <path d="M0 0 C3 -2 5 -2 7 -2 C6 1 3 1 0 0Z"       fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.7" />
        <path d="M0 0 C3 1 5 3 6 5 C3 4 1 3 0 0Z"          fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.7" />
        <path d="M0 0 C1 3 0 6 0 7 C-1 5 -1 3 0 0Z"        fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.7" />
        <path d="M0 0 C-3 1 -5 3 -6 5 C-3 4 -1 3 0 0Z"     fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.7" />
        <path d="M0 0 C-3 -2 -5 -2 -7 -2 C-6 1 -3 1 0 0Z"  fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.7" />
        <circle cx="0" cy="0" r="3" fill="#BD6809" />
        <circle cx="0" cy="0" r="1.5" fill="#9A3F4A" opacity="0.8" />
      </g>

      {/* ── Flower 3 (right stem) — bud, not fully open ──────────── */}
      <g transform="translate(40, 27)">
        {/* Bud petals, slightly closed */}
        <path d="M0 0 C-1 -2 -1 -5 0 -7 C1 -5 1 -2 0 0Z"   fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.7" opacity="0.9" />
        <path d="M0 0 C2 -1 4 -2 6 -2 C5 1 2 1 0 0Z"       fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.7" opacity="0.9" />
        <path d="M0 0 C2 1 4 3 5 5 C2 4 0 2 0 0Z"          fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.7" opacity="0.9" />
        <path d="M0 0 C-2 1 -4 3 -5 5 C-2 4 0 2 0 0Z"      fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.7" opacity="0.9" />
        <path d="M0 0 C-2 -1 -4 -2 -6 -2 C-5 1 -2 1 0 0Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.7" opacity="0.9" />
        <circle cx="0" cy="0" r="3" fill="#9A3F4A" />
        <circle cx="0" cy="0" r="1.5" fill="#BD6809" opacity="0.8" />
      </g>

      {/* ── Wispy flower 4 (leaning right) — tiny daisy bud ─────── */}
      <g transform="translate(42, 31)">
        <path d="M0 -5 C-1 -3 0 0 0 0 C1 -2 1 -4 0 -5Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.6" />
        <path d="M5 -2 C3 -1 0 0 0 0 C2 0 4 -1 5 -2Z"   fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.6" />
        <path d="M4 3 C2 1 0 0 0 0 C2 1 3 2 4 3Z"       fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.6" />
        <path d="M-4 3 C-2 1 0 0 0 0 C-2 1 -3 2 -4 3Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.6" />
        <path d="M-5 -2 C-3 -1 0 0 0 0 C-2 0 -4 -1 -5 -2Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.6" />
        <circle cx="0" cy="0" r="2.2" fill="#BD6809" opacity="0.9" />
      </g>

      {/* ── Jar base / bottom edge ───────────────────────────────── */}
      <path d="M16 63 L16 66 Q32 68 48 66 L48 63"
        stroke="#3D1419" strokeWidth="1" fill="none" opacity="0.5" />

      {/* ── Small label on jar ───────────────────────────────────── */}
      <rect x="21" y="54" width="22" height="8" rx="1"
        fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" opacity="0.8" />
      <line x1="23" y1="57" x2="41" y2="57" stroke="#BD6809" strokeWidth="0.5" opacity="0.5" />
      <line x1="23" y1="59" x2="38" y2="59" stroke="#BD6809" strokeWidth="0.5" opacity="0.35" />
    </svg>
  );
}
