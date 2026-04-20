"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, RotateCcw } from "lucide-react";

export interface MnemonicWord {
  letter: string;
  word: string;
  connection?: string;
}

export interface MnemonicCardProps {
  concept: string;
  acronym: string;
  words: MnemonicWord[];
  tip?: string;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

const LETTER_COLORS = [
  "#1E3A5F", "#7C2D12", "#14532D", "#581C87",
  "#164E63", "#9D174D", "#78350F", "#1D4ED8",
];

export function MnemonicCard({
  concept,
  acronym,
  words,
  tip,
  onStateChange,
  state,
}: MnemonicCardProps) {
  const [practiceMode, setPracticeMode] = useState((state?.practiceMode as boolean) ?? false);
  const [revealed, setReveal] = useState<Set<number>>(
    new Set((state?.revealed as number[]) ?? [])
  );

  const toggleReveal = (i: number) => {
    if (!practiceMode) return;
    setReveal((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i); else next.add(i);
      onStateChange?.({ practiceMode, revealed: Array.from(next) });
      return next;
    });
  };

  const togglePractice = () => {
    const next = !practiceMode;
    setPracticeMode(next);
    setReveal(new Set());
    onStateChange?.({ practiceMode: next, revealed: [] });
  };

  const reset = () => {
    setReveal(new Set());
    onStateChange?.({ practiceMode, revealed: [] });
  };

  const allRevealed = practiceMode && revealed.size === words.length;

  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: "1.5px solid #E5E7EB", background: "#FAFBFF" }}>
      {/* Header */}
      <div
        className="px-4 py-2.5 flex items-center justify-between"
        style={{ background: "#F9FAFB", borderBottom: "1px solid #F3F4F6" }}
      >
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#374151]">Mnemonic</span>
          <span className="text-[10px] text-[#9CA3AF]">· {concept}</span>
        </div>
        <div className="flex items-center gap-1">
          {practiceMode && revealed.size > 0 && (
            <button
              onClick={reset}
              className="p-1 rounded text-[#9CA3AF] hover:text-[#374151] transition-colors"
              title="Reset"
            >
              <RotateCcw size={11} />
            </button>
          )}
          <button
            onClick={togglePractice}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-colors"
            style={{
              background: practiceMode ? "#1F2937" : "#F3F4F6",
              color: practiceMode ? "#fff" : "#6B7280",
            }}
          >
            {practiceMode ? <Eye size={10} /> : <EyeOff size={10} />}
            {practiceMode ? "Show All" : "Practice"}
          </button>
        </div>
      </div>

      {/* Acronym grid */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex flex-wrap gap-2">
          {words.map((w, i) => {
            const color = LETTER_COLORS[i % LETTER_COLORS.length];
            const isRevealed = !practiceMode || revealed.has(i);

            return (
              <motion.button
                key={i}
                onClick={() => toggleReveal(i)}
                disabled={!practiceMode}
                layout
                className="flex items-start gap-2 px-3 py-2 rounded-xl text-left transition-colors"
                style={{
                  background: `${color}08`,
                  border: `1.5px solid ${color}${isRevealed ? "30" : "12"}`,
                  cursor: practiceMode ? "pointer" : "default",
                }}
              >
                <span className="text-xl font-black shrink-0 leading-none" style={{ color }}>
                  {w.letter}
                </span>

                <AnimatePresence mode="wait">
                  {isRevealed ? (
                    <motion.div
                      key="revealed"
                      initial={{ opacity: 0, width: 0, overflow: "hidden" }}
                      animate={{ opacity: 1, width: "auto" }}
                      exit={{ opacity: 0, width: 0 }}
                    >
                      <p className="text-xs font-semibold text-[#374151] leading-snug whitespace-nowrap">{w.word}</p>
                      {w.connection && (
                        <p className="text-[10px] text-[#9CA3AF] leading-snug mt-0.5 whitespace-nowrap">{w.connection}</p>
                      )}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="hidden"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center"
                    >
                      <span className="text-[10px] text-[#9CA3AF] whitespace-nowrap">tap to reveal</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.button>
            );
          })}
        </div>

        {practiceMode && (
          <p className="text-[10px] text-[#9CA3AF] mt-2">
            {revealed.size} / {words.length} revealed
            {allRevealed && " · You've got it!"}
          </p>
        )}
      </div>

      {tip && (
        <div
          className="mx-4 mb-4 rounded-lg px-3 py-2 text-[11px] text-[#6B7280] leading-relaxed"
          style={{ background: "#F3F4F6" }}
        >
          💡 {tip}
        </div>
      )}
    </div>
  );
}
