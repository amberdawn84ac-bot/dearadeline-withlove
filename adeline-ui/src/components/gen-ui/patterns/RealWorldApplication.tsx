"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Globe, ChevronRight, CheckCircle2, Lightbulb } from "lucide-react";
import { fireGenUICallback } from "@/lib/genui-callback";

export interface ScenarioStep {
  id: string;
  prompt: string;
  options?: { label: string; isCorrect: boolean; feedback: string }[];
  freeResponse?: boolean;
}

export interface RealWorldApplicationProps {
  title: string;
  scenario: string;
  steps: ScenarioStep[];
  context?: string;
  track?: string;
  studentId?: string;
  lessonId?: string;
  blockId?: string;
  onComplete?: (state: { correctSteps: number; totalSteps: number; timeMs: number }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

export function RealWorldApplication({
  title,
  scenario,
  steps,
  context,
  track,
  studentId,
  lessonId,
  blockId,
  onComplete,
  onStateChange,
}: RealWorldApplicationProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [correctCount, setCorrectCount] = useState(0);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [freeText, setFreeText] = useState("");
  const mountedAt = useRef(Date.now());

  const themeColor = track === "HOMESTEADING" ? "#5C4033" : "#2F4731";
  const accentColor = track === "HOMESTEADING" ? "#A0785A" : "#8BAE6B";

  const step = steps[currentStep];

  const handleChoice = (optionLabel: string, isCorrect: boolean, fb: string) => {
    setResponses((r) => ({ ...r, [step.id]: optionLabel }));
    setFeedback(fb);
    if (isCorrect) setCorrectCount((c) => c + 1);
    onStateChange?.({ currentStep, responses: { ...responses, [step.id]: optionLabel }, correctCount });
    fireGenUICallback({ studentId, lessonId, componentType: "RealWorldApplication", event: "onAnswer", state: { isCorrect, step: step.id, optionLabel }, blockId, track });
  };

  const handleFreeSubmit = () => {
    if (!freeText.trim()) return;
    setResponses((r) => ({ ...r, [step.id]: freeText }));
    setFreeText("");
    advance();
  };

  const advance = () => {
    setFeedback(null);
    if (currentStep + 1 >= steps.length) {
      setCompleted(true);
      onComplete?.({ correctSteps: correctCount, totalSteps: steps.length, timeMs: Date.now() - mountedAt.current });
      fireGenUICallback({ studentId, lessonId, componentType: "RealWorldApplication", event: "onComplete", state: { correctSteps: correctCount, totalSteps: steps.length, timeMs: Date.now() - mountedAt.current }, blockId, track });
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div className="px-5 py-3" style={{ background: `${themeColor}08` }}>
        <div className="flex items-center gap-2">
          <Globe size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
        </div>
        <p className="text-xs text-gray-500 mt-1">Real-World Application</p>
      </div>

      {/* Scenario description */}
      <div className="px-5 py-3 border-b border-gray-100">
        <p className="text-sm text-gray-700 leading-relaxed">{scenario}</p>
        {context && (
          <div className="mt-2 flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50">
            <Lightbulb size={14} className="text-amber-600 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-700">{context}</p>
          </div>
        )}
      </div>

      {/* Progress */}
      <div className="px-5 py-2 flex items-center gap-2">
        {steps.map((_, i) => (
          <div
            key={i}
            className="h-1.5 flex-1 rounded-full transition-colors"
            style={{
              background: i < currentStep ? accentColor : i === currentStep ? `${accentColor}60` : "#E5E7EB",
            }}
          />
        ))}
      </div>

      {/* Current step */}
      {!completed && step && (
        <AnimatePresence mode="wait">
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="px-5 py-4"
          >
            <p className="text-sm font-medium text-gray-800 mb-3">{step.prompt}</p>

            {/* Multiple choice */}
            {step.options && (
              <div className="space-y-2">
                {step.options.map((opt) => (
                  <button
                    key={opt.label}
                    onClick={() => handleChoice(opt.label, opt.isCorrect, opt.feedback)}
                    disabled={!!responses[step.id]}
                    className="w-full text-left px-4 py-2.5 rounded-lg border text-xs transition-colors disabled:opacity-60"
                    style={{
                      borderColor: responses[step.id] === opt.label
                        ? (opt.isCorrect ? "#22C55E" : "#EF4444")
                        : "#E5E7EB",
                      background: responses[step.id] === opt.label
                        ? (opt.isCorrect ? "#F0FDF4" : "#FEF2F2")
                        : "white",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}

            {/* Free response */}
            {step.freeResponse && !responses[step.id] && (
              <div className="flex gap-2">
                <textarea
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  placeholder="Type your answer…"
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-xs resize-none"
                  rows={3}
                />
                <button
                  onClick={handleFreeSubmit}
                  className="px-3 py-2 rounded-lg text-xs font-medium text-white self-end"
                  style={{ background: accentColor }}
                >
                  Submit
                </button>
              </div>
            )}

            {/* Feedback */}
            {feedback && (
              <div className="mt-3 px-4 py-2 rounded-lg bg-blue-50 text-xs text-blue-700">
                {feedback}
              </div>
            )}

            {/* Next button */}
            {responses[step.id] && !step.freeResponse && (
              <button
                onClick={advance}
                className="mt-3 flex items-center gap-1 px-4 py-2 rounded-lg text-xs font-medium text-white"
                style={{ background: accentColor }}
              >
                Next <ChevronRight size={12} />
              </button>
            )}
          </motion.div>
        </AnimatePresence>
      )}

      {/* Completed */}
      {completed && (
        <div className="px-5 py-6 text-center">
          <CheckCircle2 size={32} style={{ color: accentColor }} className="mx-auto mb-2" />
          <p className="text-sm font-medium" style={{ color: themeColor }}>Scenario Complete!</p>
          <p className="text-xs text-gray-500 mt-1">
            {correctCount}/{steps.length} decisions correct
          </p>
        </div>
      )}
    </motion.div>
  );
}
