"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, Sparkles } from "lucide-react";
import { fireGenUICallback } from "@/lib/genui-callback";

export interface StealthScenario {
  id: string;
  narrative: string;
  choices: { id: string; label: string; mastery_signal: number }[];
  followUp?: string;
}

export interface StealthAssessmentProps {
  title: string;
  intro: string;
  scenarios: StealthScenario[];
  track?: string;
  studentId?: string;
  lessonId?: string;
  blockId?: string;
  onComplete?: (state: { inferredMastery: number; choices: string[]; timeMs: number }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

export function StealthAssessment({
  title,
  intro,
  scenarios,
  track,
  studentId,
  lessonId,
  blockId,
  onComplete,
  onStateChange,
}: StealthAssessmentProps) {
  const [currentScenario, setCurrentScenario] = useState(0);
  const [choices, setChoices] = useState<string[]>([]);
  const [masterySignals, setMasterySignals] = useState<number[]>([]);
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [completed, setCompleted] = useState(false);
  const mountedAt = useRef(Date.now());

  const themeColor = track === "DISCIPLESHIP" ? "#3D2B1F" : "#2F4731";
  const accentColor = track === "DISCIPLESHIP" ? "#9B7B5E" : "#8BAE6B";

  const scenario = scenarios[currentScenario];

  useEffect(() => {
    onStateChange?.({ currentScenario, choices, inferredMastery: averageMastery() });
  }, [currentScenario, choices]);

  const averageMastery = () => {
    if (masterySignals.length === 0) return 0;
    return masterySignals.reduce((a, b) => a + b, 0) / masterySignals.length;
  };

  const handleChoice = (choiceId: string, signal: number) => {
    const updatedChoices = [...choices, choiceId];
    const updatedSignals = [...masterySignals, signal];
    setChoices(updatedChoices);
    setMasterySignals(updatedSignals);

    if (scenario.followUp) {
      setShowFollowUp(true);
    } else {
      advance(updatedChoices, updatedSignals);
    }
  };

  const advance = (updatedChoices?: string[], updatedSignals?: number[]) => {
    setShowFollowUp(false);
    const ch = updatedChoices || choices;
    const sig = updatedSignals || masterySignals;

    if (currentScenario + 1 >= scenarios.length) {
      setCompleted(true);
      const inferredMastery = sig.reduce((a, b) => a + b, 0) / sig.length;
      onComplete?.({ inferredMastery, choices: ch, timeMs: Date.now() - mountedAt.current });
      fireGenUICallback({ studentId, lessonId, componentType: "StealthAssessment", event: "onAnswer", state: { isCorrect: inferredMastery > 0.5, inferredMastery }, blockId, track });
    } else {
      setCurrentScenario(currentScenario + 1);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header — deliberately does NOT say "assessment" */}
      <div className="px-5 py-3" style={{ background: `${themeColor}08` }}>
        <div className="flex items-center gap-2">
          <Sparkles size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
        </div>
        <p className="text-xs text-gray-500 mt-1">Interactive Scenario</p>
      </div>

      {/* Intro */}
      {currentScenario === 0 && !completed && (
        <p className="px-5 py-3 text-sm text-gray-600 border-b border-gray-100 leading-relaxed">{intro}</p>
      )}

      {/* Progress dots — subtle, no "question X of Y" */}
      <div className="px-5 py-2 flex items-center gap-1.5">
        {scenarios.map((_, i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full transition-colors"
            style={{
              background: i < currentScenario ? accentColor : i === currentScenario ? `${accentColor}80` : "#E5E7EB",
            }}
          />
        ))}
      </div>

      {/* Current scenario */}
      {!completed && scenario && (
        <AnimatePresence mode="wait">
          <motion.div
            key={scenario.id}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            className="px-5 py-4"
          >
            <p className="text-sm text-gray-800 leading-relaxed mb-4">{scenario.narrative}</p>

            {!showFollowUp && (
              <div className="space-y-2">
                {scenario.choices.map((choice) => (
                  <button
                    key={choice.id}
                    onClick={() => handleChoice(choice.id, choice.mastery_signal)}
                    className="w-full text-left px-4 py-3 rounded-xl border border-gray-200 text-sm hover:border-gray-300 transition-all hover:shadow-sm"
                    style={{ background: "white" }}
                  >
                    {choice.label}
                  </button>
                ))}
              </div>
            )}

            {showFollowUp && scenario.followUp && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-3"
              >
                <p className="text-sm text-gray-600 italic">{scenario.followUp}</p>
                <button
                  onClick={() => advance()}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-white"
                  style={{ background: accentColor }}
                >
                  Continue
                </button>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      )}

      {/* Completion — no score shown (stealth!) */}
      {completed && (
        <div className="px-5 py-6 text-center">
          <Sparkles size={28} style={{ color: accentColor }} className="mx-auto mb-2" />
          <p className="text-sm font-medium" style={{ color: themeColor }}>Great exploration!</p>
          <p className="text-xs text-gray-500 mt-1">Your choices help Adeline understand how to teach you best.</p>
        </div>
      )}
    </motion.div>
  );
}
