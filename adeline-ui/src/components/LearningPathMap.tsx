"use client";

import { useEffect, useRef, useState } from "react";
import type { LearningPathNode, LearningPathResponse, Track } from "@/lib/brain-client";
import { fetchLearningPath } from "@/lib/brain-client";

// ── Track display labels ──────────────────────────────────────────────────────

const TRACK_LABELS: Record<string, string> = {
  TRUTH_HISTORY:        "Truth & History",
  CREATION_SCIENCE:     "Creation Science",
  HOMESTEADING:         "Homesteading",
  GOVERNMENT_ECONOMICS: "Government & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Changemaking",
  DISCIPLESHIP:         "Discipleship",
  HEALTH_NATUROPATHY:   "Health & Naturopathy",
  ENGLISH_LITERATURE:   "English Literature",
  APPLIED_MATHEMATICS:  "Applied Mathematics",
  CREATIVE_ECONOMY:     "Creative Economy",
};

const STATE_STYLES: Record<LearningPathNode["state"], string> = {
  mastered:  "bg-[#2F4731] border-[#5C7A2F] text-white",
  available: "bg-[#BD6809] border-[#BD6809] text-white",
  locked:    "bg-white border-[#3D1419]/20 text-[#3D1419]/40",
};

const STATE_ICON: Record<LearningPathNode["state"], string> = {
  mastered:  "✓",
  available: "▶",
  locked:    "🔒",
};

// ── Node card ─────────────────────────────────────────────────────────────────

