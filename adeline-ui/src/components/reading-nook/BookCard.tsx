"use client";

/**
 * BookCard — A reusable card component for displaying a single book in the Bookshelf.
 *
 * Features:
 * - Book cover image or 📚 placeholder
 * - Title (2-line max) and author with ellipsis
 * - Track badge (colored pill with curriculum track)
 * - Reading level badge (grade band)
 * - Progress bar (shown only when reading)
 * - Hover state with "Start Reading" or "Open Reader" button
 *
 * Design:
 * - Card width: 180px (fits 4-column grid on desktop)
 * - Cover image: 160px × 200px
 * - Padding: 12px
 * - Tailwind-only styling (no CSS files)
 */

import { useState } from "react";
import { BookOpen } from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

export interface Book {
  id: string;
  title: string;
  author: string;
  lexile_level: number;
  grade_band: string;
  track: string;
  cover_url?: string;
  source_library?: string;
}

export interface ReadingSession {
  id: string;
  status: "reading" | "finished" | "wishlist";
  pages_read: number;
  total_pages?: number;
  started_at: string;
  reading_minutes: number;
}

export interface BookCardProps {
  book: Book;
  session?: ReadingSession;
  onStart?: (bookId: string) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// TRACK CONFIG — Colors & Labels for curriculum tracks
// ─────────────────────────────────────────────────────────────────────────────

export const TRACK_CONFIG: Record<
  string,
  { color: string; label: string }
> = {
  CREATION_SCIENCE: {
    color: "bg-green-100 text-green-700",
    label: "Science",
  },
  HEALTH_NATUROPATHY: {
    color: "bg-emerald-100 text-emerald-700",
    label: "Health",
  },
  HOMESTEADING: {
    color: "bg-amber-100 text-amber-700",
    label: "Homesteading",
  },
  GOVERNMENT_ECONOMICS: {
    color: "bg-blue-100 text-blue-700",
    label: "Gov",
  },
  JUSTICE_CHANGEMAKING: {
    color: "bg-red-100 text-red-700",
    label: "Justice",
  },
  DISCIPLESHIP: {
    color: "bg-purple-100 text-purple-700",
    label: "Discipleship",
  },
  TRUTH_HISTORY: {
    color: "bg-orange-100 text-orange-700",
    label: "History",
  },
  ENGLISH_LITERATURE: {
    color: "bg-rose-100 text-rose-700",
    label: "Literature",
  },
  APPLIED_MATHEMATICS: {
    color: "bg-indigo-100 text-indigo-700",
    label: "Math",
  },
  CREATIVE_ECONOMY: {
    color: "bg-pink-100 text-pink-700",
    label: "Creative",
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// READING LEVEL COLORS — Grade-band color mapping
// ─────────────────────────────────────────────────────────────────────────────

const READING_LEVEL_COLORS: Record<string, string> = {
  K: "bg-blue-50 text-blue-600",
  "1": "bg-blue-50 text-blue-600",
  "2": "bg-blue-100 text-blue-700",
  "3": "bg-green-50 text-green-600",
  "4-5": "bg-green-100 text-green-700",
  "6": "bg-yellow-50 text-yellow-600",
  "7": "bg-yellow-100 text-yellow-700",
  "8": "bg-orange-50 text-orange-600",
  "9-12": "bg-red-50 text-red-600",
};

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export function BookCard({ book, session, onStart }: BookCardProps) {
  const [hovering, setHovering] = useState(false);

  const trackConfig = TRACK_CONFIG[book.track] || {
    color: "bg-gray-100 text-gray-700",
    label: book.track,
  };

  const readingLevelColor = READING_LEVEL_COLORS[book.grade_band] || "bg-gray-50 text-gray-600";

  const isReading = session?.status === "reading";
  const hasProgress = isReading && session?.total_pages && session.total_pages > 0;
  const progressPercent = hasProgress
    ? Math.round((session!.pages_read / session!.total_pages!) * 100)
    : 0;

  const handleClick = (e: React.MouseEvent) => {
    // Prevent triggering onStart if clicking the button
    if ((e.target as HTMLElement).closest("button")) return;
    onStart?.(book.id);
  };

  return (
    <article
      onClick={handleClick}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      className={`
        w-[180px] rounded-lg overflow-hidden
        transition-all duration-200 cursor-pointer
        ${hovering ? "shadow-lg border border-amber-200" : "shadow-sm border border-[#E7DAC3]"}
        bg-white
      `}
    >
      {/* COVER IMAGE OR PLACEHOLDER */}
      <div className="relative h-[200px] w-full overflow-hidden bg-gray-100 flex items-center justify-center">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={`${book.title} cover`}
            className={`w-full h-full object-cover transition-transform duration-200 ${
              hovering ? "scale-110" : "scale-100"
            }`}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-gray-400">
            <BookOpen size={48} />
          </div>
        )}
      </div>

      {/* CONTENT SECTION */}
      <div className="p-3 space-y-2">
        {/* TITLE */}
        <h3 className="text-sm font-bold text-[#2F4731] line-clamp-2">
          {book.title}
        </h3>

        {/* AUTHOR */}
        <p className="text-xs text-[#2F4731]/60 line-clamp-1">
          {book.author}
        </p>

        {/* BADGES */}
        <div className="flex gap-1 flex-wrap pt-1">
          {/* TRACK BADGE */}
          <span
            className={`text-[10px] font-bold px-2 py-1 rounded-full ${trackConfig.color}`}
            title={`Track: ${trackConfig.label}`}
            aria-label={`Track: ${trackConfig.label}`}
          >
            {trackConfig.label}
          </span>

          {/* READING LEVEL BADGE */}
          <span
            className={`text-[10px] font-bold px-2 py-1 rounded-full ${readingLevelColor}`}
            title={`Grade: ${book.grade_band}`}
            aria-label={`Reading Level: ${book.grade_band}`}
          >
            {book.grade_band}
          </span>
        </div>

        {/* PROGRESS BAR (if reading) */}
        {hasProgress && (
          <div className="pt-2 space-y-1">
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
                role="progressbar"
                aria-valuenow={progressPercent}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
            <p className="text-xs text-gray-600 text-right">
              {progressPercent}%
            </p>
          </div>
        )}
      </div>

      {/* BUTTON (shown on hover) */}
      {hovering && (
        <div className="px-3 pb-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStart?.(book.id);
            }}
            className={`
              w-full py-2 rounded-lg font-semibold text-sm
              transition-all duration-150
              ${
                isReading
                  ? "bg-blue-500 hover:bg-blue-600 text-white"
                  : "bg-teal-500 hover:bg-teal-600 text-white"
              }
            `}
            aria-label={isReading ? "Open Reader" : "Start Reading"}
          >
            {isReading ? "Open Reader" : "Start Reading"}
          </button>
        </div>
      )}
    </article>
  );
}
