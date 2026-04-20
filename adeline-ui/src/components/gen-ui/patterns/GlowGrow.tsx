"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Sparkles, TrendingUp, ChevronRight } from "lucide-react";

export interface GlowGrowQuestion {
  question: string;
  options: { text: string; is_correct: boolean }[];
  explanation: string;
  glow: string;
  grow: string;
}

export interface GlowGrowProps {
  title?: string;
  topic?: string;
  questions: GlowGrowQuestion[];
  onComplete?: (score: number) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

type Phase = "quiz" | "results";

export function GlowGrow({
  title = "QuizMe",
  topic,
  questions,
  onComplete,
  onStateChange,
  state,
}: GlowGrowProps) {
  const [phase, setPhase] = useState<Phase>((state?.phase as Phase) ?? "quiz");
  const [qIdx, setQIdx] = useState((state?.qIdx as number) ?? 0);
  const [selected, setSelected] = useState<number | null>(null);
  const [answers, setAnswers] = useState<boolean[]>((state?.answers as boolean[]) ?? []);

  const question = questions[qIdx];
  const isAnswered = selected !== null;

  const handleNext = () => {
    if (!isAnswered) return;
    const correct = question.options[selected!].is_correct;
    const newAnswers = [...answers, correct];

    if (qIdx + 1 >= questions.length) {
      setAnswers(newAnswers);
      setPhase("results");
      onComplete?.(newAnswers.filter(Boolean).length / questions.length);
      onStateChange?.({ phase: "results", answers: newAnswers, qIdx });
    } else {
      setAnswers(newAnswers);
      setQIdx(qIdx + 1);
      setSelected(null);
      onStateChange?.({ phase: "quiz", qIdx: qIdx + 1, answers: newAnswers });
    }
  };

  const score = answers.filter(Boolean).length;
  const total = questions.length;
  const pct = total > 0 ? score / total : 0;

  const glows = questions.filter((_, i) => answers[i] === true).map((q) => q.glow);
  const grows  = questions.filter((_, i) => answers[i] === false).map((q) => q.grow);

  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: "1.5px solid #E5E7EB", background: "#FAFBFF" }}>
      {/* Header */}
      <div
        className="px-4 py-2.5 flex items-center justify-between"
        style={{ background: "#F9FAFB", borderBottom: "1px solid #F3F4F6" }}
      >
        <div className="flex items-center gap-1.5">
          <Sparkles size={13} className="text-[#6B7280]" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#374151]">{title}</span>
          {topic && <span className="text-[10px] text-[#9CA3AF]">· {topic}</span>}
        </div>
        {phase === "quiz" && (
          <span className="text-[10px] text-[#9CA3AF]">{qIdx + 1} / {total}</span>
        )}
      </div>

      <AnimatePresence mode="wait">
        {phase === "quiz" ? (
          <motion.div
            key={`q-${qIdx}`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="px-4 py-4 space-y-3"
          >
            {/* Progress bar */}
            <div className="h-1 rounded-full bg-[#E5E7EB] overflow-hidden">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all"
                style={{ width: `${(qIdx / total) * 100}%` }}
              />
            </div>

            <p className="text-sm font-semibold text-[#1F2937] leading-snug">{question.question}</p>

            <div className="space-y-2">
              {question.options.map((opt, i) => {
                let bg = "#fff", border = "#E5E7EB", color = "#374151";
                if (isAnswered) {
                  if (opt.is_correct)                      { bg = "#F0FDF4"; border = "#86EFAC"; color = "#15803D"; }
                  else if (i === selected && !opt.is_correct) { bg = "#FEF2F2"; border = "#FCA5A5"; color = "#DC2626"; }
                } else if (i === selected) {
                  bg = "#EEF2FF"; border = "#A5B4FC"; color = "#3730A3";
                }
                return (
                  <button
                    key={i}
                    onClick={() => !isAnswered && setSelected(i)}
                    disabled={isAnswered}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all text-sm"
                    style={{ background: bg, border: `1px solid ${border}`, color }}
                  >
                    <span className="shrink-0 font-bold text-[11px]">{String.fromCharCode(65 + i)}</span>
                    <span className="flex-1 leading-snug">{opt.text}</span>
                    {isAnswered && opt.is_correct       && <CheckCircle2 size={14} className="shrink-0 text-emerald-500" />}
                    {isAnswered && i === selected && !opt.is_correct && <XCircle size={14} className="shrink-0 text-red-400" />}
                  </button>
                );
              })}
            </div>

            <AnimatePresence>
              {isAnswered && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="overflow-hidden space-y-2"
                >
                  <div
                    className="rounded-lg px-3 py-2 text-xs leading-relaxed"
                    style={{
                      background: question.options[selected!].is_correct ? "#F0FDF4" : "#FEF2F2",
                      color: question.options[selected!].is_correct ? "#15803D" : "#DC2626",
                    }}
                  >
                    <span className="font-semibold">
                      {question.options[selected!].is_correct ? "✓ Correct! " : "✗ Not quite. "}
                    </span>
                    {question.explanation}
                  </div>
                  <button
                    onClick={handleNext}
                    className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#1F2937] text-white"
                  >
                    {qIdx + 1 < total ? "Next Question" : "See Results"}
                    <ChevronRight size={12} />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ) : (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="px-4 py-4 space-y-4"
          >
            {/* Score row */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-bold text-[#1F2937]">{score} / {total}</p>
                <p className="text-[11px] text-[#9CA3AF]">
                  {pct >= 0.8 ? "Excellent!" : pct >= 0.6 ? "Good work!" : "Keep practicing!"}
                </p>
              </div>
              <div className="relative" style={{ width: 56, height: 56 }}>
                <svg width="56" height="56" className="-rotate-90">
                  <circle cx="28" cy="28" r="22" fill="none" stroke="#E5E7EB" strokeWidth="5" />
                  <circle
                    cx="28" cy="28" r="22" fill="none"
                    stroke={pct >= 0.8 ? "#10B981" : pct >= 0.6 ? "#F59E0B" : "#EF4444"}
                    strokeWidth="5"
                    strokeDasharray={`${2 * Math.PI * 22}`}
                    strokeDashoffset={`${2 * Math.PI * 22 * (1 - pct)}`}
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-[#374151]">
                  {Math.round(pct * 100)}%
                </span>
              </div>
            </div>

            {/* Glows */}
            {glows.length > 0 && (
              <div className="rounded-xl px-3 py-2.5" style={{ background: "#F0FDF4", border: "1px solid #BBF7D0" }}>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-base">✨</span>
                  <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">Glows</span>
                </div>
                <ul className="space-y-1">
                  {glows.map((g, i) => (
                    <li key={i} className="text-xs text-emerald-800 leading-snug flex gap-1.5">
                      <CheckCircle2 size={11} className="shrink-0 mt-0.5 text-emerald-500" />
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Grows */}
            {grows.length > 0 && (
              <div className="rounded-xl px-3 py-2.5" style={{ background: "#FFFBEB", border: "1px solid #FDE68A" }}>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-base">🌱</span>
                  <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">Grows</span>
                </div>
                <ul className="space-y-1">
                  {grows.map((g, i) => (
                    <li key={i} className="text-xs text-amber-900 leading-snug flex gap-1.5">
                      <TrendingUp size={11} className="shrink-0 mt-0.5 text-amber-500" />
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
