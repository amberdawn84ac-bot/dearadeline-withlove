interface Props {
  tier: 1 | 2 | 3;
}

const TIER_CONFIG = {
  1: { label: "Core Truth", bg: "#FEE2E2", text: "#991B1B", accent: "#DC2626" },
  2: { label: "Working Knowledge", bg: "#FEF3C7", text: "#92400E", accent: "#F59E0B" },
  3: { label: "Exposure", bg: "#F3F4F6", text: "#374151", accent: "#9CA3AF" },
} as const;

export function WeightTierBadge({ tier }: Props) {
  const config = TIER_CONFIG[tier];
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
      style={{ background: config.bg, color: config.text, borderLeft: `3px solid ${config.accent}` }}
    >
      {config.label}
    </span>
  );
}