function NodeCard({
  node,
  onClick,
  selected,
}: {
  node: LearningPathNode;
  onClick: () => void;
  selected: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        relative rounded-xl border-2 p-3 text-left transition-all duration-200 w-[160px] shrink-0
        ${STATE_STYLES[node.state]}
        ${selected ? "ring-2 ring-offset-2 ring-[#BD6809]" : ""}
        ${node.state === "locked" ? "cursor-not-allowed opacity-60" : "hover:scale-105 cursor-pointer"}
      `}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-xs">{STATE_ICON[node.state]}</span>
        {node.mastery_score !== null && (
          <span className="text-xs opacity-80 ml-auto font-mono">
            {Math.round(node.mastery_score * 100)}%
          </span>
        )}
      </div>
      <p className="font-kalam text-sm font-semibold leading-tight line-clamp-2">
        {node.title}
      </p>
      {node.grade_band && (
        <span className="mt-1.5 inline-block font-mono text-[10px] opacity-70 uppercase tracking-wide">
          {node.grade_band}
        </span>
      )}
    </button>
  );
}

// ── Detail panel ──────────────────────────────────────────────────────────────

function NodeDetail({
  node,
  allNodes,
  onClose,
}: {
  node: LearningPathNode;
  allNodes: LearningPathNode[];
  onClose: () => void;
}) {
  const prereqs = allNodes.filter((n) => node.prerequisite_ids.includes(n.id));

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="bg-[#FFFEF7] rounded-2xl border border-[#BD6809]/30 shadow-xl w-full max-w-md p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#3D1419]/40 hover:text-[#3D1419] text-xl"
          aria-label="Close"
        >
          ✕
        </button>

        <div className="flex items-center gap-2 mb-3">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: node.track_color }}
          />
          <span className="font-mono text-xs uppercase tracking-widest text-[#3D1419]/60">
            {TRACK_LABELS[node.track] ?? node.track}
          </span>
        </div>

        <h3 className="font-kranky text-2xl text-[#3D1419] mb-1">{node.title}</h3>

        <div className="flex gap-2 flex-wrap mb-3">
          <span
            className={`text-xs font-mono uppercase px-2 py-0.5 rounded-full border ${
              node.state === "mastered"
                ? "bg-[#2F4731] text-white border-transparent"
                : node.state === "available"
                ? "bg-[#BD6809] text-white border-transparent"
                : "bg-white text-[#3D1419]/50 border-[#3D1419]/20"
            }`}
          >
            {node.state}
          </span>
          {node.grade_band && (
            <span className="text-xs font-mono uppercase px-2 py-0.5 rounded-full bg-[#3D1419]/10 text-[#3D1419]/70">
              {node.grade_band}
            </span>
          )}
          {node.difficulty && (
            <span className="text-xs font-mono uppercase px-2 py-0.5 rounded-full bg-[#BD6809]/10 text-[#BD6809]">
              {node.difficulty}
            </span>
          )}
        </div>

        {node.description && (
          <p className="font-kalam text-sm text-[#3D1419]/80 leading-relaxed mb-4">
            {node.description}
          </p>
        )}

        {node.mastery_score !== null && (
          <div className="mb-4">
            <div className="flex justify-between text-xs font-mono text-[#3D1419]/60 mb-1">
              <span>Mastery</span>
              <span>{Math.round(node.mastery_score * 100)}%</span>
            </div>
            <div className="h-2 bg-[#3D1419]/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#2F4731] rounded-full transition-all"
                style={{ width: `${Math.round(node.mastery_score * 100)}%` }}
              />
            </div>
          </div>
        )}

        {prereqs.length > 0 && (
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-[#3D1419]/50 mb-2">
              Prerequisites
            </p>
            <div className="flex flex-col gap-1">
              {prereqs.map((p) => (
                <div key={p.id} className="flex items-center gap-2">
                  <span className={`text-xs ${p.state === "mastered" ? "text-[#2F4731]" : "text-[#3D1419]/40"}`}>
                    {p.state === "mastered" ? "✓" : "○"}
                  </span>
                  <span className="font-kalam text-sm text-[#3D1419]/70">{p.title}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {node.standard_code && (
          <p className="mt-4 font-mono text-[10px] text-[#3D1419]/40 uppercase tracking-wide">
            Standard: {node.standard_code}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Track column ──────────────────────────────────────────────────────────────

function TrackColumn({
  trackName,
  nodes,
  onSelect,
  selectedId,
}: {
  trackName: string;
  nodes: LearningPathNode[];
  onSelect: (node: LearningPathNode) => void;
  selectedId: string | null;
}) {
  const color = nodes[0]?.track_color ?? "#3D1419";
  const mastered  = nodes.filter((n) => n.state === "mastered").length;
  const available = nodes.filter((n) => n.state === "available").length;

  return (
    <div className="flex flex-col gap-3 min-w-[180px]">
      {/* Track header */}
      <div
        className="rounded-xl px-3 py-2 text-white"
        style={{ backgroundColor: color }}
      >
        <p className="font-kranky text-sm leading-tight">{TRACK_LABELS[trackName] ?? trackName}</p>
        <p className="font-mono text-[10px] opacity-70 mt-0.5">
          {mastered} mastered · {available} ready
        </p>
      </div>

      {/* Concept nodes in this track */}
      <div className="flex flex-col gap-2 pl-2 border-l-2" style={{ borderColor: `${color}40` }}>
        {nodes.map((node) => (
          <NodeCard
            key={node.id}
            node={node}
            onClick={() => onSelect(node)}
            selected={node.id === selectedId}
          />
        ))}
      </div>
    </div>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressSummary({ data }: { data: LearningPathResponse }) {
  const total = data.nodes.length;
  const pct   = total > 0 ? Math.round((data.mastered_count / total) * 100) : 0;

  return (
    <div className="flex items-center gap-4 flex-wrap">
      <div className="flex-1 min-w-[200px]">
        <div className="flex justify-between text-xs font-mono text-[#3D1419]/60 mb-1">
          <span>Overall Progress</span>
          <span>{pct}% ({data.mastered_count}/{total})</span>
        </div>
        <div className="h-2.5 bg-[#3D1419]/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#2F4731] rounded-full transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <div className="flex gap-3 text-xs font-mono">
        <span className="text-[#2F4731]">✓ {data.mastered_count} mastered</span>
        <span className="text-[#BD6809]">▶ {data.available_count} ready</span>
        <span className="text-[#3D1419]/40">🔒 {data.locked_count} locked</span>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  studentId: string;
  filterTrack?: Track;
}

export default function LearningPathMap({ studentId, filterTrack }: Props) {
  const [data, setData]           = useState<LearningPathResponse | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [selected, setSelected]   = useState<LearningPathNode | null>(null);
  const [activeTrack, setActiveTrack] = useState<Track | undefined>(filterTrack);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchLearningPath(studentId, activeTrack)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [studentId, activeTrack]);

  // Group nodes by track
  const nodesByTrack = data
    ? data.nodes.reduce<Record<string, LearningPathNode[]>>((acc, node) => {
        (acc[node.track] ??= []).push(node);
        return acc;
      }, {})
    : {};

  // Sort nodes within each track: mastered first, then available, then locked
  const STATE_ORDER = { mastered: 0, available: 1, locked: 2 };
  for (const trackName in nodesByTrack) {
    nodesByTrack[trackName].sort(
      (a, b) => STATE_ORDER[a.state] - STATE_ORDER[b.state],
    );
  }

  return (
    <div className="rounded-2xl border border-[#BD6809]/30 bg-[#FFFEF7] overflow-hidden shadow">
      {/* Header */}
      <div className="bg-[#3D1419] px-6 py-4">
        <h2 className="font-kranky text-2xl text-[#FFFEF7]">Learning Path</h2>
        <p className="font-kalam text-sm text-[#BD6809] mt-0.5">
          Your curriculum concept map — see what you&apos;ve mastered and what&apos;s next.
        </p>
      </div>

      {/* Track filter pills */}
      <div className="px-6 py-3 border-b border-[#BD6809]/15 flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTrack(undefined)}
          className={`px-3 py-1 rounded-full text-xs font-mono transition-colors ${
            !activeTrack
              ? "bg-[#3D1419] text-white"
              : "bg-[#3D1419]/10 text-[#3D1419]/70 hover:bg-[#3D1419]/20"
          }`}
        >
          All Tracks
        </button>
        {Object.keys(TRACK_LABELS).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTrack(t as Track)}
            className={`px-3 py-1 rounded-full text-xs font-mono transition-colors ${
              activeTrack === t
                ? "bg-[#BD6809] text-white"
                : "bg-[#3D1419]/10 text-[#3D1419]/70 hover:bg-[#3D1419]/20"
            }`}
          >
            {TRACK_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Progress summary */}
      {data && (
        <div className="px-6 py-3 border-b border-[#BD6809]/10">
          <ProgressSummary data={data} />
        </div>
      )}

      {/* Content */}
      <div ref={scrollRef} className="overflow-x-auto px-6 py-5">
        {loading && (
          <div className="flex items-center justify-center py-16 text-[#3D1419]/40 font-kalam">
            Loading your learning map…
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center py-16 text-[#9A3F4A] font-kalam text-sm">
            {error.includes("Neo4j") || error.includes("unavailable")
              ? "Knowledge graph is warming up. Try again in a moment."
              : error}
          </div>
        )}

        {!loading && !error && data && data.nodes.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-[#3D1419]/50 font-kalam gap-2">
            <span className="text-4xl">🌱</span>
            <p>No concepts found yet — the curriculum is still being seeded.</p>
          </div>
        )}

        {!loading && !error && Object.keys(nodesByTrack).length > 0 && (
          <div className="flex gap-6">
            {Object.entries(nodesByTrack).map(([trackName, nodes]) => (
              <TrackColumn
                key={trackName}
                trackName={trackName}
                nodes={nodes}
                onSelect={setSelected}
                selectedId={selected?.id ?? null}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail panel overlay */}
      {selected && (
        <NodeDetail
          node={selected}
          allNodes={data?.nodes ?? []}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
