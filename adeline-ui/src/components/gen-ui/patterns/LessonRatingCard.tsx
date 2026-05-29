"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ThumbsUp, ThumbsDown } from "lucide-react";

interface LessonRatingCardProps {
  studentId: string;
  lessonId: string;
  componentType: string;
  track?: string;
  topic?: string;
}

export function LessonRatingCard({
  studentId,
  lessonId,
  componentType,
  track,
  topic,
}: LessonRatingCardProps) {
  const [rating, setRating] = useState<1 | -1 | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleRating(value: 1 | -1) {
    setRating(value);
    try {
      await fetch(`/api/students/${studentId}/lesson-rating`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lessonId, componentType, rating: value, track, topic }),
      });
    } catch {
    } finally {
      setTimeout(() => setSaved(true), 600);
    }
  }

  return (
    <AnimatePresence mode="wait">
      {!saved ? (
        <motion.div
          key="rating"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          className="rounded-2xl border border-slate-200 bg-white px-6 py-4 flex items-center justify-between gap-4"
        >
          <p className="text-sm text-slate-600 font-medium">
            Did this lesson work for you?
          </p>
          <div className="flex gap-3">
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={() => handleRating(1)}
              className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                rating === 1
                  ? "bg-emerald-500 text-white"
                  : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
              }`}
            >
              <ThumbsUp className="w-4 h-4" />
              Yes
            </motion.button>
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={() => handleRating(-1)}
              className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                rating === -1
                  ? "bg-rose-500 text-white"
                  : "bg-rose-50 text-rose-700 hover:bg-rose-100"
              }`}
            >
              <ThumbsDown className="w-4 h-4" />
              Not really
            </motion.button>
          </div>
        </motion.div>
      ) : (
        <motion.div
          key="thanks"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-slate-100 bg-slate-50 px-6 py-4 text-center"
        >
          <p className="text-sm text-slate-500">
            {rating === 1
              ? "Glad it helped! Adeline will remember that. 🌟"
              : "Got it — Adeline will try something different next time."}
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
