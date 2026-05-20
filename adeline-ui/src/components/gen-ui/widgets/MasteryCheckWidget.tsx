"use client";

/**
 * MasteryCheckWidget
 *
 * Rendered when useChat receives a tool_call: render_quiz_widget.
 * Parses the block content into a QuizCard and reports the answer
 * back to /brain/genui/callback.
 *
 * Design: inherits PAPAYA/PARADISE/PALM palette exactly as used in
 * QuizCard.tsx and BlockWrapper.tsx — no new colors introduced.
 */

import { useState } from "react";
import { CheckCircle, XCircle, Brain } from "lucide-react";

interface MasteryCheckWidgetProps {
  blockId: string;
  lessonId: string;
  track: string;
  title: string;
  content: string;
  tags?: string[];
}

interface ParsedQuestion {
  question: string;
  options: string[];
  correctIndex: number;
  explanation: string | undefined;
}

/**
 * Parse the QUIZ block content written by the agent.
 * Expected loose format:
 *   Q: <question text>
 *   A) First option
 *   B) *Second option   ← asterisk marks correct answer
 *   C) Third option
 *   Explanation: The reason B is correct.
 *
 * Falls back gracefully if the format doesn't match.
 */
function parseQuizContent(content: string): ParsedQuestion {
  const lines = content
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  const questionLine = lines.find((l) => /^Q[:.]/i.test(l));
  const question = questionLine
    ? questionLine.replace(/^Q[:.]\s*/i, "")
    : lines[0] ?? "Reflect on what you just read.";

  const optionLines = lines.filter((l) => /^[A-D][).]/i.test(l));
  const options = optionLines.map((l) =>
    l.replace(/^[A-D][).]\s*\*?\s*/i, "").replace(/\*\s*$/, "").trim()
  );

  const correctIndex = optionLines.findIndex((l) => l.includes("*"));

  const explanationLine = lines.find((l) =>
    /^explanation[:\s]/i.test(l)
  );
  const explanation = explanationLine
    ? explanationLine.replace(/^explanation[:\s]*/i, "").trim()
    : undefined;

  return {
    question,
    options: options.length >= 2 ? options : ["I understand this", "I need to review"],
    correctIndex: correctIndex >= 0 ? correctIndex : 0,
    explanation,
  };
}

export function MasteryCheckWidget({
  blockId,
  lessonId,
  track,
  title,
  content,
  tags = [],
}: MasteryCheckWidgetProps) {
  const parsed = parseQuizContent(content);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [callbackSent, setCallbackSent] = useState(false);

  const isAnswered = selectedIndex !== null;
  const isCorrect = selectedIndex === parsed.correctIndex;

  const handleSelect = async (idx: number) => {
    if (isAnswered) return;
    setSelectedIndex(idx);

    if (!callbackSent) {
      setCallbackSent(true);
      try {
        await fetch("/brain/genui/callback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lesson_id: lessonId,
            component_type: "QUIZ",
            event: "onAnswer",
            block_id: blockId,
            track,
            state: { isCorrect: idx === parsed.correctIndex },
          }),
        });
      } catch {
        // Non-fatal — BKT update best-effort
      }
    }
  };

  return (
    <div className="rounded-2xl border-2 border-[#E7DAC3] bg-[#FFFEF7] p-5 space-y-4 my-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-[#2F4731]/10 flex items-center justify-center shrink-0">
          <Brain className="w-4 h-4 text-[#2F4731]" />
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#BD6809]">
            Mastery Check
          </p>
          {title && (
            <p className="text-sm font-bold text-[#2F4731] leading-tight">{title}</p>
          )}
        </div>
      </div>

      {/* Question */}
      <p className="text-sm font-semibold text-[#2F4731] leading-relaxed">
        {parsed.question}
      </p>

      {/* Options */}
      <div className="space-y-2">
        {parsed.options.map((option, idx) => {
          const isSelected = selectedIndex === idx;
          const isCorrectOption = idx === parsed.correctIndex;
          const showGreen = isAnswered && isCorrectOption;
          const showRed = isAnswered && isSelected && !isCorrect;

          return (
            <button
              key={idx}
              onClick={() => handleSelect(idx)}
              disabled={isAnswered}
              className="w-full text-left flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition-all disabled:cursor-default"
              style={{
                background: showGreen
                  ? "#D4EDDA"
                  : showRed
                  ? "#F8D7DA"
                  : "#FFFFFF",
                border: `1.5px solid ${
                  showGreen ? "#28A745" : showRed ? "#DC3545" : "#E7DAC3"
                }`,
                opacity: isAnswered && !isSelected && !isCorrectOption ? 0.5 : 1,
                fontWeight: isSelected ? 700 : 400,
                color: "#2F4731",
              }}
            >
              {showGreen && (
                <CheckCircle
                  size={16}
                  className="shrink-0"
                  style={{ color: "#28A745" }}
                />
              )}
              {showRed && (
                <XCircle
                  size={16}
                  className="shrink-0"
                  style={{ color: "#DC3545" }}
                />
              )}
              {!showGreen && !showRed && (
                <span
                  className="w-5 h-5 rounded-full border text-[10px] font-bold flex items-center justify-center shrink-0"
                  style={{ borderColor: "#E7DAC3", color: "#2F4731" }}
                >
                  {String.fromCharCode(65 + idx)}
                </span>
              )}
              <span>{option}</span>
            </button>
          );
        })}
      </div>

      {/* Explanation */}
      {isAnswered && parsed.explanation && (
        <div
          className="rounded-xl px-4 py-3 text-sm leading-relaxed"
          style={{
            background: isCorrect ? "#D4EDDA" : "#FDF6E9",
            border: `1px solid ${isCorrect ? "#28A745" : "#BD6809"}`,
            color: "#2F4731",
          }}
        >
          <strong>{isCorrect ? "✓ Correct! " : "Not quite — "}</strong>
          {parsed.explanation}
        </div>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-block px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#2F4731]/10 text-[#2F4731]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
