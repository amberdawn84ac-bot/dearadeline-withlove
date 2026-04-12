"use client";

/**
 * AgentThinkingState — Transparent AI "thinking" visualization.
 *
 * Cycles through agent activity messages while waiting for lesson generation,
 * giving students and parents insight into Adeline's multi-agent orchestration.
 * Uses framer-motion for smooth, physics-based transitions.
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, BookOpen, Search, Sparkles, GraduationCap, Lightbulb } from "lucide-react";

// ── Thinking step configuration ────────────────────────────────────────────────

interface ThinkingStep {
  id: string;
  icon: React.ReactNode;
  message: string;
  subtext?: string;
  color: string;
}

const THINKING_STEPS: ThinkingStep[] = [
  {
    id: "orchestrator",
    icon: <Brain className="w-5 h-5" />,
    message: "Waking up the Orchestrator…",
    subtext: "Analyzing your request",
    color: "#BD6809",
  },
  {
    id: "historian",
    icon: <BookOpen className="w-5 h-5" />,
    message: "Consulting the Historian Agent…",
    subtext: "Searching primary sources",
    color: "#9A3F4A",
  },
  {
    id: "witness",
    icon: <Search className="w-5 h-5" />,
    message: "Running Witness Protocol…",
    subtext: "Verifying source authenticity",
    color: "#166534",
  },
  {
    id: "pedagogy",
    icon: <GraduationCap className="w-5 h-5" />,
    message: "Adapting to your learning level…",
    subtext: "Calibrating vocabulary & complexity",
    color: "#1D4ED8",
  },
  {
    id: "zpd",
    icon: <Lightbulb className="w-5 h-5" />,
    message: "Finding your Zone of Proximal Development…",
    subtext: "Balancing challenge & support",
    color: "#6B21A8",
  },
  {
    id: "crafting",
    icon: <Sparkles className="w-5 h-5" />,
    message: "Crafting your lesson…",
    subtext: "Weaving narrative & evidence",
    color: "#2F4731",
  },
];

// ── Component props ────────────────────────────────────────────────────────────

interface AgentThinkingStateProps {
  /** Whether the thinking animation is active */
  isActive: boolean;
  /** Optional: custom steps to cycle through */
  steps?: ThinkingStep[];
  /** Interval between step changes in ms (default: 2500) */
  intervalMs?: number;
  /** Optional: compact mode for inline use */
  compact?: boolean;
}

// ── AgentThinkingState component ───────────────────────────────────────────────

export function AgentThinkingState({
  isActive,
  steps = THINKING_STEPS,
  intervalMs = 2500,
  compact = false,
}: AgentThinkingStateProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Cycle through steps while active
  useEffect(() => {
    if (!isActive) {
      setCurrentIndex(0);
      return;
    }

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % steps.length);
    }, intervalMs);

    return () => clearInterval(interval);
  }, [isActive, steps.length, intervalMs]);

  if (!isActive) return null;

  const currentStep = steps[currentIndex];

  // ── Compact mode (inline) ────────────────────────────────────────────────────
  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep.id}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="flex items-center gap-2"
          >
            <motion.span
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
              style={{ color: currentStep.color }}
            >
              {currentStep.icon}
            </motion.span>
            <span className="text-sm text-[#2F4731]/70 italic">
              {currentStep.message}
            </span>
          </motion.div>
        </AnimatePresence>
      </div>
    );
  }

  // ── Full mode (card) ─────────────────────────────────────────────────────────
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="flex flex-col items-center justify-center py-12 px-6"
    >
      {/* Animated icon container */}
      <motion.div
        className="relative mb-6"
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        {/* Pulsing ring */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{ background: `${currentStep.color}20` }}
          animate={{ scale: [1, 1.4, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeOut" }}
        />
        
        {/* Icon circle */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep.id}
            initial={{ opacity: 0, rotate: -180, scale: 0.5 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: 180, scale: 0.5 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            className="relative w-16 h-16 rounded-full flex items-center justify-center"
            style={{ 
              background: `linear-gradient(135deg, ${currentStep.color}15, ${currentStep.color}30)`,
              border: `2px solid ${currentStep.color}40`,
            }}
          >
            <span style={{ color: currentStep.color }}>
              {currentStep.icon}
            </span>
          </motion.div>
        </AnimatePresence>
      </motion.div>

      {/* Message text */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="text-center"
        >
          <p
            className="text-lg font-semibold mb-1"
            style={{ color: currentStep.color, fontFamily: "var(--font-kalam), cursive" }}
          >
            {currentStep.message}
          </p>
          {currentStep.subtext && (
            <p className="text-sm text-[#2F4731]/50 italic">
              {currentStep.subtext}
            </p>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Progress dots */}
      <div className="flex gap-2 mt-6">
        {steps.map((step, index) => (
          <motion.div
            key={step.id}
            className="w-2 h-2 rounded-full"
            animate={{
              scale: index === currentIndex ? 1.3 : 1,
              background: index === currentIndex ? currentStep.color : "#E7DAC3",
            }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
          />
        ))}
      </div>
    </motion.div>
  );
}

// ── Export default steps for customization ─────────────────────────────────────

export { THINKING_STEPS };
export type { ThinkingStep };
