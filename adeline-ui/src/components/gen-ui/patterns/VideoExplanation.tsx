"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Play, Pause, SkipForward, CheckCircle2, BookOpen } from "lucide-react";

export interface VideoChapter {
  title: string;
  timestamp: number;
  comprehensionCheck?: string;
}

export interface VideoExplanationProps {
  title: string;
  videoUrl: string;
  provider?: "youtube" | "vimeo" | "narrated";
  chapters?: VideoChapter[];
  transcript?: string;
  track?: string;
  onComplete?: (state: { watchedPercent: number; chaptersCompleted: number }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

function getEmbedUrl(videoUrl: string, provider: string): string {
  if (provider === "youtube") {
    const match = videoUrl.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return match ? `https://www.youtube.com/embed/${match[1]}?rel=0&modestbranding=1` : videoUrl;
  }
  if (provider === "vimeo") {
    const match = videoUrl.match(/vimeo\.com\/(\d+)/);
    return match ? `https://player.vimeo.com/video/${match[1]}` : videoUrl;
  }
  return videoUrl;
}

export function VideoExplanation({
  title,
  videoUrl,
  provider = "youtube",
  chapters = [],
  transcript,
  track,
  onComplete,
  onStateChange,
}: VideoExplanationProps) {
  const [currentChapter, setCurrentChapter] = useState(0);
  const [chaptersCompleted, setChaptersCompleted] = useState<Set<number>>(new Set());
  const [showTranscript, setShowTranscript] = useState(false);
  const [completed, setCompleted] = useState(false);
  const mountedAt = useRef(Date.now());

  const themeColor = track === "TRUTH_HISTORY" ? "#6B3A2A" : "#2F4731";
  const accentColor = track === "TRUTH_HISTORY" ? "#C27C4E" : "#8BAE6B";
  const embedUrl = getEmbedUrl(videoUrl, provider);

  useEffect(() => {
    onStateChange?.({ currentChapter, chaptersCompleted: chaptersCompleted.size, showTranscript });
  }, [currentChapter, chaptersCompleted, showTranscript, onStateChange]);

  const markChapterDone = (index: number) => {
    const updated = new Set(chaptersCompleted);
    updated.add(index);
    setChaptersCompleted(updated);

    if (updated.size === chapters.length && chapters.length > 0 && !completed) {
      setCompleted(true);
      onComplete?.({ watchedPercent: 100, chaptersCompleted: updated.size });
    }
  };

  const handleComplete = () => {
    setCompleted(true);
    onComplete?.({
      watchedPercent: chapters.length > 0 ? (chaptersCompleted.size / chapters.length) * 100 : 100,
      chaptersCompleted: chaptersCompleted.size,
    });
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
        <div>
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>{title}</h3>
          <p className="text-xs text-gray-500 mt-0.5 capitalize">{provider} Video</p>
        </div>
        {completed && (
          <span className="flex items-center gap-1 text-xs font-medium" style={{ color: accentColor }}>
            <CheckCircle2 size={14} /> Watched
          </span>
        )}
      </div>

      {/* Video embed */}
      <div className="relative" style={{ paddingBottom: "56.25%" }}>
        <iframe
          src={embedUrl}
          className="absolute inset-0 w-full h-full border-0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          title={title}
        />
      </div>

      {/* Chapters */}
      {chapters.length > 0 && (
        <div className="px-5 py-3 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-500 mb-2">Chapters</p>
          <div className="space-y-1.5">
            {chapters.map((ch, i) => (
              <button
                key={i}
                onClick={() => {
                  setCurrentChapter(i);
                  markChapterDone(i);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-xs transition-colors ${
                  currentChapter === i ? "font-medium" : ""
                }`}
                style={{
                  background: currentChapter === i ? `${accentColor}15` : "transparent",
                  color: chaptersCompleted.has(i) ? accentColor : "#374151",
                }}
              >
                {chaptersCompleted.has(i) ? (
                  <CheckCircle2 size={12} style={{ color: accentColor }} />
                ) : (
                  <Play size={12} className="text-gray-400" />
                )}
                <span className="flex-1">{ch.title}</span>
                <span className="text-gray-400">
                  {Math.floor(ch.timestamp / 60)}:{(ch.timestamp % 60).toString().padStart(2, "0")}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Transcript toggle */}
      {transcript && (
        <div className="px-5 pb-3">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="flex items-center gap-1.5 text-xs font-medium transition-colors"
            style={{ color: themeColor }}
          >
            <BookOpen size={12} />
            {showTranscript ? "Hide" : "Show"} Transcript
          </button>
          {showTranscript && (
            <div className="mt-2 p-3 rounded-lg bg-gray-50 text-xs text-gray-600 max-h-40 overflow-y-auto leading-relaxed">
              {transcript}
            </div>
          )}
        </div>
      )}

      {/* Complete button */}
      {!completed && (
        <div className="px-5 pb-4">
          <button
            onClick={handleComplete}
            className="w-full py-2 rounded-lg text-xs font-medium text-white transition-colors"
            style={{ background: accentColor }}
          >
            Mark as Watched
          </button>
        </div>
      )}
    </motion.div>
  );
}
