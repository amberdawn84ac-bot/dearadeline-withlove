"use client";

/**
 * QuizCard — Multiple-choice quiz component for lesson blocks.
 * Adapted from cascade-adeline/src/components/gen-ui/patterns/QuizCard.tsx.
 * Uses dearadeline's PAPAYA/PARADISE/PALM color palette.
 */

import { useState } from "react";
import { CheckCircle, XCircle } from "lucide-react";

export interface QuizCardProps {
  question: string;
  options: string[];
  correctIndex: number;
  explanation?: string;
  onAnswer?: (isCorrect: boolean) => void;
}

export function QuizCard({
  question,
  options,
  correctIndex,
  explanation,
  onAnswer,
}: QuizCardProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [showResult, setShowResult]       = useState(false);

  const handleSelect = (index: number) => {
    if (showResult) return;
    setSelectedIndex(index);
    setShowResult(true);
    onAnswer?.(index === correctIndex);
  };

  const isCorrect = selectedIndex === correctIndex;

  return (
    <div
      className="rounded-2xl p-4 space-y-3"
      style={{ background: "#FFFEF7", border: "2px solid #2F473140" }}
    >
      <p className="text-sm font-bold text-[#2F4731] leading-relaxed">{question}</p>

      <div className="space-y-2">
        {options.map((option, idx) => {
          const isSelected      = selectedIndex === idx;
          const isCorrectOption = idx === correctIndex;
          const showCorrect     = showResult && isCorrectOption;
          const showIncorrect   = showResult && isSelected && !isCorrect;

          return (
            <button
              key={idx}
              onClick={() => handleSelect(idx)}
              disabled={showResult}
              className="w-full text-left flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition-all disabled:cursor-default"
              style={{
                background: showCorrect
                  ? "#D4EDDA"
                  : showIncorrect
                    ? "#F8D7DA"
                    : "#fff",
                border: `1.5px solid ${
                  showCorrect ? "#28A745" : showIncorrect ? "#DC3545" : "#E7DAC3"
                }`,
                opacity: showResult && !isSelected && !isCorrectOption ? 0.5 : 1,
                fontWeight: isSelected ? 700 : 400,
                color: "#2F4731",
              }}
            >
              {showCorrect && <CheckCircle size={16} style={{ color: "#28A745", flexShrink: 0 }} />}
              {showIncorrect && <XCircle size={16} style={{ color: "#DC3545", flexShrink: 0 }} />}
              {!showCorrect && !showIncorrect && (
                <span
                  className="w-5 h-5 rounded-full border text-[10px] font-bold flex items-center justify-center shrink-0"
                  style={{ borderColor: "#E7DAC3", color: "#2F4731" }}
                >
                  {String.fromCharCode(65 + idx)}
                </span>
              )}
              {option}
            </button>
          );
        })}
      </div>

      {showResult && explanation && (
        <div
          className="rounded-xl px-4 py-3 text-sm leading-relaxed"
          style={{
            background: isCorrect ? "#D4EDDA" : "#FFF3CD",
            border: `1px solid ${isCorrect ? "#28A745" : "#BD6809"}`,
            color: "#2F4731",
          }}
        >
          <strong>{isCorrect ? "✓ Correct! " : "✗ Not quite. "}</strong>
          {explanation}
        </div>
      )}
    </div>
  );
}
