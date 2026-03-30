"use client";

/**
 * ExperimentCard.tsx — Compact experiment preview card for browsing/listing.
 *
 * Shows: title, chaos level, wow factor, concept badges, "Film This" hint,
 * and a "Start Experiment" CTA. Clicking reveals the Creation Connection.
 */
import { useState } from "react";
import type { Experiment } from "./LabGuide";

const CHAOS_CONFIG = {
  1: { label: "Sprout",    emoji: "🌱", color: "#6B7F5E", bg: "#F0FDF4" },
  2: { label: "Scout",     emoji: "🔭", color: "#BD6809", bg: "#FDF6E9" },
  3: { label: "Sovereign", emoji: "🔥", color: "#9A3F4A", bg: "#FEF2F2" },
} as const;

interface ExperimentCardProps {
  experiment: Experiment;
  onStart?: (experimentId: string) => void;
}

export function ExperimentCard({ experiment, onStart }: ExperimentCardProps) {
  const [showCreation, setShowCreation] = useState(false);
  const chaos = CHAOS_CONFIG[experiment.chaos_level];

  return (
    <div className="rounded-2xl border-2 overflow-hidden transition-all hover:scale-[1.01] hover:shadow-lg"
      style={{ borderColor: chaos.color + "60", background: "#FFFEF7" }}
    >
      {/* Header strip */}
      <div className="px-4 py-3 flex items-center gap-3" style={{ background: chaos.bg }}>
        <span className="text-2xl">{chaos.emoji}</span>
        <div className="flex-1 min-w-0">
          <h3
            className="text-lg font-bold text-[#2F4731] truncate"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            {experiment.title}
          </h3>
          <p className="text-[10px] font-black uppercase tracking-widest" style={{ color: chaos.color }}>
            Level {experiment.chaos_level}: {chaos.label}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-xs font-bold text-[#BD6809]">
            {"💥".repeat(Math.min(Math.ceil(experiment.wow_factor / 2), 5))}
          </p>
          <p className="text-[9px] text-[#2F4731]/40">{experiment.wow_factor}/10</p>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-3">
        <p className="text-xs text-[#2F4731]/70 leading-relaxed">{experiment.tagline}</p>

        {/* Concept badges */}
        <div className="flex flex-wrap gap-1">
          {experiment.scientific_concepts.slice(0, 3).map((c) => (
            <span
              key={c}
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider bg-[#2F4731] text-white"
            >
              {c}
            </span>
          ))}
          {experiment.scientific_concepts.length > 3 && (
            <span className="text-[9px] text-[#2F4731]/40">
              +{experiment.scientific_concepts.length - 3} more
            </span>
          )}
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-2 text-[10px] text-[#2F4731]/50">
          <span>⏱ {experiment.estimated_minutes} min</span>
          <span>·</span>
          <span>Gr {experiment.grade_band}</span>
          <span>·</span>
          <span>{experiment.materials.length} materials</span>
          <span>·</span>
          <span className="text-[#BD6809]">🎬 Film This</span>
        </div>

        {/* Creation Connection toggle */}
        <button
          onClick={(e) => { e.stopPropagation(); setShowCreation(!showCreation); }}
          className="text-[10px] font-bold text-[#9A3F4A] hover:underline"
        >
          ✝️ {showCreation ? "Hide" : "Show"} Creation Connection
        </button>

        {showCreation && (
          <div className="rounded-lg bg-[#FEF2F2] border border-[#9A3F4A]/10 p-3 space-y-1.5">
            <p className="text-xs font-bold text-[#9A3F4A]">{experiment.creation_connection.title}</p>
            {experiment.creation_connection.scripture && (
              <p className="text-[10px] italic text-[#9A3F4A]/60">{experiment.creation_connection.scripture}</p>
            )}
            <p className="text-xs text-[#2F4731]/70 leading-relaxed">
              {experiment.creation_connection.explanation}
            </p>
          </div>
        )}
      </div>

      {/* CTA */}
      <div className="px-4 pb-4">
        <button
          onClick={() => onStart?.(experiment.id)}
          className="w-full py-3 rounded-xl text-xs font-black uppercase tracking-widest text-white transition-all hover:brightness-110"
          style={{ background: chaos.color }}
        >
          {chaos.emoji} Start Experiment
        </button>
      </div>
    </div>
  );
}
