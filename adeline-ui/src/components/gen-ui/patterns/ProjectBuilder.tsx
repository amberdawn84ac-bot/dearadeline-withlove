"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, Circle, ChevronDown, ChevronUp, Package, Clock, Award } from "lucide-react";

export interface ProjectStep {
  title: string;
  description: string;
  estimated_minutes?: number;
  materials?: string[];
}

export interface ProjectBuilderProps {
  title: string;
  description: string;
  track?: string;
  steps: ProjectStep[];
  materials?: string[];
  estimated_hours?: number;
  portfolio_credit?: boolean;
  difficulty?: "beginner" | "intermediate" | "advanced";
  onComplete?: (completedSteps: number[]) => void;
  onStateChange?: (state: Record<string, any>) => void;
}

const DIFFICULTY_COLORS = {
  beginner:     { bg: "#D1FAE5", text: "#065F46", label: "Beginner" },
  intermediate: { bg: "#FEF3C7", text: "#92400E", label: "Intermediate" },
  advanced:     { bg: "#FEE2E2", text: "#991B1B", label: "Advanced" },
};

export function ProjectBuilder({
  title,
  description,
  track,
  steps,
  materials = [],
  estimated_hours,
  portfolio_credit = false,
  difficulty = "beginner",
  onComplete,
  onStateChange,
}: ProjectBuilderProps) {
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [expandedStep, setExpandedStep] = useState<number | null>(0);
  const [showMaterials, setShowMaterials] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const themeColor = track === "CREATIVE_ECONOMY" ? "#7C3AED" : "#2F4731";
  const accentColor = track === "CREATIVE_ECONOMY" ? "#A78BFA" : "#8BAE6B";
  const diff = DIFFICULTY_COLORS[difficulty];

  const allCompleted = completedSteps.size === steps.length && steps.length > 0;
  const progressPct = steps.length > 0 ? Math.round((completedSteps.size / steps.length) * 100) : 0;

  const toggleStep = (idx: number) => {
    const next = new Set(completedSteps);
    if (next.has(idx)) {
      next.delete(idx);
    } else {
      next.add(idx);
    }
    setCompletedSteps(next);
    onStateChange?.({ completedSteps: [...next], total: steps.length });

    if (next.size === steps.length) {
      onComplete?.([...next]);
    }
  };

  const handleSubmit = () => {
    setSubmitted(true);
    onComplete?.([...completedSteps]);
    onStateChange?.({ submitted: true, completedSteps: [...completedSteps] });
  };

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}30`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div
        className="px-5 py-4"
        style={{ background: `${themeColor}08`, borderBottom: `1px solid ${themeColor}15` }}
      >
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                style={{ background: themeColor, color: "#fff" }}
              >
                Project
              </span>
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                style={{ background: diff.bg, color: diff.text }}
              >
                {diff.label}
              </span>
              {portfolio_credit && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1"
                  style={{ background: "#FEF3C7", color: "#92400E" }}>
                  <Award size={10} />
                  Portfolio Credit
                </span>
              )}
            </div>
            <h3 className="text-base font-bold leading-tight" style={{ color: themeColor }}>
              {title}
            </h3>
          </div>
          {estimated_hours && (
            <div className="flex items-center gap-1 text-xs shrink-0" style={{ color: "#9CA3AF" }}>
              <Clock size={12} />
              {estimated_hours}h
            </div>
          )}
        </div>

        <p className="text-sm leading-relaxed text-[#6B7280]">{description}</p>

        {/* Progress bar */}
        {steps.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] mb-1">
              <span>{completedSteps.size} of {steps.length} steps complete</span>
              <span>{progressPct}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-[#E5E7EB] overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: accentColor }}
                animate={{ width: `${progressPct}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Materials list (collapsible) */}
      {materials.length > 0 && (
        <div style={{ borderBottom: `1px solid ${themeColor}10` }}>
          <button
            onClick={() => setShowMaterials(!showMaterials)}
            className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium"
            style={{ color: themeColor }}
          >
            <span className="flex items-center gap-2">
              <Package size={14} />
              Materials ({materials.length})
            </span>
            {showMaterials ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <AnimatePresence>
            {showMaterials && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-5 pb-3 flex flex-wrap gap-2">
                  {materials.map((m, i) => (
                    <span
                      key={i}
                      className="text-xs px-2.5 py-1 rounded-full"
                      style={{ background: `${accentColor}20`, color: themeColor }}
                    >
                      {m}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Steps list */}
      <div className="divide-y" style={{ borderColor: `${themeColor}08` }}>
        {steps.map((step, idx) => {
          const isDone = completedSteps.has(idx);
          const isExpanded = expandedStep === idx;

          return (
            <div key={idx} className={isDone ? "opacity-80" : ""}>
              <div
                className="flex items-start gap-3 px-5 py-3 cursor-pointer hover:bg-[#FAFAF7] transition-colors"
                onClick={() => setExpandedStep(isExpanded ? null : idx)}
              >
                {/* Checkbox */}
                <button
                  onClick={(e) => { e.stopPropagation(); toggleStep(idx); }}
                  className="mt-0.5 shrink-0 transition-transform active:scale-90"
                >
                  {isDone ? (
                    <CheckCircle size={20} style={{ color: accentColor }} />
                  ) : (
                    <Circle size={20} style={{ color: `${themeColor}40` }} />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={`text-sm font-semibold leading-snug ${isDone ? "line-through" : ""}`}
                      style={{ color: isDone ? "#9CA3AF" : themeColor }}
                    >
                      {idx + 1}. {step.title}
                    </p>
                    <div className="flex items-center gap-2 shrink-0">
                      {step.estimated_minutes && (
                        <span className="text-[10px] text-[#9CA3AF]">
                          ~{step.estimated_minutes}m
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronUp size={14} style={{ color: "#9CA3AF" }} />
                      ) : (
                        <ChevronDown size={14} style={{ color: "#9CA3AF" }} />
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Expanded step detail */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="px-5 pb-4 pl-14 space-y-3">
                      <p className="text-sm leading-relaxed text-[#6B7280]">
                        {step.description}
                      </p>
                      {step.materials && step.materials.length > 0 && (
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9CA3AF] mb-1.5">
                            For this step
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {step.materials.map((m, mi) => (
                              <span
                                key={mi}
                                className="text-xs px-2 py-0.5 rounded-full"
                                style={{ background: `${accentColor}15`, color: themeColor }}
                              >
                                {m}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      <button
                        onClick={() => toggleStep(idx)}
                        className="text-xs font-semibold px-3 py-1.5 rounded-lg transition-opacity"
                        style={{
                          background: isDone ? "#E5E7EB" : accentColor,
                          color: isDone ? "#6B7280" : "#fff",
                        }}
                      >
                        {isDone ? "Mark incomplete" : "Mark complete"}
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {/* Submit for portfolio */}
      {portfolio_credit && (
        <div
          className="px-5 py-4"
          style={{ borderTop: `1px solid ${themeColor}15` }}
        >
          {submitted ? (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-2"
            >
              <p className="text-sm font-bold" style={{ color: themeColor }}>
                Project submitted for your portfolio.
              </p>
              <p className="text-xs text-[#9CA3AF] mt-0.5">
                Adeline's Registrar will credit this to your transcript.
              </p>
            </motion.div>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!allCompleted}
              className="w-full py-3 rounded-xl text-sm font-bold transition-all disabled:opacity-40"
              style={{
                background: allCompleted ? themeColor : "#E5E7EB",
                color: allCompleted ? "#fff" : "#9CA3AF",
              }}
            >
              {allCompleted
                ? "Submit to Portfolio"
                : `Complete all ${steps.length} steps to submit`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
