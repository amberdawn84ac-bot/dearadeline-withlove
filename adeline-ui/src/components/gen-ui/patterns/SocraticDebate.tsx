"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, ChevronDown, ChevronUp, Lightbulb } from "lucide-react";

export interface SocraticTurn {
  question: string;
  hint?: string;
  expectedThemes?: string[];
}

export interface SocraticDebateProps {
  thesis: string;
  turns: SocraticTurn[];
  track?: string;
  onComplete?: (responses: string[]) => void;
  onStateChange?: (state: Record<string, any>) => void;
}

type TurnState = "waiting" | "answered" | "skipped";

export function SocraticDebate({
  thesis,
  turns,
  track,
  onComplete,
  onStateChange,
}: SocraticDebateProps) {
  const [currentTurn, setCurrentTurn] = useState(0);
  const [responses, setResponses] = useState<string[]>([]);
  const [turnStates, setTurnStates] = useState<TurnState[]>(
    turns.map(() => "waiting")
  );
  const [draft, setDraft] = useState("");
  const [showHint, setShowHint] = useState(false);
  const [completed, setCompleted] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const themeColor = track === "TRUTH_HISTORY" ? "#6B3A2A" : "#2F4731";
  const accentColor = track === "TRUTH_HISTORY" ? "#C27C4E" : "#8BAE6B";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentTurn, completed]);

  const submit = () => {
    if (!draft.trim()) return;
    const newResponses = [...responses, draft.trim()];
    const newStates = [...turnStates];
    newStates[currentTurn] = "answered";

    setResponses(newResponses);
    setTurnStates(newStates);
    setDraft("");
    setShowHint(false);
    onStateChange?.({ currentTurn, responses: newResponses });

    if (currentTurn + 1 >= turns.length) {
      setCompleted(true);
      onComplete?.(newResponses);
    } else {
      setCurrentTurn(currentTurn + 1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}30`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div
        className="px-5 py-4"
        style={{ background: `${themeColor}10`, borderBottom: `1px solid ${themeColor}20` }}
      >
        <div className="flex items-center gap-2 mb-1">
          <span
            className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
            style={{ background: accentColor, color: "#fff" }}
          >
            Socratic Dialogue
          </span>
          <span className="text-[10px] text-[#9CA3AF]">
            {turns.length} question{turns.length !== 1 ? "s" : ""}
          </span>
        </div>
        <p className="text-sm font-bold leading-snug" style={{ color: themeColor }}>
          {thesis}
        </p>
      </div>

      {/* Conversation thread */}
      <div className="px-5 py-4 space-y-4 max-h-[420px] overflow-y-auto">
        {turns.map((turn, idx) => {
          const state = turnStates[idx];
          const response = responses[idx];
          const isActive = idx === currentTurn && !completed;
          const isPast = idx < currentTurn || completed;
          const isFuture = idx > currentTurn;

          if (isFuture) return null;

          return (
            <div key={idx} className="space-y-2">
              {/* Adeline's question */}
              <div className="flex gap-3">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
                  style={{ background: themeColor, color: "#fff" }}
                >
                  A
                </div>
                <div
                  className="rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed flex-1"
                  style={{ background: `${themeColor}10`, color: themeColor }}
                >
                  {turn.question}
                </div>
              </div>

              {/* Student's response (if answered) */}
              {isPast && response && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3 justify-end"
                >
                  <div
                    className="rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed max-w-[85%]"
                    style={{ background: accentColor + "22", color: "#374151", border: `1px solid ${accentColor}40` }}
                  >
                    {response}
                  </div>
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
                    style={{ background: accentColor, color: "#fff" }}
                  >
                    S
                  </div>
                </motion.div>
              )}

              {/* Active input area */}
              {isActive && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="pl-10 space-y-2"
                >
                  {/* Hint toggle */}
                  {turn.hint && (
                    <button
                      onClick={() => setShowHint(!showHint)}
                      className="flex items-center gap-1.5 text-xs font-medium transition-colors"
                      style={{ color: accentColor }}
                    >
                      <Lightbulb size={12} />
                      {showHint ? "Hide hint" : "Show hint"}
                      {showHint ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                  )}

                  <AnimatePresence>
                    {showHint && turn.hint && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-xs leading-relaxed rounded-xl px-3 py-2"
                        style={{
                          background: accentColor + "15",
                          border: `1px solid ${accentColor}30`,
                          color: "#6B7280",
                        }}
                      >
                        <strong style={{ color: accentColor }}>Hint:</strong> {turn.hint}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div className="flex gap-2">
                    <textarea
                      ref={textareaRef}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Share your thinking… (Cmd+Enter to submit)"
                      rows={3}
                      className="flex-1 rounded-xl px-3 py-2.5 text-sm resize-none focus:outline-none"
                      style={{
                        background: "#fff",
                        border: `1.5px solid ${themeColor}30`,
                        color: "#374151",
                      }}
                    />
                    <button
                      onClick={submit}
                      disabled={!draft.trim()}
                      className="self-end w-9 h-9 rounded-xl flex items-center justify-center transition-opacity disabled:opacity-30"
                      style={{ background: themeColor }}
                    >
                      <Send size={14} color="#fff" />
                    </button>
                  </div>

                  <p className="text-[10px] text-[#9CA3AF] pl-1">
                    Question {idx + 1} of {turns.length}
                  </p>
                </motion.div>
              )}
            </div>
          );
        })}

        {/* Completion state */}
        {completed && (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-2xl p-4 text-center"
            style={{ background: `${themeColor}08`, border: `1.5px solid ${themeColor}20` }}
          >
            <p className="text-sm font-bold" style={{ color: themeColor }}>
              Well reasoned.
            </p>
            <p className="text-xs text-[#6B7280] mt-1">
              You worked through {turns.length} question{turns.length !== 1 ? "s" : ""}.
              Adeline has recorded your thinking.
            </p>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
