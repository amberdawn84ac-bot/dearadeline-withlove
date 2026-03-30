"use client";

import { useEffect, useState } from "react";
import { fetchStudentState, type StudentState } from "@/lib/brain-client";

// ── Static data ────────────────────────────────────────────────────────────────

const TRACK_SHORT: Record<string, string> = {
  TRUTH_HISTORY: "History", CREATION_SCIENCE: "Science", HOMESTEADING: "Homestead",
  GOVERNMENT_ECONOMICS: "Civics", JUSTICE_CHANGEMAKING: "Justice", DISCIPLESHIP: "Discipleship",
  HEALTH_NATUROPATHY: "Health", ENGLISH_LITERATURE: "Literature",
  APPLIED_MATHEMATICS: "Math", CREATIVE_ECONOMY: "Creative",
};

const TRACK_COLOR: Record<string, string> = {
  TRUTH_HISTORY: "#3D1419", CREATION_SCIENCE: "#2F4731", HOMESTEADING: "#5C7A2F",
  GOVERNMENT_ECONOMICS: "#BD6809", JUSTICE_CHANGEMAKING: "#9A3F4A", DISCIPLESHIP: "#4F46E5",
  HEALTH_NATUROPATHY: "#047857", ENGLISH_LITERATURE: "#7C3AED",
  APPLIED_MATHEMATICS: "#0369A1", CREATIVE_ECONOMY: "#B45309",
};

const TRACK_CONCEPTS: Record<string, string[]> = {
  TRUTH_HISTORY:        ["Primary Sources", "Dawes Act", "Reconstruction", "Trail of Tears", "Land Treaties"],
  CREATION_SCIENCE:     ["Cell Biology", "Soil pH", "Photosynthesis", "Taxonomy", "Ecosystems"],
  HOMESTEADING:         ["Seed Saving", "Composting", "Water Harvesting", "Fermentation", "Animal Care"],
  GOVERNMENT_ECONOMICS: ["Reg. Capture", "Supply & Demand", "Sound Money", "Federalism", "Tax Policy"],
  JUSTICE_CHANGEMAKING: ["Narrative Capture", "Civil Rights", "Organizing", "Lobbying Records", "Redress"],
  DISCIPLESHIP:         ["Biblical Worldview", "Virtue Ethics", "Sabbath Econ.", "Covenant", "Apologetics"],
  HEALTH_NATUROPATHY:   ["Herbal Medicine", "Nutrition", "Fasting", "Gut Health", "Minerals"],
  ENGLISH_LITERATURE:   ["Rhetoric", "Close Reading", "Argument Essay", "Poetry Forms", "Narrative Arc"],
  APPLIED_MATHEMATICS:  ["Fractions", "Geometry", "Budgeting", "Statistics", "Algebra"],
  CREATIVE_ECONOMY:     ["Product Costing", "Brand Story", "Market Research", "Portfolio", "Selling Craft"],
};

// ── Helpers ────────────────────────────────────────────────────────────────────

type Status = "mastered" | "in-progress" | "not-started";

const STATUS_COLOR: Record<Status, string> = {
  mastered: "#16A34A", "in-progress": "#D97706", "not-started": "#9CA3AF",
};

function status(score: number): Status {
  return score >= 0.8 ? "mastered" : score >= 0.2 ? "in-progress" : "not-started";
}

function trunc(s: string, n: number) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

// ── Layout ─────────────────────────────────────────────────────────────────────

const TR = 26, CR = 14, H_GAP = 110, PAD = 56, TRACK_Y = 70, CHILD_DY = 135, C_GAP = 44;

function trackCx(i: number) { return PAD + TR + i * H_GAP; }

function conceptPositions(trackIdx: number, count: number) {
  const cx = trackCx(trackIdx);
  const total = (count - 1) * C_GAP;
  return Array.from({ length: count }, (_, ci) => ({
    cx: cx - total / 2 + ci * C_GAP,
    cy: TRACK_Y + CHILD_DY,
  }));
}

// ── Component ──────────────────────────────────────────────────────────────────

