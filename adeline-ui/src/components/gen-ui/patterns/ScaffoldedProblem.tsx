"use client";

/**
 * ScaffoldedProblem — Step-by-step problem with hint reveals and adaptive difficulty.
 * Used in GENUI_ASSEMBLY blocks for mastery gap remediation.
 */

import { useState } from "react";
import { Lightbulb, CheckCircle, XCircle } from "lucide-react";

interface ScaffoldedProblemProps {
  state: Record<string, any>;
  onStateChange: (newState: Record<string, any>) => void;
  callbacks?: string[];
  // Component-specific props
  question: string;
  steps: Array<{
    instruction: string;
    hint?: string;
    answer?: string;
  }>;
  difficulty?: "easy" | "medium" | "hard";
}

export function ScaffoldedProblem({
  state,
  onStateChange,
  callbacks = [],
  question,
  steps,
  difficulty = "medium",
}: ScaffoldedProblemProps) {
  const [currentStep, setCurrentStep] = useState(state.currentStep || 0);
  const [hintsUsed, setHintsUsed] = useState(state.hintsUsed || 0);
  const [showHint, setShowHint] = useState(false);
  const [userAnswer, setUserAnswer] = useState("");
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

  const handleNextStep = () => {
    if (currentStep < steps.length - 1) {
      const newStep = currentStep + 1;
      setCurrentStep(newStep);
      setShowHint(false);
      setUserAnswer("");
      setIsCorrect(null);
      onStateChange({ ...state, currentStep: newStep, hintsUsed });
    }
  };

  const handleHint = () => {
    if (!showHint) {
      setHintsUsed(hintsUsed + 1);
      setShowHint(true);
      onStateChange({ ...state, currentStep, hintsUsed: hintsUsed + 1 });
      if (callbacks.includes("onHint")) {
        // TODO: Call backend to log hint usage
        console.log("[ScaffoldedProblem] Hint used");
      }
    }
  };

  const handleCheckAnswer = () => {
    const currentStepData = steps[currentStep];
    const correct = currentStepData.answer
      ? userAnswer.toLowerCase().trim() === currentStepData.answer.toLowerCase().trim()
      : true;
    setIsCorrect(correct);
    onStateChange({ ...state, currentStep, hintsUsed, lastAnswerCorrect: correct });
    if (callbacks.includes("onAnswer")) {
      // TODO: Call backend to update BKT
      console.log("[ScaffoldedProblem] Answer checked:", correct);
    }
  };

  const currentStepData = steps[currentStep];

  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: "#FFFEF7", border: "2px solid #7C3AED40" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🧩</span>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-[#7C3AED] text-white">
          Scaffolded Problem
        </span>
        {difficulty && (
          <span className="text-xs text-[#7C3AED]/70 ml-auto">
            {difficulty}
          </span>
        )}
      </div>

      <p className="text-sm font-bold text-[#2F4731]">{question}</p>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-[#374151]/60">
          <span>Step {currentStep + 1} of {steps.length}</span>
          <span>Hints used: {hintsUsed}</span>
        </div>

        <div className="rounded-lg p-4 bg-white border border-[#E7DAC3]">
          <p className="text-sm text-[#2F4731] leading-relaxed">
            {currentStepData.instruction}
          </p>

          {currentStepData.hint && (
            <button
              onClick={handleHint}
              className="mt-3 flex items-center gap-2 text-xs text-[#7C3AED] hover:text-[#6D28D9] transition-colors"
            >
              <Lightbulb size={14} />
              {showHint ? "Hide hint" : "Show hint"}
            </button>
          )}

          {showHint && currentStepData.hint && (
            <div className="mt-2 p-3 rounded-lg bg-[#F3E8FF] border border-[#7C3AED]/20">
              <p className="text-xs text-[#6B21A8] italic">{currentStepData.hint}</p>
            </div>
          )}

          {currentStepData.answer && (
            <div className="mt-3 space-y-2">
              <input
                type="text"
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                placeholder="Your answer..."
                className="w-full px-3 py-2 text-sm border border-[#E7DAC3] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#7C3AED]"
                disabled={isCorrect !== null}
              />
              {isCorrect !== null && (
                <div className="flex items-center gap-2 text-xs">
                  {isCorrect ? (
                    <>
                      <CheckCircle size={14} className="text-green-600" />
                      <span className="text-green-600">Correct!</span>
                    </>
                  ) : (
                    <>
                      <XCircle size={14} className="text-red-600" />
                      <span className="text-red-600">Not quite. Try again or use a hint.</span>
                    </>
                  )}
                </div>
              )}
              <button
                onClick={handleCheckAnswer}
                disabled={isCorrect !== null || !userAnswer.trim()}
                className="px-4 py-2 text-xs font-semibold bg-[#7C3AED] text-white rounded-lg hover:bg-[#6D28D9] disabled:opacity-40 transition-colors"
              >
                Check Answer
              </button>
            </div>
          )}
        </div>
      </div>

      {currentStep < steps.length - 1 && isCorrect && (
        <button
          onClick={handleNextStep}
          className="w-full px-4 py-2 text-sm font-semibold bg-[#2F4731] text-white rounded-lg hover:bg-[#1E3A2F] transition-colors"
        >
          Next Step →
        </button>
      )}

      {currentStep === steps.length - 1 && isCorrect && callbacks.includes("onComplete") && (
        <div className="p-3 rounded-lg bg-[#D4EDDA] border border-[#28A745]">
          <p className="text-xs text-[#155724] font-semibold">
            ✓ Problem completed! Great work.
          </p>
        </div>
      )}
    </div>
  );
}
