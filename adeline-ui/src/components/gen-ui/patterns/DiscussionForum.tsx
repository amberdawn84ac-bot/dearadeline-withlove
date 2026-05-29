"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface DiscussionResponse {
  id: string;
  author: string;
  text: string;
  grade: string;
  upvotes: number;
}

interface DiscussionForumProps {
  prompt: string;
  conceptTitle: string;
  track: string;
  targetGrade?: string;
  state?: Record<string, any>;
  onStateChange?: (newState: Record<string, any>) => void;
}

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

// Seeded example responses shown before the student posts — make the forum
// feel alive. In production these come from the /api/discussion endpoint.
const SEED_RESPONSES: DiscussionResponse[] = [
  {
    id: "seed-1",
    author: "Student A",
    text: "What surprised me most was how this connects directly to things we do every day without thinking about it.",
    grade: "7th",
    upvotes: 4,
  },
  {
    id: "seed-2",
    author: "Student B",
    text: "I'd never thought about the bigger picture before. Once you see it, you can't unsee it.",
    grade: "9th",
    upvotes: 7,
  },
];

export function DiscussionForum({
  prompt,
  conceptTitle,
  track,
  targetGrade,
  state = {},
  onStateChange,
}: DiscussionForumProps) {
  const [response, setResponse] = useState(state.draftResponse ?? "");
  const [posted, setPosted] = useState(state.posted ?? false);
  const [upvoted, setUpvoted] = useState<Set<string>>(new Set(state.upvoted ?? []));

  const accentColor = TRACK_COLORS[track] ?? "#BD6809";

  function handlePost() {
    if (!response.trim()) return;
    setPosted(true);
    onStateChange?.({ draftResponse: response, posted: true, upvoted: [...upvoted] });
  }

  function handleUpvote(id: string) {
    setUpvoted((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      onStateChange?.({ draftResponse: response, posted, upvoted: [...next] });
      return next;
    });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl overflow-hidden"
      style={{
        border: `1.5px solid ${accentColor}30`,
        background: `linear-gradient(135deg, ${accentColor}06, ${accentColor}02)`,
      }}
    >
      {/* Header */}
      <div
        className="px-5 py-3 flex items-center gap-3"
        style={{ background: `${accentColor}14` }}
      >
        <span className="text-lg">💬</span>
        <div>
          <p className="text-xs font-semibold tracking-widest uppercase opacity-60">
            Discussion
          </p>
          <p className="text-sm font-bold leading-tight" style={{ color: accentColor }}>
            {conceptTitle}
          </p>
        </div>
        {targetGrade && (
          <span
            className="ml-auto text-xs px-2 py-0.5 rounded-full font-medium"
            style={{ background: `${accentColor}20`, color: accentColor }}
          >
            Grade {targetGrade}
          </span>
        )}
      </div>

      {/* Prompt */}
      <div className="px-5 pt-4 pb-2">
        <p className="text-sm font-semibold text-gray-800 leading-relaxed">{prompt}</p>
      </div>

      {/* Existing responses */}
      <div className="px-5 pb-3 space-y-3">
        <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">
          What others said
        </p>
        {SEED_RESPONSES.map((r) => (
          <div
            key={r.id}
            className="p-3 rounded-xl text-sm"
            style={{ background: `${accentColor}08`, border: `1px solid ${accentColor}18` }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-xs" style={{ color: accentColor }}>
                {r.author} · {r.grade}
              </span>
              <button
                onClick={() => handleUpvote(r.id)}
                className="text-xs flex items-center gap-1 transition-opacity hover:opacity-80"
                style={{ color: upvoted.has(r.id) ? accentColor : "#9CA3AF" }}
              >
                ▲{" "}
                {r.upvotes + (upvoted.has(r.id) ? 1 : 0)}
              </button>
            </div>
            <p className="text-gray-700 leading-relaxed">{r.text}</p>
          </div>
        ))}

        {/* Student's own post (after posting) */}
        <AnimatePresence>
          {posted && (
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-3 rounded-xl text-sm"
              style={{ background: `${accentColor}15`, border: `1.5px solid ${accentColor}40` }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-xs" style={{ color: accentColor }}>
                  You · just now
                </span>
                <span className="text-xs text-gray-400">Posted ✓</span>
              </div>
              <p className="text-gray-800 leading-relaxed">{response}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input area */}
      {!posted && (
        <div className="px-5 pb-5 space-y-2">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">
            Your response
          </p>
          <textarea
            value={response}
            onChange={(e) => {
              setResponse(e.target.value);
              onStateChange?.({ draftResponse: e.target.value, posted, upvoted: [...upvoted] });
            }}
            placeholder="Write your thoughts — there's no single right answer here."
            rows={3}
            className="w-full rounded-xl px-4 py-3 text-sm resize-none outline-none transition-shadow"
            style={{
              border: `1.5px solid ${accentColor}30`,
              background: "white",
              boxShadow: "none",
            }}
            onFocus={(e) => {
              e.target.style.boxShadow = `0 0 0 2px ${accentColor}40`;
            }}
            onBlur={(e) => {
              e.target.style.boxShadow = "none";
            }}
          />
          <button
            onClick={handlePost}
            disabled={!response.trim()}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity disabled:opacity-40"
            style={{ background: accentColor }}
          >
            Post to Discussion
          </button>
          <p className="text-center text-xs text-gray-400">
            Responses are visible to other students in this co-op group.
          </p>
        </div>
      )}

      {posted && (
        <div className="px-5 pb-5">
          <p className="text-center text-xs text-gray-500">
            Your response is live. Check back to see if others reply.
          </p>
        </div>
      )}
    </motion.div>
  );
}
