"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Lightbulb, ArrowRight, X } from "lucide-react";

export interface RelatedConcept {
  title: string;
  brief: string;
}

export interface CorrectiveOverlayProps {
  studentAnswer: string;
  correctAnswer: string;
  mistakeType: string;
  explanation: string;
  correctApproach: string;
  relatedConcepts?: RelatedConcept[];
  track?: string;
  onDismiss?: () => void;
  onRetry?: () => void;
}

export function CorrectiveOverlay({
  studentAnswer,
  correctAnswer,
  mistakeType,
  explanation,
  correctApproach,
  relatedConcepts = [],
  track,
  onDismiss,
  onRetry,
}: CorrectiveOverlayProps) {
  const [step, setStep] = useState<"mistake" | "approach" | "related">("mistake");

  const themeColor = track === "TRUTH_HISTORY" ? "#6B3A2A" : "#2F4731";
  const accentColor = track === "TRUTH_HISTORY" ? "#C27C4E" : "#8BAE6B";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="rounded-2xl overflow-hidden shadow-lg"
      style={{ border: `2px solid #EF444440`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div className="px-5 py-3 flex items-center justify-between bg-red-50">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-500" />
          <h3 className="font-semibold text-sm text-red-700">Let&apos;s Look at This Together</h3>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-gray-400 hover:text-gray-600">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Step navigation */}
      <div className="px-5 py-2 flex gap-1 border-b border-gray-100">
        {(["mistake", "approach", "related"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStep(s)}
            className="px-3 py-1 rounded-full text-[10px] font-medium transition-colors capitalize"
            style={{
              background: step === s ? `${themeColor}10` : "transparent",
              color: step === s ? themeColor : "#9CA3AF",
            }}
          >
            {s === "mistake" ? "What Happened" : s === "approach" ? "Better Approach" : "Related"}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {step === "mistake" && (
          <motion.div
            key="mistake"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            className="px-5 py-4 space-y-3"
          >
            <div className="flex gap-3">
              <div className="flex-1 p-3 rounded-lg bg-red-50 border border-red-100">
                <p className="text-[10px] font-medium text-red-500 mb-1">Your Answer</p>
                <p className="text-xs text-red-700">{studentAnswer}</p>
              </div>
              <div className="flex-1 p-3 rounded-lg bg-green-50 border border-green-100">
                <p className="text-[10px] font-medium text-green-500 mb-1">Expected</p>
                <p className="text-xs text-green-700">{correctAnswer}</p>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-amber-50">
              <p className="text-[10px] font-medium text-amber-600 mb-1">Mistake Type: {mistakeType}</p>
              <p className="text-xs text-amber-700 leading-relaxed">{explanation}</p>
            </div>
            <button
              onClick={() => setStep("approach")}
              className="flex items-center gap-1 text-xs font-medium"
              style={{ color: accentColor }}
            >
              See the better approach <ArrowRight size={12} />
            </button>
          </motion.div>
        )}

        {step === "approach" && (
          <motion.div
            key="approach"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            className="px-5 py-4"
          >
            <div className="flex items-start gap-2 p-4 rounded-xl" style={{ background: `${accentColor}08` }}>
              <Lightbulb size={16} style={{ color: accentColor }} className="shrink-0 mt-0.5" />
              <p className="text-sm text-gray-700 leading-relaxed">{correctApproach}</p>
            </div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="mt-4 w-full py-2.5 rounded-lg text-xs font-medium text-white"
                style={{ background: accentColor }}
              >
                Try Again
              </button>
            )}
          </motion.div>
        )}

        {step === "related" && (
          <motion.div
            key="related"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            className="px-5 py-4 space-y-2"
          >
            {relatedConcepts.length > 0 ? (
              relatedConcepts.map((concept) => (
                <div key={concept.title} className="p-3 rounded-lg border border-gray-100">
                  <p className="text-xs font-medium" style={{ color: themeColor }}>{concept.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{concept.brief}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-400 italic">No related concepts to show.</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