export function KnowledgeTree({ studentId }: { studentId: string }) {
  const [state, setState]       = useState<StudentState | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetchStudentState(studentId)
      .then(setState)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return (
    <div className="rounded-2xl p-5 space-y-3 animate-pulse" style={{ background: "#FDFAF6", border: "1px solid #BD680920" }}>
      <div className="h-4 w-40 bg-gray-200 rounded" />
      <div className="h-36 bg-gray-100 rounded-xl" />
    </div>
  );

  if (error) return (
    <div className="rounded-2xl p-4 text-sm text-red-600" style={{ border: "1px solid #fee2e2" }}>
      Could not load mastery data: {error}
    </div>
  );

  if (!state) return null;

  const tracks = Object.entries(state.tracks).map(([key, data]) => ({
    key, score: data.mastery_score, status: status(data.mastery_score),
    short: TRACK_SHORT[key] ?? key, color: TRACK_COLOR[key] ?? "#6B7280",
    concepts: TRACK_CONCEPTS[key] ?? [],
  }));

  const n       = tracks.length;
  const svgW    = Math.max(600, n * H_GAP + PAD * 2);
  const svgH    = expanded ? 305 : 155;
  const expIdx  = expanded ? tracks.findIndex((t) => t.key === expanded) : -1;

  return (
    <div className="rounded-2xl p-5 space-y-4" style={{ background: "#FDFAF6", border: "1px solid #BD680920" }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-gray-800">Knowledge Tree</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-400">
          {tracks.filter((t) => t.status === "mastered").length}/{n} mastered
        </span>
      </div>

      {/* Mobile list (hidden md+) */}
      <div className="space-y-2 md:hidden">
        {tracks.map((t) => {
          const pct = Math.round(t.score * 100);
          return (
            <div key={t.key} className="rounded-xl px-4 py-3 flex items-center gap-3"
              style={{ background: "#fff", border: `1px solid ${t.color}25` }}>
              <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs font-bold"
                style={{ background: t.color }}>{pct}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-800 truncate">{t.short}</p>
                <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, background: STATUS_COLOR[t.status] }} />
                </div>
              </div>
              <span className="text-xs font-bold flex-shrink-0" style={{ color: STATUS_COLOR[t.status] }}>
                {t.status === "mastered" ? "Mastered" : t.status === "in-progress" ? "In Progress" : "Not Started"}
              </span>
            </div>
          );
        })}
      </div>

      {/* SVG tree (hidden on mobile) */}
      <div className="hidden md:block overflow-x-auto">
        <svg width={svgW} height={svgH} viewBox={`0 0 ${svgW} ${svgH}`} aria-label="Knowledge mastery tree">
          {/* Edges to concept children */}
          {expIdx >= 0 && conceptPositions(expIdx, tracks[expIdx].concepts.length).map((pos, ci) => (
            <line key={`e${ci}`} x1={trackCx(expIdx)} y1={TRACK_Y + TR}
              x2={pos.cx} y2={pos.cy - CR} stroke="#D1D5DB" strokeWidth={1.5} strokeDasharray="4 3" />
          ))}

          {/* Track nodes */}
          {tracks.map((t, i) => {
            const cx      = trackCx(i);
            const pct     = t.score;
            const r2      = TR - 4;
            const circ    = 2 * Math.PI * r2;
            const isExp   = expanded === t.key;
            const glow    = t.status === "mastered" ? "drop-shadow(0 0 6px #16A34A88)" : "none";
            return (
              <g key={t.key} onClick={() => setExpanded(isExp ? null : t.key)}
                className="cursor-pointer" role="button" aria-pressed={isExp}
                aria-label={`${t.short} — ${Math.round(pct * 100)}% mastered`}>
                <circle cx={cx} cy={TRACK_Y} r={TR} fill="#fff" stroke={t.color}
                  strokeWidth={isExp ? 2.5 : 1.5} style={{ filter: glow }} />
                {/* Progress fill arc */}
                <circle cx={cx} cy={TRACK_Y} r={r2} fill="none"
                  stroke={STATUS_COLOR[t.status]} strokeWidth={5}
                  strokeDasharray={`${circ * pct} ${circ}`}
                  strokeDashoffset={circ * 0.25} strokeLinecap="round"
                  transform={`rotate(-90 ${cx} ${TRACK_Y})`} opacity={0.85} />
                <text x={cx} y={TRACK_Y + 4} textAnchor="middle" fontSize={10} fontWeight="700" fill={t.color}>
                  {Math.round(pct * 100)}%
                </text>
                <text x={cx} y={TRACK_Y + TR + 14} textAnchor="middle" fontSize={9} fontWeight="600" fill="#374151">
                  {t.short}
                </text>
              </g>
            );
          })}

          {/* Concept child nodes */}
          {expIdx >= 0 && tracks[expIdx].concepts.map((concept, ci) => {
            const pos  = conceptPositions(expIdx, tracks[expIdx].concepts.length)[ci];
            const col  = tracks[expIdx].color;
            return (
              <g key={`c${ci}`}>
                <circle cx={pos.cx} cy={pos.cy} r={CR} fill="#fff" stroke={col} strokeWidth={1.5} />
                <text x={pos.cx} y={pos.cy + 3} textAnchor="middle" fontSize={7} fontWeight="600" fill={col}>
                  {trunc(concept, 10)}
                </text>
                <text x={pos.cx} y={pos.cy + CR + 11} textAnchor="middle" fontSize={7} fill="#6B7280">
                  {trunc(concept, 12)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <p className="hidden md:block text-[10px] text-gray-400 text-center">
        Click a track to expand its concepts
      </p>

      {/* Legend */}
      <div className="flex items-center gap-5 justify-center">
        {(["not-started", "in-progress", "mastered"] as Status[]).map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <svg width={10} height={10} viewBox="0 0 10 10">
              <circle cx={5} cy={5} r={4} fill={STATUS_COLOR[s]} opacity={s === "not-started" ? 0.5 : 1} />
            </svg>
            <span className="text-[10px] text-gray-500">
              {s === "not-started" ? "Not Started" : s === "in-progress" ? "In Progress" : "Mastered"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
