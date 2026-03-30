"use client";

/**
 * LabGuide.tsx — The "Sovereign Lab" recipe-card UI.
 *
 * Displays an experiment as a high-end step-by-step guide with:
 *   - Chaos Gauge (Sprout 🌱 / Scout 🔭 / Sovereign 🔥)
 *   - Materials checklist
 *   - Bold, readable steps (viewable from across the yard)
 *   - Safety callouts
 *   - "Film This" social media toolkit
 *   - "God's Creation" connection pop-up
 *   - "Upload Discovery" seal button
 */
import { useState } from "react";

// ── Types (mirror adeline-brain Experiment schema) ──────────────────────────

export interface ExperimentStep {
  step_number: number;
  instruction: string;
  tip?: string;
}

export interface SocialMediaKit {
  caption_template: string;
  filming_tips: string[];
  hashtags: string[];
}

export interface CreationConnection {
  title: string;
  scripture: string;
  explanation: string;
}

export interface Experiment {
  id: string;
  title: string;
  tagline: string;
  chaos_level: 1 | 2 | 3;
  wow_factor: number;
  scientific_concepts: string[];
  science_credits: string[];
  grade_band: string;
  materials: string[];
  safety_requirements: string[];
  steps: ExperimentStep[];
  creation_connection: CreationConnection;
  social_media_kit: SocialMediaKit;
  estimated_minutes: number;
}

// ── Chaos Gauge config ──────────────────────────────────────────────────────

const CHAOS = {
  1: { label: "Sprout",    emoji: "🌱", color: "#6B7F5E", bg: "#F0FDF4", desc: "Kitchen table; paper towels only" },
  2: { label: "Scout",     emoji: "🔭", color: "#BD6809", bg: "#FDF6E9", desc: "Driveway/backyard; wear old clothes" },
  3: { label: "Sovereign", emoji: "🔥", color: "#9A3F4A", bg: "#FEF2F2", desc: "Open field; fire extinguisher & Dad required" },
} as const;

// ── Component ───────────────────────────────────────────────────────────────

interface LabGuideProps {
  experiment: Experiment;
  onSeal?: (experimentId: string) => void;
  onMaterialsReady?: (experimentId: string) => void;
}

