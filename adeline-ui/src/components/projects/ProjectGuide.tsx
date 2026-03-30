"use client";

/**
 * ProjectGuide.tsx — Step-by-step project runner.
 *
 * Phases: materials → steps → done
 * Fetches project from /projects/{projectId} on mount.
 * Seal button calls onSeal and records credit via sealProject().
 */

import { useState, useEffect } from "react";
import { fetchProject, startProject, sealProject } from "@/lib/brain-client";
import type { ProjectDetail } from "@/lib/brain-client";

// ── Track accent colors ───────────────────────────────────────────────────────

const TRACK_COLOR: Record<string, string> = {
  CREATIVE_ECONOMY: "#BD6809",
  HOMESTEADING:     "#166534",
};

// ── Loading Skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="rounded-3xl border-2 border-[#E7DAC3] overflow-hidden animate-pulse bg-[#FFFEF7]">
      <div className="p-6 space-y-3 bg-[#FDF6E9]">
        <div className="h-7 w-3/4 rounded-xl bg-[#E7DAC3]" />
        <div className="h-4 w-1/2 rounded bg-[#E7DAC3]" />
        <div className="flex gap-2">
          <div className="h-5 w-20 rounded-full bg-[#E7DAC3]" />
          <div className="h-5 w-16 rounded-full bg-[#E7DAC3]" />
        </div>
      </div>
      <div className="p-6 space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-lg bg-[#E7DAC3] shrink-0" />
            <div className="h-4 flex-1 rounded bg-[#E7DAC3]" style={{ width: `${60 + i * 7}%` }} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

interface ProjectGuideProps {
  projectId: string;
  studentId: string;
  onSeal: (projectId: string) => void;
}

