interface BeeProps {
  size?: number;
  className?: string;
  /** Tilt the bee like it's in flight */
  tilt?: number;
}

export default function Bee({ size = 64, className = "", tilt = -15 }: BeeProps) {
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
      {/* ── Wings (above body, translucent) ────────────────────── */}

      {/* Upper-left wing */}
      <path
        d="M34 26 C30 20 20 16 14 18 C12 19 12 22 16 24 C22 27 30 27 34 28Z"
        fill="#FDF8F0"
        opacity="0.75"
        stroke="#BD6809"
        strokeWidth="0.75"
      />
      {/* Wing veins — left */}
      <path d="M34 27 C26 24 18 20 14 18" stroke="#BD6809" strokeWidth="0.4" opacity="0.4" strokeLinecap="round" />
      <path d="M33 28 C27 27 20 25 16 24" stroke="#BD6809" strokeWidth="0.3" opacity="0.3" strokeLinecap="round" />

      {/* Upper-right wing */}
      <path
        d="M46 26 C50 20 60 16 66 18 C68 19 68 22 64 24 C58 27 50 27 46 28Z"
        fill="#FDF8F0"
        opacity="0.75"
        stroke="#BD6809"
        strokeWidth="0.75"
      />
      {/* Wing veins — right */}
      <path d="M46 27 C54 24 62 20 66 18" stroke="#BD6809" strokeWidth="0.4" opacity="0.4" strokeLinecap="round" />
      <path d="M47 28 C53 27 60 25 64 24" stroke="#BD6809" strokeWidth="0.3" opacity="0.3" strokeLinecap="round" />

      {/* Lower-left wing (smaller) */}
      <path
        d="M34 30 C28 28 20 28 17 30 C19 33 26 33 34 32Z"
        fill="#FDF8F0"
        opacity="0.55"
        stroke="#BD6809"
        strokeWidth="0.6"
      />

      {/* Lower-right wing (smaller) */}
      <path
        d="M46 30 C52 28 60 28 63 30 C61 33 54 33 46 32Z"
        fill="#FDF8F0"
        opacity="0.55"
        stroke="#BD6809"
        strokeWidth="0.6"
      />

      {/* ── Body ───────────────────────────────────────────────── */}
      {/* Main abdomen — rounded oval */}
      <ellipse cx="40" cy="38" rx="13" ry="9" fill="#BD6809" stroke="#3D1419" strokeWidth="1" />

      {/* Stripes */}
      <path
        d="M28.5 34.5 C29 32 30 30.5 40 30.5 C50 30.5 51 32 51.5 34.5
           C51 36 50 37 40 37 C30 37 29 36 28.5 34.5Z"
        fill="#3D1419"
        opacity="0.8"
      />
      <path
        d="M27.5 39 C28 37 29 36.5 40 36.5 C51 36.5 52 37 52.5 39
           C52 41 51 42 40 42 C29 42 28 41 27.5 39Z"
        fill="#3D1419"
        opacity="0.75"
      />
      <path
        d="M29 44 C30 42.5 31 42 40 42 C49 42 50 42.5 51 44
           C50 45.5 48 46.5 40 46.5 C32 46.5 30 45.5 29 44Z"
        fill="#3D1419"
        opacity="0.65"
      />

      {/* Stinger */}
      <path d="M27.5 38 C24 38 20 38.5 17 40"
        stroke="#3D1419" strokeWidth="1.25" strokeLinecap="round" />

      {/* ── Head ───────────────────────────────────────────────── */}
      <ellipse cx="52" cy="35" rx="6" ry="5.5" fill="#3D1419" />
      {/* Eyes */}
      <ellipse cx="54" cy="33" rx="1.5" ry="1.5" fill="#BD6809" opacity="0.8" />
      <ellipse cx="54" cy="33" rx="0.6" ry="0.6" fill="#FDF8F0" opacity="0.9" />

      {/* ── Antennae ───────────────────────────────────────────── */}
      <path d="M54 30 C56 26 58 22 60 20"
        stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
      <circle cx="60" cy="20" r="1.5" fill="#BD6809" />

      <path d="M56 31 C59 28 62 25 64 23"
        stroke="#3D1419" strokeWidth="0.85" strokeLinecap="round" />
      <circle cx="64" cy="23" r="1.5" fill="#BD6809" />

      {/* ── Legs (3 pairs, small) ───────────────────────────────── */}
      <path d="M36 46 C34 49 32 51 30 53" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.6" />
      <path d="M40 47 C40 50 40 52 39 54" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.6" />
      <path d="M44 46 C46 49 48 51 50 52" stroke="#3D1419" strokeWidth="0.7" strokeLinecap="round" opacity="0.6" />
      {/* Upper legs */}
      <path d="M36 33 C34 30 31 28 29 27" stroke="#3D1419" strokeWidth="0.6" strokeLinecap="round" opacity="0.4" />
      <path d="M44 33 C46 30 49 28 51 27" stroke="#3D1419" strokeWidth="0.6" strokeLinecap="round" opacity="0.4" />

      {/* ── Pollen basket (corbicula) — small yellow blob on leg ── */}
      <ellipse cx="30" cy="44" rx="2" ry="1.2" fill="#BD6809" opacity="0.5"
        transform="rotate(-30 30 44)" />
    </svg>
  );
}
