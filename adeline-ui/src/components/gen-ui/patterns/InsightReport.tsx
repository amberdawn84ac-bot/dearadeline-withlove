"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Target, TrendingUp, ChevronDown, ChevronUp } from "lucide-react";

export interface ConceptMastery {
  concept_id: string;
  concept_name: string;
  mastery: number;
  status: "not_started" | "in_progress" | "mastered";
}

export interface InsightReportProps {
  topic: string;
  track: string;
  reason: string;
  zpd_priority: number;
  prereq_readiness: number;
  concepts: ConceptMastery[];
  next_steps: string[];
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

const TRACK_COLORS: Record<string, string> = {
  TRUTH_HISTORY:        "#1E3A5F",
  JUSTICE_CHANGEMAKING: "#7C2D12",
  GOVERNMENT_ECONOMICS: "#78350F",
  CREATION_SCIENCE:     "#14532D",
  HOMESTEADING:         "#365314",
  DISCIPLESHIP:         "#581C87",
  HEALTH_NATUROPATHY:   "#164E63",
  ENGLISH_LITERATURE:   "#7C3AED",
  APPLIED_MATHEMATICS:  "#1D4ED8",
  CREATIVE_ECONOMY:     "#9D174D",
};

function MasteryBar({ concept }: { concept: ConceptMastery }) {
  const pct = Math.round(concept.mastery * 100);
  const color =
    concept.status === "mastered"    ? "#10B981" :
    concept.status === "in_progress" ? "#F59E0B" : "#E5E7EB";
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-[#374151] leading-snug truncate pr-2">{concept.concept_name}</span>
        <span className="text-[10px] font-semibold shrink-0" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-[#E5E7EB] overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.05 }}
        />
      </div>
    </div>
  );
}

export function InsightReport({
  topic,
  track,
  reason,
  zpd_priority,
  prereq_readiness,
  concepts,
  next_steps,
}: InsightReportProps) {
  const [showConcepts, setShowConcepts] = useState(false);
  const themeColor = TRACK_COLORS[track] ?? "#1E3A5F";

  const mastered    = concepts.filter((c) => c.status === "mastered").length;
  const inProgress  = concepts.filter((c) => c.status === "in_progress").length;
  const notStarted  = concepts.filter((c) => c.status === "not_started").length;

  const metrics = [
    { label: "ZPD Priority",      value: zpd_priority,      icon: <Target size={11} /> },
    { label: "Prereq Readiness",  value: prereq_readiness,  icon: <TrendingUp size={11} /> },
  ];

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `1.5px solid ${themeColor}25`, background: "#FAFBFF" }}
    >
      {/* Header */}
      <div
        className="px-4 py-2.5 flex items-center gap-2"
        style={{ background: `${themeColor}08`, borderBottom: `1px solid ${themeColor}15` }}
      >
        <Brain size={13} style={{ color: themeColor }} />
        <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: themeColor }}>
          Learning Insight
        </span>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Topic + reason */}
        <div>
          <p className="text-sm font-bold text-[#1F2937] mb-1">{topic}</p>
          <p className="text-xs text-[#6B7280] leading-relaxed">{reason}</p>
        </div>

        {/* ZPD metrics */}
        <div className="grid grid-cols-2 gap-2">
          {metrics.map(({ label, value, icon }) => (
            <div
              key={label}
              className="rounded-lg px-3 py-2.5 text-center"
              style={{ background: `${themeColor}08`, border: `1px solid ${themeColor}15` }}
            >
              <div className="flex items-center justify-center gap-1 mb-1" style={{ color: themeColor }}>
                {icon}
                <span className="text-[9px] font-bold uppercase tracking-wider">{label}</span>
              </div>
              <p className="text-lg font-bold" style={{ color: themeColor }}>
                {Math.round(value * 100)}%
              </p>
              <div className="h-1 rounded-full bg-white mt-1.5 overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: themeColor }}
                  initial={{ width: 0 }}
                  animate={{ width: `${value * 100}%` }}
                  transition={{ duration: 0.6 }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Concept mastery collapsible */}
        {concepts.length > 0 && (
          <div>
            <button
              onClick={() => setShowConcepts((s) => !s)}
              className="flex items-center justify-between w-full"
            >
              <span className="text-[11px] font-semibold text-[#374151]">
                Concept Mastery
                <span className="font-normal text-[#9CA3AF] ml-1">
                  ({mastered} mastered · {inProgress} in progress · {notStarted} not started)
                </span>
              </span>
              {showConcepts
                ? <ChevronUp size={12} className="text-[#9CA3AF]" />
                : <ChevronDown size={12} className="text-[#9CA3AF]" />
              }
            </button>
            <AnimatePresence>
              {showConcepts && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden mt-2 space-y-2"
                >
                  {concepts.map((c) => <MasteryBar key={c.concept_id} concept={c} />)}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Next steps */}
        {next_steps.length > 0 && (
          <div
            className="rounded-xl px-3 py-2.5 space-y-1.5"
            style={{ background: `${themeColor}06`, border: `1px solid ${themeColor}15` }}
          >
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: themeColor }}>
              Recommended Next
            </p>
            {next_steps.map((step, i) => (
              <p key={i} className="text-xs text-[#374151] leading-snug flex gap-1.5">
                <span style={{ color: themeColor }}>→</span>
                {step}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
