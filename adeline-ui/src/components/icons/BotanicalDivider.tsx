/**
 * BotanicalDivider — a hand-pressed field note scene used between lesson sections.
 * Features: wildflowers, a butterfly, a bee, and a ladybug on a wavy stem line.
 */

interface BotanicalDividerProps {
  className?: string;
  width?: number | string;
}

export default function BotanicalDivider({ className = "", width = "100%" }: BotanicalDividerProps) {
  return (
    <svg
      width={width}
      height="72"
      viewBox="0 0 600 72"
      preserveAspectRatio="xMidYMid meet"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* ── Ground / stem line (wavy hand-drawn) ─────────────────── */}
      <path
        d="M0 50 C30 48 60 52 90 50 C120 48 150 52 180 50
           C210 48 240 52 270 50 C300 48 330 52 360 50
           C390 48 420 52 450 50 C480 48 510 52 540 50
           C560 49 580 51 600 50"
        stroke="#3D1419"
        strokeWidth="1"
        opacity="0.3"
      />

      {/* ══ LEFT CLUSTER ══════════════════════════════════════════════ */}

      {/* Wildflower 1 — tall, left */}
      <g transform="translate(30, 0)">
        {/* Stem */}
        <path d="M12 50 C11 40 13 30 12 18" stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
        {/* Leaf */}
        <path d="M12 38 C8 35 4 34 2 33 C5 36 9 38 12 38Z" fill="#9A3F4A" opacity="0.2" stroke="#9A3F4A" strokeWidth="0.6" />
        {/* Petals */}
        <path d="M12 18 C11 14 10 10 12 7 C14 10 13 14 12 18Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 18 C15 15 18 13 21 12 C19 16 16 18 12 18Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 18 C16 18 19 17 22 18 C19 20 16 20 12 18Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 18 C15 21 17 24 18 27 C15 25 13 22 12 18Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 18 C9 21 7 24 6 27 C8 25 11 22 12 18Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 18 C8 18 5 17 2 18 C5 20 8 20 12 18Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 18 C9 15 6 13 3 12 C5 16 8 18 12 18Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <circle cx="12" cy="18" r="4.5" fill="#9A3F4A" />
        <circle cx="12" cy="18" r="2.5" fill="#BD6809" opacity="0.7" />
      </g>

      {/* Wildflower 2 — shorter, beside first */}
      <g transform="translate(52, 8)">
        <path d="M8 42 C7 34 9 26 8 14" stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
        <path d="M8 14 C7 11 6 8 8 5 C10 8 9 11 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M8 14 C11 12 14 11 16 10 C14 13 11 14 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M8 14 C11 14 14 14 16 15 C14 17 11 16 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M8 14 C9 17 9 20 10 22 C8 20 7 17 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M8 14 C5 17 4 20 3 22 C5 20 7 17 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M8 14 C5 14 2 14 0 15 C2 17 5 16 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M8 14 C5 12 2 11 0 10 C2 13 5 14 8 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <circle cx="8" cy="14" r="3.5" fill="#BD6809" />
        <circle cx="8" cy="14" r="1.8" fill="#9A3F4A" opacity="0.8" />
      </g>

      {/* Ladybug — sitting on the stem line near left cluster */}
      <g transform="translate(80, 34) scale(0.45)">
        <ellipse cx="33" cy="40" rx="18" ry="15" fill="#3D1419" opacity="0.1" />
        <path d="M32 26 C26 26 16 30 15 38 C14 46 20 52 28 53 C30 53 32 52 32 52Z"
          fill="#9A3F4A" stroke="#3D1419" strokeWidth="1.25" />
        <path d="M32 26 C38 26 48 30 49 38 C50 46 44 52 36 53 C34 53 32 52 32 52Z"
          fill="#9A3F4A" stroke="#3D1419" strokeWidth="1.25" />
        <path d="M32 26 C32 35 32 44 32 52" stroke="#3D1419" strokeWidth="1.25" strokeLinecap="round" opacity="0.8" />
        <circle cx="24" cy="32" r="3" fill="#3D1419" opacity="0.8" />
        <circle cx="22" cy="41" r="2.5" fill="#3D1419" opacity="0.8" />
        <circle cx="40" cy="32" r="3" fill="#3D1419" opacity="0.8" />
        <circle cx="42" cy="41" r="2.5" fill="#3D1419" opacity="0.8" />
        <path d="M25 27 C26 22 38 22 39 27 C38 29 35 30 32 30 C29 30 26 29 25 27Z"
          fill="#FDF8F0" stroke="#3D1419" strokeWidth="1" />
        <circle cx="29" cy="26" r="1.8" fill="#3D1419" opacity="0.7" />
        <circle cx="35" cy="26" r="1.8" fill="#3D1419" opacity="0.7" />
        <ellipse cx="32" cy="21" rx="6.5" ry="5.5" fill="#3D1419" />
        <circle cx="29" cy="19.5" r="1.6" fill="#FDF8F0" opacity="0.9" />
        <circle cx="35" cy="19.5" r="1.6" fill="#FDF8F0" opacity="0.9" />
        <path d="M28 16 C26 12 23 9 21 7" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
        <circle cx="21" cy="7" r="1.2" fill="#3D1419" />
        <path d="M36 16 C38 12 41 9 43 7" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
        <circle cx="43" cy="7" r="1.2" fill="#3D1419" />
      </g>

      {/* ══ CENTER ════════════════════════════════════════════════════ */}

      {/* Butterfly — center, slightly above stem */}
      <g transform="translate(230, 4) scale(0.55)">
        <path d="M38 32 C34 26 24 18 14 16 C10 15 7 17 8 22 C9 28 18 32 28 34 C33 35 37 34 38 32Z"
          fill="#BD6809" opacity="0.8" stroke="#3D1419" strokeWidth="0.75" />
        <circle cx="20" cy="22" r="3.5" fill="#9A3F4A" opacity="0.5" />
        <circle cx="20" cy="22" r="1.5" fill="#FDF8F0" opacity="0.6" />
        <path d="M42 32 C46 26 56 18 66 16 C70 15 73 17 72 22 C71 28 62 32 52 34 C47 35 43 34 42 32Z"
          fill="#BD6809" opacity="0.8" stroke="#3D1419" strokeWidth="0.75" />
        <circle cx="60" cy="22" r="3.5" fill="#9A3F4A" opacity="0.5" />
        <circle cx="60" cy="22" r="1.5" fill="#FDF8F0" opacity="0.6" />
        <path d="M38 34 C32 36 22 40 16 46 C12 50 14 56 20 55 C28 54 36 46 39 38 C40 36 39 34 38 34Z"
          fill="#9A3F4A" opacity="0.65" stroke="#3D1419" strokeWidth="0.75" />
        <path d="M42 34 C48 36 58 40 64 46 C68 50 66 56 60 55 C52 54 44 46 41 38 C40 36 41 34 42 34Z"
          fill="#9A3F4A" opacity="0.65" stroke="#3D1419" strokeWidth="0.75" />
        <path d="M40 20 C39 24 38.5 30 39 36 C39.5 42 40 46 40 50 C40 46 40.5 42 41 36 C41.5 30 41 24 40 20Z"
          fill="#3D1419" opacity="0.9" />
        <ellipse cx="40" cy="23" rx="2" ry="2.5" fill="#3D1419" />
        <path d="M39.5 21 C37 17 32 13 30 10" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
        <circle cx="30" cy="10" r="1.5" fill="#9A3F4A" />
        <path d="M40.5 21 C43 17 48 13 50 10" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
        <circle cx="50" cy="10" r="1.5" fill="#9A3F4A" />
      </g>

      {/* Center wildflower cluster — 3 small blooms */}
      <g transform="translate(278, 12)">
        <path d="M6 38 C5 32 6 22 6 12" stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
        <path d="M6 12 C5 9 4 6 6 3 C8 6 7 9 6 12Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M6 12 C9 10 12 9 14 8 C12 11 9 12 6 12Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M6 12 C9 12 12 12 14 13 C12 15 9 14 6 12Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M6 12 C5 15 4 18 4 20 C6 18 7 15 6 12Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M6 12 C3 10 0 9 -2 8 C0 11 3 12 6 12Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <path d="M6 12 C3 12 0 12 -2 13 C0 15 3 14 6 12Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.75" />
        <circle cx="6" cy="12" r="3" fill="#9A3F4A" />
        <circle cx="6" cy="12" r="1.5" fill="#BD6809" opacity="0.8" />
      </g>

      {/* ══ RIGHT CLUSTER ══════════════════════════════════════════════ */}

      {/* Bee — in flight, right side */}
      <g transform="translate(390, 18) scale(0.48) rotate(-12)">
        <path d="M34 26 C30 20 20 16 14 18 C12 19 12 22 16 24 C22 27 30 27 34 28Z"
          fill="#FDF8F0" opacity="0.75" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M46 26 C50 20 60 16 66 18 C68 19 68 22 64 24 C58 27 50 27 46 28Z"
          fill="#FDF8F0" opacity="0.75" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M34 30 C28 28 20 28 17 30 C19 33 26 33 34 32Z"
          fill="#FDF8F0" opacity="0.5" stroke="#BD6809" strokeWidth="0.6" />
        <path d="M46 30 C52 28 60 28 63 30 C61 33 54 33 46 32Z"
          fill="#FDF8F0" opacity="0.5" stroke="#BD6809" strokeWidth="0.6" />
        <ellipse cx="40" cy="38" rx="13" ry="9" fill="#BD6809" stroke="#3D1419" strokeWidth="1" />
        <path d="M28.5 34.5 C29 32 30 30.5 40 30.5 C50 30.5 51 32 51.5 34.5 C51 36 50 37 40 37 C30 37 29 36 28.5 34.5Z"
          fill="#3D1419" opacity="0.8" />
        <path d="M27.5 39 C28 37 29 36.5 40 36.5 C51 36.5 52 37 52.5 39 C52 41 51 42 40 42 C29 42 28 41 27.5 39Z"
          fill="#3D1419" opacity="0.75" />
        <path d="M27.5 38 C24 38 20 38.5 17 40" stroke="#3D1419" strokeWidth="1.25" strokeLinecap="round" />
        <ellipse cx="52" cy="35" rx="6" ry="5.5" fill="#3D1419" />
        <path d="M54 30 C56 26 58 22 60 20" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
        <circle cx="60" cy="20" r="1.5" fill="#BD6809" />
        <path d="M56 31 C59 28 62 25 64 23" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
        <circle cx="64" cy="23" r="1.5" fill="#BD6809" />
      </g>

      {/* Wildflower 3 — right side tall */}
      <g transform="translate(465, 2)">
        <path d="M12 48 C11 38 13 28 12 14" stroke="#3D1419" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
        <path d="M12 32 C16 30 20 29 22 28 C19 31 15 33 12 32Z" fill="#9A3F4A" opacity="0.2" stroke="#9A3F4A" strokeWidth="0.6" />
        <path d="M12 14 C11 10 10 6 12 3 C14 6 13 10 12 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 14 C15 11 18 9 21 8 C19 12 16 14 12 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 14 C16 14 19 13 22 14 C19 16 16 16 12 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 14 C15 17 17 20 18 23 C15 21 13 18 12 14Z" fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 14 C9 17 7 20 6 23 C8 21 11 18 12 14Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 14 C8 14 5 13 2 14 C5 16 8 16 12 14Z"  fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <path d="M12 14 C9 11 6 9 3 8 C5 12 8 14 12 14Z"    fill="#FDF8F0" stroke="#9A3F4A" strokeWidth="0.85" />
        <circle cx="12" cy="14" r="5" fill="#9A3F4A" />
        <circle cx="12" cy="14" r="2.8" fill="#BD6809" opacity="0.7" />
        <circle cx="11" cy="13" r="0.7" fill="#FDF8F0" opacity="0.8" />
        <circle cx="13" cy="13" r="0.7" fill="#FDF8F0" opacity="0.8" />
        <circle cx="12" cy="15" r="0.7" fill="#FDF8F0" opacity="0.8" />
      </g>

      {/* Small wildflower 4 — far right short */}
      <g transform="translate(500, 22)">
        <path d="M8 28 C7 22 8 16 8 10" stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" opacity="0.45" />
        <path d="M8 10 C7 7 6 5 8 3 C10 5 9 7 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M8 10 C11 8 13 7 15 7 C13 9 11 10 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M8 10 C11 10 13 10 15 11 C13 13 11 12 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M8 10 C9 13 9 15 10 17 C8 15 7 13 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M8 10 C5 13 4 15 3 17 C5 15 7 13 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M8 10 C5 10 3 10 1 11 C3 13 5 12 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <path d="M8 10 C5 8 3 7 1 7 C3 9 5 10 8 10Z" fill="#FDF8F0" stroke="#BD6809" strokeWidth="0.75" />
        <circle cx="8" cy="10" r="3.5" fill="#BD6809" />
        <circle cx="8" cy="10" r="1.8" fill="#9A3F4A" opacity="0.7" />
      </g>

      {/* Tiny scattered dots — pollen/seeds floating */}
      <circle cx="110" cy="44" r="1" fill="#BD6809" opacity="0.3" />
      <circle cx="145" cy="40" r="0.8" fill="#9A3F4A" opacity="0.25" />
      <circle cx="200" cy="46" r="1.2" fill="#BD6809" opacity="0.2" />
      <circle cx="350" cy="42" r="1"   fill="#9A3F4A" opacity="0.3" />
      <circle cx="420" cy="45" r="0.8" fill="#BD6809" opacity="0.25" />
      <circle cx="560" cy="43" r="1"   fill="#9A3F4A" opacity="0.2" />
    </svg>
  );
}