export function ProjectGuide({ projectId, studentId, onSeal }: ProjectGuideProps) {
  const [project, setProject]         = useState<ProjectDetail | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [phase, setPhase]             = useState<"materials" | "steps" | "done">("materials");
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const [currentStep, setCurrentStep] = useState(0);
  const [sealing, setSealing]         = useState(false);

  // Fetch on mount
  useEffect(() => {
    let cancelled = false;
    fetchProject(projectId)
      .then((p) => { if (!cancelled) setProject(p); })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load project.");
      });
    return () => { cancelled = true; };
  }, [projectId]);

  if (error) {
    return (
      <div className="rounded-2xl border-2 border-[#9A3F4A]/30 bg-[#FEF2F2] p-6 text-center">
        <p className="text-sm font-bold text-[#9A3F4A]">Could not load project.</p>
        <p className="text-xs text-[#9A3F4A]/60 mt-1">{error}</p>
      </div>
    );
  }

  if (!project) return <LoadingSkeleton />;

  const accentColor = TRACK_COLOR[project.track] ?? "#BD6809";
  const allGathered = checkedItems.size === project.materials.length;
  const step        = project.steps[currentStep];
  const totalSteps  = project.steps.length;

  function toggleItem(idx: number) {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  }

  async function handleStartSteps() {
    try {
      await startProject(projectId, studentId);
    } catch {
      // Best-effort — not fatal if the start endpoint is not live yet
    }
    setPhase("steps");
  }

  async function handleSeal() {
    setSealing(true);
    try {
      await sealProject(projectId, studentId);
      onSeal(projectId);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Seal failed.";
      setError(msg);
    } finally {
      setSealing(false);
    }
  }

  return (
    <div
      className="rounded-3xl border-2 overflow-hidden"
      style={{ borderColor: accentColor, background: "#FFFEF7" }}
    >
      {/* ── Header ───────────────────────────────────────────────── */}
      <div
        className="p-6 space-y-2"
        style={{ background: project.track === "HOMESTEADING" ? "#F0FDF4" : "#FDF6E9" }}
      >
        <h2
          className="text-3xl font-bold tracking-tight text-[#2F4731]"
          style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
        >
          {project.title}
        </h2>
        <p className="text-sm text-[#2F4731]/60 max-w-md">{project.tagline}</p>

        {/* Meta badges */}
        <div className="flex flex-wrap gap-2 pt-1 text-xs">
          <span className="px-2 py-0.5 rounded-full font-bold text-white" style={{ background: accentColor }}>
            {project.track === "HOMESTEADING" ? "Homesteading" : "Creative Economy"}
          </span>
          <span className="px-2 py-0.5 rounded-full font-bold bg-[#2F4731] text-white">
            ⏱ {project.estimated_hours}h
          </span>
          <span className="px-2 py-0.5 rounded-full border border-[#E7DAC3] text-[#2F4731]/60">
            Grades {project.grade_band}
          </span>
        </div>
      </div>

      {/* ── Safety (always visible if present) ───────────────────── */}
      {project.safety_notes.length > 0 && (
        <div
          className="px-6 py-3 border-b"
          style={{ borderColor: accentColor + "40", background: accentColor + "10" }}
        >
          <p
            className="text-xs font-black uppercase tracking-wider mb-1.5"
            style={{ color: accentColor }}
          >
            ⚠ Safety
          </p>
          <ul className="space-y-1">
            {project.safety_notes.map((note, i) => (
              <li key={i} className="text-xs text-[#2F4731]/80 flex items-start gap-2">
                <span style={{ color: accentColor }}>&#9888;</span>
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* ── Phase: Materials ─────────────────────────────────────── */}
      {/* ══════════════════════════════════════════════════════════ */}
      {phase === "materials" && (
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm font-bold text-[#2F4731]">Gather your materials:</p>

          <ul className="space-y-2">
            {project.materials.map((mat, i) => (
              <li key={i} className="flex items-center gap-3">
                <button
                  onClick={() => toggleItem(i)}
                  className="w-6 h-6 rounded-lg border-2 flex items-center justify-center text-xs transition-all shrink-0"
                  style={{
                    borderColor: checkedItems.has(i) ? "#166534" : "#E7DAC3",
                    background:  checkedItems.has(i) ? "#F0FDF4"  : "#fff",
                    color:       checkedItems.has(i) ? "#166534"  : "#ccc",
                  }}
                >
                  {checkedItems.has(i) ? "✓" : ""}
                </button>
                <span
                  className="text-sm"
                  style={{
                    color:          checkedItems.has(i) ? "#2F4731"   : "#2F4731aa",
                    textDecoration: checkedItems.has(i) ? "line-through" : "none",
                  }}
                >
                  {mat}
                </span>
              </li>
            ))}
          </ul>

          <button
            onClick={handleStartSteps}
            disabled={!allGathered}
            className="w-full py-4 rounded-2xl text-sm font-black uppercase tracking-widest text-white transition-all disabled:opacity-30 hover:brightness-110"
            style={{ background: accentColor }}
          >
            {allGathered ? "All Gathered — Start" : "Check off all materials first"}
          </button>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* ── Phase: Steps ─────────────────────────────────────────── */}
      {/* ══════════════════════════════════════════════════════════ */}
      {phase === "steps" && (
        <div className="px-6 py-5 space-y-5">
          {/* Step counter */}
          <p
            className="text-xs font-black uppercase tracking-widest"
            style={{ color: accentColor }}
          >
            Step {step.step_number} of {totalSteps}
          </p>

          {/* Big instruction card */}
          <div className="rounded-2xl border-2 border-[#E7DAC3] p-6 min-h-[180px] flex flex-col justify-center space-y-4">
            <p
              className="text-2xl font-bold leading-relaxed text-[#2F4731]"
              style={{ fontFamily: "var(--font-kalam), cursive" }}
            >
              {step.instruction}
            </p>
            {step.tip && (
              <p className="text-sm italic" style={{ color: accentColor }}>
                💡 {step.tip}
              </p>
            )}
          </div>

          {/* Step dots + prev/next navigation */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
              disabled={currentStep === 0}
              className="px-4 py-2 rounded-xl border-2 border-[#E7DAC3] text-sm font-bold disabled:opacity-30 hover:bg-[#F5F0E8] transition-colors"
            >
              ← Back
            </button>

            {/* Dots */}
            <div className="flex gap-1.5 flex-1 justify-center flex-wrap">
              {project.steps.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentStep(i)}
                  className="w-2.5 h-2.5 rounded-full transition-all hover:scale-125"
                  style={{
                    background:
                      i === currentStep
                        ? accentColor
                        : i < currentStep
                        ? "#166534"
                        : "#E7DAC3",
                  }}
                />
              ))}
            </div>

            {currentStep < totalSteps - 1 ? (
              <button
                onClick={() => setCurrentStep((s) => s + 1)}
                className="px-4 py-2 rounded-xl text-sm font-bold text-white hover:brightness-110 transition-all"
                style={{ background: accentColor }}
              >
                Next →
              </button>
            ) : (
              <button
                onClick={() => setPhase("done")}
                className="px-4 py-2 rounded-xl text-sm font-black text-white uppercase tracking-wider hover:brightness-110 transition-all"
                style={{ background: "#166534" }}
              >
                Done ✓
              </button>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* ── Phase: Done ──────────────────────────────────────────── */}
      {/* ══════════════════════════════════════════════════════════ */}
      {phase === "done" && (
        <div className="px-6 py-6 space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <p className="text-5xl">🎉</p>
            <h3
              className="text-2xl font-bold text-[#2F4731]"
              style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
            >
              Project Complete
            </h3>
          </div>

          {/* Business skills earned */}
          {project.business_skills.length > 0 && (
            <div className="rounded-2xl border border-[#E7DAC3] p-4 space-y-2">
              <p className="text-xs font-black uppercase tracking-wider text-[#2F4731]">
                Business Skills Earned
              </p>
              <ul className="space-y-1.5">
                {project.business_skills.map((skill) => (
                  <li key={skill} className="flex items-center gap-2 text-sm text-[#2F4731]/80">
                    <span style={{ color: accentColor }}>✦</span>
                    {skill}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Price range + where to sell */}
          {(project.price_range || project.where_to_sell.length > 0) && (
            <div
              className="rounded-2xl p-4 space-y-3"
              style={{ background: accentColor + "12" }}
            >
              {project.price_range && (
                <div>
                  <p className="text-xs font-black uppercase tracking-wider mb-1" style={{ color: accentColor }}>
                    What It Sells For
                  </p>
                  <p className="text-xl font-bold text-[#2F4731]">
                    ${project.price_range.low}–${project.price_range.high}
                    <span className="text-sm font-normal text-[#2F4731]/50 ml-1">{project.price_range.unit}</span>
                  </p>
                  {project.income_description && (
                    <p className="text-xs text-[#2F4731]/60 mt-1 leading-relaxed">
                      {project.income_description}
                    </p>
                  )}
                </div>
              )}

              {project.where_to_sell.length > 0 && (
                <div>
                  <p className="text-xs font-black uppercase tracking-wider mb-2" style={{ color: accentColor }}>
                    Where to Sell
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {project.where_to_sell.map((place) => (
                      <span
                        key={place}
                        className="text-xs font-bold px-2 py-0.5 rounded-full border"
                        style={{ borderColor: accentColor + "60", color: accentColor }}
                      >
                        {place}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Portfolio prompts — shown as reflection questions */}
          {project.portfolio_prompts.length > 0 && (
            <div className="rounded-2xl bg-[#FEF2F2] border border-[#9A3F4A]/10 p-5 space-y-3">
              <p className="text-xs font-black uppercase tracking-wider text-[#9A3F4A]">
                Portfolio — Answer These
              </p>
              <ol className="space-y-3 list-none">
                {project.portfolio_prompts.map((prompt, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="text-xs font-black text-[#9A3F4A] shrink-0 mt-0.5">{i + 1}.</span>
                    <p className="text-sm text-[#2F4731]/80 leading-relaxed">{prompt}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Seal CTA */}
          <button
            onClick={handleSeal}
            disabled={sealing}
            className="w-full py-4 rounded-2xl text-sm font-black uppercase tracking-widest text-white transition-all hover:brightness-110 disabled:opacity-50"
            style={{ background: "#166534" }}
          >
            {sealing ? "Recording..." : "Seal Credit & Add to Portfolio"}
          </button>
        </div>
      )}
    </div>
  );
}
