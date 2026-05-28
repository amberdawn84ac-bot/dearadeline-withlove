"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, TrendingUp, TrendingDown, CheckCircle2, XCircle } from "lucide-react";
import { fireGenUICallback } from "@/lib/genui-callback";

export interface AdaptiveQuestion {
  id: string;
  difficulty: "easy" | "medium" | "hard" | "challenge";
  question: string;
  options: { label: string; isCorrect: boolean }[];
  explanation?: string;
  hint?: string;
}

export interface AdaptiveQuizProps {
  title: string;
  questions: AdaptiveQuestion[];
  startDifficulty?: "easy" | "medium" | "hard";
  track?: string;
  studentId?: string;
  lessonId?: string;
  blockId?: string;
  onComplete?: (state: { finalDifficulty: string; correct: number; total: number; timeMs: number }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  onStruggle?: (state: { wrongStreak: number; currentDifficulty: string }) => void;
}

const DIFFICULTY_ORDER = ["easy", "medium", "hard", "challenge"] as const;

export function AdaptiveQuiz({
  title,
  questions,
  startDifficulty = "medium",
  track,
  studentId,
  lessonId,
  blockId,
  onComplete,
  onStateChange,
  onStruggle,
}: AdaptiveQuizProps) {
  const [currentDifficulty, setCurrentDifficulty] = useState<typeof DIFFICULTY_ORDER[number]>(startDifficulty);
  const [answeredIds, setAnsweredIds] = useState<Set<string>>(new Set());
  const [correct, setCorrect] = useState(0);
  const [total, setTotal] = useState(0);
  const [streak, setStreak] = useState(0);
  const [wrongStreak, setWrongStreak] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [difficultyChange, setDifficultyChange] = useState<"up" | "down" | null>(null);
  const mountedAt = useRef(Date.now());

  const themeColor = track === "GOVERNMENT_ECONOMICS" ? "#1E3A5F" : "#2F4731";
  const accentColor = track === "GOVERNMENT_ECONOMICS" ? "#4A90D9" : "#8BAE6B";

  // Get next question at current difficulty
  const getNextQuestion = useCallback((): AdaptiveQuestion | null => {
    const available = questions.filter(
      (q) => q.difficulty === currentDifficulty && !answeredIds.has(q.id)
    );
    if (available.length > 0) return available[0];
    // Fallback: any unanswered
    const any = questions.filter((q) => !answeredIds.has(q.id));
    return any.length > 0 ? any[0] : null;
  }, [questions, currentDifficulty, answeredIds]);

  const currentQuestion = getNextQuestion();

  const adjustDifficulty = (wasCorrect: boolean) => {
    const idx = DIFFICULTY_ORDER.indexOf(currentDifficulty as typeof DIFFICULTY_ORDER[number]);

    if (wasCorrect) {
      setStreak((s) => s + 1);
      setWrongStreak(0);
      // Level up after 2 correct in a row
      if (streak + 1 >= 2 && idx < DIFFICULTY_ORDER.length - 1) {
        setCurrentDifficulty(DIFFICULTY_ORDER[idx + 1]);
        setStreak(0);
        setDifficultyChange("up");
        setTimeout(() => setDifficultyChange(null), 2000);
      }
    } else {
      setWrongStreak((w) => w + 1);
      setStreak(0);
      // Level down after 2 wrong in a row
      if (wrongStreak + 1 >= 2 && idx > 0) {
        setCurrentDifficulty(DIFFICULTY_ORDER[idx - 1]);
        setWrongStreak(0);
        setDifficultyChange("down");
        setTimeout(() => setDifficultyChange(null), 2000);
      }
      // Trigger struggle callback
      if (wrongStreak + 1 >= 3) {
        onStruggle?.({ wrongStreak: wrongStreak + 1, currentDifficulty });
        fireGenUICallback({ studentId, lessonId, componentType: "AdaptiveQuiz", event: "onStruggle", state: { wrongStreak: wrongStreak + 1, currentDifficulty }, blockId, track }).then(result => {
          if (result?.should_re_render) onStateChange?.({ _scaffold: { component: result.scaffold_component, props: result.scaffold_props } });
        });
      }
    }
  };

  const handleAnswer = (optionLabel: string, isCorrect: boolean) => {
    if (selectedAnswer) return;
    setSelectedAnswer(optionLabel);
    setTotal((t) => t + 1);
    if (isCorrect) setCorrect((c) => c + 1);
    setShowExplanation(true);
    adjustDifficulty(isCorrect);
    onStateChange?.({ correct: correct + (isCorrect ? 1 : 0), total: total + 1, currentDifficulty });
    fireGenUICallback({ studentId, lessonId, componentType: "AdaptiveQuiz", event: "onAnswer", state: { isCorrect, currentDifficulty }, blockId, track });
  };

  const nextQuestion = () => {
    if (!currentQuestion) return;
    setAnsweredIds((ids) => new Set([...ids, currentQuestion.id]));
    setSelectedAnswer(null);
    setShowExplanation(false);
    setShowHint(false);

    // Check if done (answered 8 questions or no more available)
    const remaining = questions.filter((q) => !answeredIds.has(q.id) && q.id !== currentQuestion.id);
    if (total >= 8 || remaining.length === 0) {
      setCompleted(true);
      onComplete?.({
        finalDifficulty: currentDifficulty,
        correct: correct,
        total: total,
        timeMs: Date.now() - mountedAt.current,
      });
      fireGenUICallback({ studentId, lessonId, componentType: "AdaptiveQuiz", event: "onComplete", state: { finalDifficulty: currentDifficulty, correct, total, timeMs: Date.now() - mountedAt.current }, blockId, track });
    }
  };

  const difficultyColors: Record<string, string> = {
    easy: "#22C55E",
    medium: "#F59E0B",
    hard: "#EF4444",
    challenge: "#8B5CF6",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div className="px-5 py-3 flex items-center justify-between" style={{ background: `${themeColor}08` }}>
        <div className="flex items-center gap-2">
          <Brain size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase"
            style={{ background: `${difficultyColors[currentDifficulty]}20`, color: difficultyColors[currentDifficulty] }}
          >
            {currentDifficulty}
          </span>
          {difficultyChange && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex items-center"
            >
              {difficultyChange === "up" ? (
                <TrendingUp size={14} className="text-green-500" />
              ) : (
                <TrendingDown size={14} className="text-orange-500" />
              )}
            </motion.span>
          )}
        </div>
      </div>

      {/* Score bar */}
      <div className="px-5 py-2 flex items-center gap-3 text-xs text-gray-500 border-b border-gray-100">
        <span>{correct}/{total} correct</span>
        <span>•</span>
        <span>Q{total + 1} of ~8</span>
      </div>

      {/* Current question */}
      {!completed && currentQuestion && (
        <AnimatePresence mode="wait">
          <motion.div
            key={currentQuestion.id}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            className="px-5 py-4"
          >
            <p className="text-sm font-medium text-gray-800 mb-4">{currentQuestion.question}</p>

            <div className="space-y-2">
              {currentQuestion.options.map((opt) => {
                const isSelected = selectedAnswer === opt.label;
                const showResult = selectedAnswer !== null;
                return (
                  <button
                    key={opt.label}
                    onClick={() => handleAnswer(opt.label, opt.isCorrect)}
                    disabled={!!selectedAnswer}
                    className="w-full text-left px-4 py-2.5 rounded-lg border text-xs transition-all disabled:cursor-default"
                    style={{
                      borderColor: showResult && isSelected
                        ? (opt.isCorrect ? "#22C55E" : "#EF4444")
                        : showResult && opt.isCorrect ? "#22C55E" : "#E5E7EB",
                      background: showResult && isSelected
                        ? (opt.isCorrect ? "#F0FDF4" : "#FEF2F2")
                        : showResult && opt.isCorrect ? "#F0FDF4" : "white",
                    }}
                  >
                    <span className="flex items-center gap-2">
                      {showResult && isSelected && (opt.isCorrect ? <CheckCircle2 size={12} className="text-green-500" /> : <XCircle size={12} className="text-red-500" />)}
                      {showResult && !isSelected && opt.isCorrect && <CheckCircle2 size={12} className="text-green-500" />}
                      {opt.label}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Hint */}
            {currentQuestion.hint && !showHint && !selectedAnswer && (
              <button
                onClick={() => setShowHint(true)}
                className="mt-3 text-xs underline"
                style={{ color: accentColor }}
              >
                Need a hint?
              </button>
            )}
            {showHint && currentQuestion.hint && (
              <p className="mt-2 px-3 py-2 rounded-lg bg-amber-50 text-xs text-amber-700">{currentQuestion.hint}</p>
            )}

            {/* Explanation + next */}
            {showExplanation && currentQuestion.explanation && (
              <p className="mt-3 px-3 py-2 rounded-lg bg-blue-50 text-xs text-blue-700">{currentQuestion.explanation}</p>
            )}
            {selectedAnswer && (
              <button
                onClick={nextQuestion}
                className="mt-3 px-4 py-2 rounded-lg text-xs font-medium text-white"
                style={{ background: accentColor }}
              >
                Next Question
              </button>
            )}
          </motion.div>
        </AnimatePresence>
      )}

      {/* No more questions */}
      {!completed && !currentQuestion && (
        <div className="px-5 py-4 text-center text-sm text-gray-500">
          No more questions at this level.
        </div>
      )}

      {/* Completed */}
      {completed && (
        <div className="px-5 py-6 text-center">
          <Brain size={28} style={{ color: accentColor }} className="mx-auto mb-2" />
          <p className="text-sm font-medium" style={{ color: themeColor }}>Quiz Complete!</p>
          <p className="text-xs text-gray-500 mt-1">
            {correct}/{total} correct • Final level: <span className="font-medium capitalize">{currentDifficulty}</span>
          </p>
        </div>
      )}
    </motion.div>
  );
}