export function LabGuide({ experiment, onSeal, onMaterialsReady }: LabGuideProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [materialsChecked, setMaterialsChecked] = useState<Set<number>>(new Set());
  const [showCreation, setShowCreation] = useState(false);
  const [showFilmKit, setShowFilmKit] = useState(false);
  const [phase, setPhase] = useState<"materials" | "guide" | "done">("materials");

  const chaos = CHAOS[experiment.chaos_level];
  const allMaterialsReady = materialsChecked.size === experiment.materials.length;

  function toggleMaterial(idx: number) {
    setMaterialsChecked((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  }

  return (
    <div
      className="rounded-3xl border-2 overflow-hidden"
      style={{ borderColor: chaos.color, background: "#FFFEF7" }}
    >
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="p-6 flex items-start justify-between gap-4" style={{ background: chaos.bg }}>
        <div className="space-y-2">
          <h2
            className="text-3xl font-bold tracking-tight"
            style={{ fontFamily: "var(--font-emilys-candy), cursive", color: "#2F4731" }}
          >
            {experiment.title}
          </h2>
          <p className="text-sm text-[#2F4731]/60 max-w-md">{experiment.tagline}</p>

          {/* Concept badges */}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {experiment.scientific_concepts.map((c) => (
              <span
                key={c}
                className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
                style={{ background: "#2F4731", color: "#fff" }}
              >
                {c}
              </span>
            ))}
          </div>
        </div>

        {/* Chaos Gauge */}
        <div className="flex flex-col items-center gap-1 shrink-0">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl border-2"
            style={{ borderColor: chaos.color, background: "#fff" }}
          >
            {chaos.emoji}
          </div>
          <span className="text-xs font-black uppercase tracking-widest" style={{ color: chaos.color }}>
            {chaos.label}
          </span>
          <span className="text-[9px] text-[#2F4731]/40 text-center max-w-[100px]">{chaos.desc}</span>
        </div>
      </div>

      {/* ── Wow Factor + Time ────────────────────────────────────── */}
      <div className="px-6 py-3 border-b border-[#E7DAC3] flex items-center gap-4 text-xs">
        <span className="font-bold text-[#BD6809]">
          {"💥".repeat(Math.min(experiment.wow_factor, 5))} Wow: {experiment.wow_factor}/10
        </span>
        <span className="text-[#2F4731]/40">|</span>
        <span className="text-[#2F4731]/60">{experiment.estimated_minutes} min</span>
        <span className="text-[#2F4731]/40">|</span>
        <span className="text-[#2F4731]/60">Grades {experiment.grade_band}</span>
        {experiment.science_credits.map((c) => (
          <span
            key={c}
            className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#F0FDF4] text-[#166534] uppercase"
          >
            {c.replace(/_/g, " ")}
          </span>
        ))}
      </div>

      {/* ── Safety (always visible for Scout/Sovereign) ──────────── */}
      {experiment.safety_requirements.length > 0 && (
        <div className="px-6 py-3 border-b" style={{ borderColor: chaos.color + "40", background: chaos.bg }}>
          <p className="text-xs font-black uppercase tracking-wider mb-2" style={{ color: chaos.color }}>
            {chaos.emoji} Safety Requirements
          </p>
          <ul className="space-y-1">
            {experiment.safety_requirements.map((req, i) => (
              <li key={i} className="text-xs text-[#2F4731]/80 flex items-start gap-2">
                <span style={{ color: chaos.color }}>&#9888;</span>
                {req}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Phase: Materials Checklist ────────────────────────────── */}
      {phase === "materials" && (
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm font-bold text-[#2F4731]">Gather your materials:</p>
          <ul className="space-y-2">
            {experiment.materials.map((mat, i) => (
              <li key={i} className="flex items-center gap-3">
                <button
                  onClick={() => toggleMaterial(i)}
                  className="w-6 h-6 rounded-lg border-2 flex items-center justify-center text-xs transition-all shrink-0"
                  style={{
                    borderColor: materialsChecked.has(i) ? "#166534" : "#E7DAC3",
                    background:  materialsChecked.has(i) ? "#F0FDF4" : "#fff",
                    color:       materialsChecked.has(i) ? "#166534" : "#ccc",
                  }}
                >
                  {materialsChecked.has(i) ? "✓" : ""}
                </button>
                <span
                  className="text-sm"
                  style={{
                    color: materialsChecked.has(i) ? "#2F4731" : "#2F4731aa",
                    textDecoration: materialsChecked.has(i) ? "line-through" : "none",
                  }}
                >
                  {mat}
                </span>
              </li>
            ))}
          </ul>

          <button
            onClick={() => {
              setPhase("guide");
              onMaterialsReady?.(experiment.id);
            }}
            disabled={!allMaterialsReady}
            className="w-full py-4 rounded-2xl text-sm font-black uppercase tracking-widest transition-all disabled:opacity-30"
            style={{ background: chaos.color, color: "#fff" }}
          >
            {allMaterialsReady ? `${chaos.emoji} I Have Everything — Let's Go` : "Check off all materials first"}
          </button>
        </div>
      )}

      {/* ── Phase: Live Guide (Big Bold Steps) ───────────────────── */}
      {phase === "guide" && (
        <div className="px-6 py-5 space-y-5">
          {/* Step display — BIG so you can read from across the yard */}
          <div className="rounded-2xl border-2 border-[#E7DAC3] p-6 min-h-[180px] flex flex-col justify-center">
            <p className="text-xs font-black uppercase tracking-widest text-[#BD6809] mb-2">
              Step {experiment.steps[currentStep].step_number} of {experiment.steps.length}
            </p>
            <p
              className="text-2xl font-bold leading-relaxed text-[#2F4731]"
              style={{ fontFamily: "var(--font-kalam), cursive" }}
            >
              {experiment.steps[currentStep].instruction}
            </p>
            {experiment.steps[currentStep].tip && (
              <p className="text-sm text-[#BD6809] mt-3 italic">
                💡 {experiment.steps[currentStep].tip}
              </p>
            )}
          </div>

          {/* Step navigation */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
              disabled={currentStep === 0}
              className="px-4 py-2 rounded-xl border-2 border-[#E7DAC3] text-sm font-bold disabled:opacity-30"
            >
              ← Back
            </button>

            {/* Step dots */}
            <div className="flex gap-1.5 flex-1 justify-center">
              {experiment.steps.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentStep(i)}
                  className="w-3 h-3 rounded-full transition-all"
                  style={{
                    background: i === currentStep ? chaos.color : i < currentStep ? "#166534" : "#E7DAC3",
                  }}
                />
              ))}
            </div>

            {currentStep < experiment.steps.length - 1 ? (
              <button
                onClick={() => setCurrentStep((s) => s + 1)}
                className="px-4 py-2 rounded-xl text-sm font-bold text-white"
                style={{ background: chaos.color }}
              >
                Next →
              </button>
            ) : (
              <button
                onClick={() => setPhase("done")}
                className="px-4 py-2 rounded-xl text-sm font-black text-white uppercase tracking-wider"
                style={{ background: "#166534" }}
              >
                Done! ✓
              </button>
            )}
          </div>

          {/* Film This button */}
          <button
            onClick={() => setShowFilmKit(!showFilmKit)}
            className="w-full py-3 rounded-xl border-2 border-dashed text-sm font-bold flex items-center justify-center gap-2 transition-all hover:scale-[1.01]"
            style={{ borderColor: "#BD6809", color: "#BD6809" }}
          >
            🎬 Film This — Social Media Tips
          </button>

          {showFilmKit && (
            <div className="rounded-xl bg-[#FDF6E9] p-4 space-y-3 border border-[#BD6809]/20">
              <p className="text-xs font-black uppercase tracking-wider text-[#BD6809]">Social Media Toolkit</p>
              <div className="space-y-2">
                {experiment.social_media_kit.filming_tips.map((tip, i) => (
                  <p key={i} className="text-sm text-[#2F4731]/80">📹 {tip}</p>
                ))}
              </div>
              <div className="pt-2 border-t border-[#BD6809]/10">
                <p className="text-xs text-[#2F4731]/50 mb-1">Caption template:</p>
                <p className="text-sm font-medium text-[#BD6809] italic">
                  "{experiment.social_media_kit.caption_template}"
                </p>
              </div>
              <div className="flex flex-wrap gap-1">
                {experiment.social_media_kit.hashtags.map((tag) => (
                  <span key={tag} className="text-xs font-bold text-[#BD6809]/60">{tag}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Phase: Done ──────────────────────────────────────────── */}
      {phase === "done" && (
        <div className="px-6 py-6 space-y-5 text-center">
          <p className="text-4xl">{chaos.emoji}</p>
          <h3
            className="text-2xl font-bold text-[#2F4731]"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            Experiment Complete!
          </h3>

          {/* Creation Connection reveal */}
          <button
            onClick={() => setShowCreation(!showCreation)}
            className="w-full py-3 rounded-xl border-2 text-sm font-bold transition-all hover:scale-[1.01]"
            style={{ borderColor: "#9A3F4A", color: "#9A3F4A", background: showCreation ? "#FEF2F2" : "#fff" }}
          >
            ✝️ God's Creation Connection
          </button>

          {showCreation && (
            <div className="rounded-xl bg-[#FEF2F2] border border-[#9A3F4A]/20 p-5 text-left space-y-3">
              <p className="text-sm font-black text-[#9A3F4A]">{experiment.creation_connection.title}</p>
              {experiment.creation_connection.scripture && (
                <p className="text-xs italic text-[#9A3F4A]/70">
                  {experiment.creation_connection.scripture}
                </p>
              )}
              <p className="text-sm text-[#2F4731]/80 leading-relaxed">
                {experiment.creation_connection.explanation}
              </p>
            </div>
          )}

          {/* Seal / Upload */}
          <button
            onClick={() => onSeal?.(experiment.id)}
            className="w-full py-4 rounded-2xl text-sm font-black uppercase tracking-widest text-white transition-all hover:brightness-110"
            style={{ background: "#166534" }}
          >
            📤 Upload Discovery Video & Seal Credit
          </button>

          <p className="text-xs text-[#2F4731]/40">
            Credit: {experiment.science_credits.map((c) => c.replace(/_/g, " ")).join(" + ")}
          </p>
        </div>
      )}
    </div>
  );
}
