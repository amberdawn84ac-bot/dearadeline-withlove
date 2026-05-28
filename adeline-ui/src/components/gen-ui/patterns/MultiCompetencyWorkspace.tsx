"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Layers, CheckCircle2, Circle } from "lucide-react";

export interface WorkspaceTask {
  id: string;
  label: string;
  competency: string;
  type: "text" | "number" | "choice";
  options?: string[];
  correctAnswer?: string;
  hint?: string;
}

export interface MultiCompetencyWorkspaceProps {
  title: string;
  scenario: string;
  tasks: WorkspaceTask[];
  competencies: string[];
  track?: string;
  onComplete?: (state: { completedTasks: number; totalTasks: number; timeMs: number; competencyScores: Record<string, number> }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

export function MultiCompetencyWorkspace({
  title,
  scenario,
  tasks,
  competencies,
  track,
  onComplete,
  onStateChange,
}: MultiCompetencyWorkspaceProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<Record<string, boolean>>({});
  const [completed, setCompleted] = useState(false);
  const mountedAt = useRef(Date.now());

  const themeColor = track === "CREATION_SCIENCE" ? "#2F4731" : "#6B3A2A";
  const accentColor = track === "CREATION_SCIENCE" ? "#8BAE6B" : "#C27C4E";

  const handleSubmitTask = (taskId: string) => {
    const task = tasks.find((t) => t.id === taskId);
    if (!task || !answers[taskId]) return;

    const isCorrect = task.correctAnswer
      ? answers[taskId].toLowerCase().trim() === task.correctAnswer.toLowerCase().trim()
      : true;

    setSubmitted((s) => new Set([...s, taskId]));
    setResults((r) => ({ ...r, [taskId]: isCorrect }));
    onStateChange?.({ answers, submitted: [...submitted, taskId], results: { ...results, [taskId]: isCorrect } });

    // Check if all tasks completed
    if (submitted.size + 1 >= tasks.length) {
      setCompleted(true);
      const competencyScores: Record<string, number> = {};
      competencies.forEach((c) => {
        const relatedTasks = tasks.filter((t) => t.competency === c);
        const correct = relatedTasks.filter((t) => results[t.id] || (t.id === taskId && isCorrect)).length;
        competencyScores[c] = relatedTasks.length > 0 ? correct / relatedTasks.length : 0;
      });
      onComplete?.({
        completedTasks: submitted.size + 1,
        totalTasks: tasks.length,
        timeMs: Date.now() - mountedAt.current,
        competencyScores,
      });
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
          <Layers size={16} style={{ color: accentColor }} />
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
        </div>
        <p className="text-xs text-gray-500 mt-1">Multi-Competency Problem</p>
      </div>

      {/* Scenario */}
      <div className="px-5 py-3 border-b border-gray-100">
        <p className="text-sm text-gray-700 leading-relaxed">{scenario}</p>
      </div>

      {/* Competency chips */}
      <div className="px-5 py-2 flex flex-wrap gap-1.5">
        {competencies.map((c) => (
          <span
            key={c}
            className="px-2 py-0.5 rounded-full text-[10px] font-medium"
            style={{ background: `${accentColor}15`, color: accentColor }}
          >
            {c}
          </span>
        ))}
      </div>

      {/* Tasks */}
      <div className="px-5 py-3 space-y-4">
        {tasks.map((task) => {
          const isSubmitted = submitted.has(task.id);
          const isCorrect = results[task.id];
          return (
            <div key={task.id} className="border border-gray-100 rounded-xl p-4">
              <div className="flex items-start gap-2 mb-2">
                {isSubmitted ? (
                  <CheckCircle2 size={14} className={isCorrect ? "text-green-500" : "text-red-500"} />
                ) : (
                  <Circle size={14} className="text-gray-300" />
                )}
                <div className="flex-1">
                  <p className="text-xs font-medium text-gray-700">{task.label}</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">{task.competency}</p>
                </div>
              </div>

              {!isSubmitted && (
                <div className="mt-2 flex gap-2">
                  {task.type === "choice" && task.options ? (
                    <div className="flex flex-wrap gap-1.5 flex-1">
                      {task.options.map((opt) => (
                        <button
                          key={opt}
                          onClick={() => setAnswers((a) => ({ ...a, [task.id]: opt }))}
                          className="px-3 py-1.5 rounded-lg text-xs border transition-colors"
                          style={{
                            borderColor: answers[task.id] === opt ? accentColor : "#E5E7EB",
                            background: answers[task.id] === opt ? `${accentColor}10` : "white",
                          }}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <input
                      type={task.type === "number" ? "number" : "text"}
                      value={answers[task.id] || ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [task.id]: e.target.value }))}
                      placeholder="Your answer…"
                      className="flex-1 px-3 py-1.5 rounded-lg border border-gray-200 text-xs"
                    />
                  )}
                  <button
                    onClick={() => handleSubmitTask(task.id)}
                    disabled={!answers[task.id]}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium text-white disabled:opacity-40"
                    style={{ background: accentColor }}
                  >
                    Submit
                  </button>
                </div>
              )}

              {isSubmitted && !isCorrect && task.hint && (
                <p className="mt-2 text-xs text-amber-600 italic">{task.hint}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Completed */}
      {completed && (
        <div className="px-5 pb-4 text-center">
          <p className="text-sm font-medium" style={{ color: themeColor }}>Workspace Complete!</p>
          <p className="text-xs text-gray-500 mt-1">
            {Object.values(results).filter(Boolean).length}/{tasks.length} correct
          </p>
        </div>
      )}
    </motion.div>
  );
}
