"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface PeerTutoringCardProps {
  conceptTitle: string;
  conceptTrack: string;
  difficulty: "EMERGING" | "DEVELOPING" | "EXPANDING" | "MASTERING";
  requestingStudentId?: string;
  state?: Record<string, any>;
  onStateChange?: (newState: Record<string, any>) => void;
}

const DIFFICULTY_LABELS: Record<string, string> = {
  EMERGING:   "K–2",
  DEVELOPING: "3–5",
  EXPANDING:  "6–8",
  MASTERING:  "9–12",
};

const TRACK_COLORS: Record<string, string> = {
  CREATION_SCIENCE:    "#BD6809",
  HEALTH_NATUROPATHY:  "#9A3F4A",
  HOMESTEADING:        "#BD6809",
  GOVERNMENT_ECONOMICS:"#3D1419",
  JUSTICE_CHANGEMAKING:"#9A3F4A",
  DISCIPLESHIP:        "#3D1419",
  TRUTH_HISTORY:       "#9A3F4A",
  ENGLISH_LITERATURE:  "#BD6809",
  APPLIED_MATHEMATICS: "#9A3F4A",
  CREATIVE_ECONOMY:    "#BD6809",
};

export function PeerTutoringCard({
  conceptTitle,
  conceptTrack,
  difficulty,
  requestingStudentId,
  state = {},
  onStateChange,
}: PeerTutoringCardProps) {
  const [requested, setRequested] = useState(state.requested ?? false);
  const [matched, setMatched] = useState(state.matched ?? false);

  const accentColor = TRACK_COLORS[conceptTrack] ?? "#BD6809";
  const gradeRange = DIFFICULTY_LABELS[difficulty] ?? "any grade";

  function handleRequest() {
    setRequested(true);
    // Simulate async match — in production this calls /api/peer-tutor/request
    setTimeout(() => {
      setMatched(true);
      onStateChange?.({ requested: true, matched: true });
    }, 1800);
    onStateChange?.({ requested: true, matched: false });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl overflow-hidden"
      style={{
        border: `1.5px solid ${accentColor}30`,
        background: `linear-gradient(135deg, ${accentColor}08, ${accentColor}04)`,
      }}
    >
      {/* Header */}
      <div
        className="px-5 py-3 flex items-center gap-3"
        style={{ background: `${accentColor}14` }}
      >
        <span className="text-lg">🤝</span>
        <div>
          <p className="text-xs font-semibold tracking-widest uppercase opacity-60">
            Peer Tutoring
          </p>
          <p className="text-sm font-bold leading-tight" style={{ color: accentColor }}>
            {conceptTitle}
          </p>
        </div>
        <span
          className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: `${accentColor}20`, color: accentColor }}
        >
          Grades {gradeRange}
        </span>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-4">
        <AnimatePresence mode="wait">
          {!requested && (
            <motion.div
              key="pre-request"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <p className="text-sm text-gray-700 leading-relaxed">
                A student who recently mastered{" "}
                <strong>{conceptTitle}</strong> is available to explain it to
                you in their own words. Peer explanations often land differently
                than a lesson — you might catch something that clicked for them.
              </p>
              <p className="text-xs text-gray-500">
                Matching finds a student who just completed this concept with a
                mastery score above 85%.
              </p>
              <button
                onClick={handleRequest}
                className="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-90 active:opacity-80"
                style={{ background: accentColor }}
              >
                Request a Study Partner
              </button>
            </motion.div>
          )}

          {requested && !matched && (
            <motion.div
              key="searching"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3 py-4"
            >
              <div
                className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: `${accentColor}40`, borderTopColor: accentColor }}
              />
              <p className="text-sm text-gray-600 text-center">
                Finding a student who mastered {conceptTitle}…
              </p>
            </motion.div>
          )}

          {matched && (
            <motion.div
              key="matched"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-3"
            >
              <div
                className="flex items-center gap-3 p-3 rounded-xl"
                style={{ background: `${accentColor}10` }}
              >
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm"
                  style={{ background: accentColor }}
                >
                  P
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">Peer Tutor Found</p>
                  <p className="text-xs text-gray-500">
                    Mastery score: <strong style={{ color: accentColor }}>91%</strong> on{" "}
                    {conceptTitle}
                  </p>
                </div>
                <span className="ml-auto text-green-600 text-xs font-semibold">● Available</span>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                Your study partner is ready. Start a session — they'll walk you through the
                concept in their own words, and you can ask questions as you go.
              </p>
              <button
                className="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-90"
                style={{ background: accentColor }}
              >
                Start Session →
              </button>
              <p className="text-center text-xs text-gray-400">
                Session data is private. No names shared without consent.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
