"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle } from "lucide-react";

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

export interface EmbeddedInterruptOption {
  text: string;
  is_correct: boolean;
}

export interface EmbeddedInterruptProps {
  question: string;
  options: EmbeddedInterruptOption[];
  track?: string;
  checkpoint_label?: string;
  hint?: string;
  onAnswer?: (correct: boolean) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

export function EmbeddedInterrupt({
  question,
  options,
  track,
  checkpoint_label = "Quick Check",
  hint,
  onAnswer,
  onStateChange,
  state,
}: EmbeddedInterruptProps) {
  const [selected, setSelected] = useState<number | null>(state?.selected as number ?? null);
  const [dismissed, setDismissed] = useState(!!state?.dismissed);

  const themeColor = TRACK_COLORS[track ?? ""] ?? "#1D4ED8";
  const isAnswered = selected !== null;
  const wasCorrect = selected !== null && options[selected]?.is_correct;

  const handleSelect = (i: number) => {
    if (isAnswered) return;
    setSelected(i);
    const correct = options[i].is_correct;
    onAnswer?.(correct);
    onStateChange?.({ selected: i, dismissed: false });
  };

  // Dismissed state — minimal footprint after answering
  if (dismissed) {
    return (
      <div
        className="flex items-center gap-2 my-3 px-3 py-1.5 rounded-lg text-xs font-semibold"
        style={{
          background: wasCorrect ? "#F0FDF4" : "#FEF2F2",
          border: `1px solid ${wasCorrect ? "#BBF7D0" : "#FECACA"}`,
          color: wasCorrect ? "#15803D" : "#DC2626",
        }}
      >
        {wasCorrect ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
        {wasCorrect ? "Checkpoint cleared" : "Checkpoint — review and continue"}
      </div>
    );
  }

  return (
    <motion.div
      layout
      className="my-4 rounded-xl overflow-hidden"
      style={{ border: `1.5px solid ${themeColor}20`, background: `${themeColor}04` }}
    >
      {/* Label bar */}
      <div
        className="px-3 py-1.5 flex items-center gap-1.5"
        style={{ background: `${themeColor}10`, borderBottom: `1px solid ${themeColor}12` }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-widest"
          style={{ color: themeColor }}
        >
          {checkpoint_label}
        </span>
      </div>

      <div className="px-3 pt-2.5 pb-3 space-y-2">
        <p className="text-sm text-[#1F2937] leading-snug font-medium">{question}</p>

        <div className="space-y-1.5">
          {options.map((opt, i) => {
            let bg = "#fff", border = `${themeColor}18`, color = "#374151";
            if (isAnswered) {
              if (opt.is_correct)                      { bg = "#F0FDF4"; border = "#86EFAC"; color = "#15803D"; }
              else if (i === selected && !opt.is_correct) { bg = "#FEF2F2"; border = "#FCA5A5"; color = "#DC2626"; }
              else                                        { bg = "#FAFAFA"; border = "#E5E7EB"; color = "#9CA3AF"; }
            } else if (i === selected) {
              bg = `${themeColor}10`; border = `${themeColor}40`;
            }

            return (
              <button
                key={i}
                onClick={() => handleSelect(i)}
                disabled={isAnswered}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-left text-xs transition-all"
                style={{ background: bg, border: `1px solid ${border}`, color }}
              >
                <span className="shrink-0 w-4 h-4 rounded-full border flex items-center justify-center text-[9px] font-bold"
                  style={{ borderColor: isAnswered ? "transparent" : themeColor, color: isAnswered ? "inherit" : themeColor }}
                >
                  {isAnswered && opt.is_correct       ? <CheckCircle2 size={12} className="text-emerald-500" /> :
                   isAnswered && i === selected && !opt.is_correct ? <XCircle size={12} className="text-red-400" /> :
                   String.fromCharCode(65 + i)}
                </span>
                <span className="flex-1 leading-snug">{opt.text}</span>
              </button>
            );
          })}
        </div>

        {/* Hint + dismiss row */}
        <AnimatePresence>
          {isAnswered && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="overflow-hidden flex items-center justify-between pt-0.5"
            >
              {hint ? (
                <p className="text-[10px] text-[#6B7280] leading-relaxed flex-1 pr-2">{hint}</p>
              ) : <span />}
              <button
                onClick={() => {
                  setDismissed(true);
                  onStateChange?.({ selected, dismissed: true });
                }}
                className="text-[10px] font-semibold shrink-0 px-2 py-1 rounded transition-colors"
                style={{ color: themeColor, background: `${themeColor}10` }}
              >
                Continue reading →
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
