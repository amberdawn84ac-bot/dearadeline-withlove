"use client";

/**
 * Flashcard — Flip-card component for vocabulary and concept review.
 * Adapted from cascade-adeline/src/components/gen-ui/patterns/Flashcard.tsx.
 * Pure CSS 3D flip; no framer-motion dependency required.
 */

import { useState } from "react";
import { useGenUITelemetry } from "@/lib/useGenUITelemetry";

export interface FlashcardProps {
  term: string;
  definition: string;
  example?: string;
  category?: string;
  studentId?: string;
  lessonId?: string;
  blockId?: string;
  track?: string;
}

export function Flashcard({ term, definition, example, category, studentId, lessonId, blockId, track }: FlashcardProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const { reportInteraction } = useGenUITelemetry({ studentId: studentId ?? "", lessonId: lessonId ?? "" });

  return (
    <div
      onClick={() => { setIsFlipped((f) => !f); if (studentId && lessonId) reportInteraction("Flashcard", { flipped: !isFlipped, term }, blockId); }}
      className="cursor-pointer select-none"
      style={{ perspective: "1000px", minHeight: 200 }}
      role="button"
      aria-label={isFlipped ? `Definition of ${term}` : `Flashcard: ${term}`}
    >
      <div
        style={{
          position:          "relative",
          width:             "100%",
          minHeight:         200,
          transformStyle:    "preserve-3d",
          transition:        "transform 0.6s",
          transform:         isFlipped ? "rotateY(180deg)" : "rotateY(0deg)",
        }}
      >
        {/* Front — term */}
        <div
          style={{
            position:           "absolute",
            inset:              0,
            backfaceVisibility: "hidden",
            background:         "#FFFEF7",
            border:             "2px solid #BD6809",
            borderRadius:       16,
            padding:            20,
            display:            "flex",
            flexDirection:      "column",
            justifyContent:     "center",
            alignItems:         "center",
            minHeight:          200,
          }}
        >
          {category && (
            <span
              className="text-[11px] font-bold uppercase tracking-widest px-3 py-1 rounded-full mb-4"
              style={{ background: "#BD680920", color: "#BD6809" }}
            >
              {category}
            </span>
          )}
          <p className="text-xl font-bold text-[#2F4731] text-center leading-tight">{term}</p>
          <p className="text-xs text-[#2F4731]/40 mt-4">Tap to flip</p>
        </div>

        {/* Back — definition */}
        <div
          style={{
            position:           "absolute",
            inset:              0,
            backfaceVisibility: "hidden",
            background:         "#FFFEF7",
            border:             "2px solid #2F4731",
            borderRadius:       16,
            padding:            20,
            display:            "flex",
            flexDirection:      "column",
            justifyContent:     "center",
            transform:          "rotateY(180deg)",
            minHeight:          200,
          }}
        >
          <p className="text-sm font-medium text-[#2F4731] leading-relaxed">{definition}</p>
          {example && (
            <div
              className="rounded-xl px-3 py-2 mt-3 space-y-1"
              style={{ background: "#F0E8D8", border: "1px solid #BD680940" }}
            >
              <p className="text-[10px] font-bold text-[#BD6809] uppercase tracking-wider">
                Example
              </p>
              <p className="text-xs text-[#2F4731] italic leading-relaxed">{example}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
