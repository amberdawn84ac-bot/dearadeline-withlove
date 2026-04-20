"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Volume2, VolumeX, CheckCircle2, BookOpen } from "lucide-react";
import type { NarratedSlideData } from "@/lib/brain-client";

const TRACK_COLORS: Record<string, string> = {
  TRUTH_HISTORY:        "#1E3A5F",
  JUSTICE_CHANGEMAKING: "#7C2D12",
  GOVERNMENT_ECONOMICS: "#78350F",
  CREATION_SCIENCE:     "#14532D",
  HOMESTEADING:         "#365314",
  DISCIPLESHIP:         "#581C87",
  HEALTH_NATUROPATHY:   "#164E63",
  ENGLISH_LITERATURE:   "#7C3AED",
  APPLIED_MATHEMATICS:  "#1D4ED8",
  CREATIVE_ECONOMY:     "#9D174D",
};

export interface NarratedSlidesProps {
  data: NarratedSlideData;
  track?: string;
  audio_urls?: string[];
  onComplete?: () => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

export function NarratedSlides({
  data,
  track,
  audio_urls = [],
  onComplete,
  onStateChange,
  state,
}: NarratedSlidesProps) {
  const slides = data.slides ?? [];
  const [slideIdx, setSlideIdx] = useState((state?.slideIdx as number) ?? 0);
  const [visibleBullets, setVisibleBullets] = useState((state?.visibleBullets as number) ?? 0);
  const [showNarration, setShowNarration] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [completed, setCompleted] = useState(!!state?.completed);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const slide = slides[slideIdx];
  const themeColor = TRACK_COLORS[track ?? ""] ?? "#1D4ED8";
  const audioUrl = audio_urls[slideIdx];
  const allBulletsShown = visibleBullets >= (slide?.bullets.length ?? 0);
  const isLastSlide = slideIdx === slides.length - 1;

  useEffect(() => {
    setVisibleBullets(0);
    setShowNarration(false);
    setAudioPlaying(false);
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
  }, [slideIdx]);

  const toggleAudio = useCallback(() => {
    if (!audioUrl) return;
    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl);
      audioRef.current.onended = () => setAudioPlaying(false);
    }
    if (audioPlaying) {
      audioRef.current.pause();
      setAudioPlaying(false);
    } else {
      audioRef.current.play();
      setAudioPlaying(true);
    }
  }, [audioUrl, audioPlaying]);

  const advance = () => {
    if (!allBulletsShown) {
      const next = visibleBullets + 1;
      setVisibleBullets(next);
      onStateChange?.({ slideIdx, visibleBullets: next, completed });
    } else if (!isLastSlide) {
      const next = slideIdx + 1;
      setSlideIdx(next);
      onStateChange?.({ slideIdx: next, visibleBullets: 0, completed });
    } else {
      setCompleted(true);
      onStateChange?.({ slideIdx, visibleBullets, completed: true });
      onComplete?.();
    }
  };

  const goBack = () => {
    if (visibleBullets > 0) {
      const prev = visibleBullets - 1;
      setVisibleBullets(prev);
      onStateChange?.({ slideIdx, visibleBullets: prev, completed });
    } else if (slideIdx > 0) {
      const prev = slideIdx - 1;
      setSlideIdx(prev);
    }
  };

  if (!slide) return null;

  const advanceLabel =
    !allBulletsShown ? "Next point" :
    !isLastSlide     ? "Next slide" :
    completed        ? "Done" : "Finish";

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `1.5px solid ${themeColor}25`, background: "#FAFBFF" }}
    >
      {/* Header */}
      <div
        className="px-4 py-2.5 flex items-center justify-between"
        style={{ background: `${themeColor}08`, borderBottom: `1px solid ${themeColor}15` }}
      >
        <div className="flex items-center gap-2">
          <BookOpen size={13} style={{ color: themeColor }} />
          <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: themeColor }}>
            Mini Lecture
          </span>
          <span className="text-[10px] text-[#9CA3AF]">{data.total_duration_minutes} min</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Audio toggle */}
          {audioUrl && (
            <button
              onClick={toggleAudio}
              className="p-1.5 rounded-lg transition-colors"
              style={{
                background: audioPlaying ? `${themeColor}18` : "transparent",
                color: audioPlaying ? themeColor : "#9CA3AF",
              }}
              title={audioPlaying ? "Pause narration" : "Play narration"}
            >
              {audioPlaying ? <Volume2 size={13} /> : <VolumeX size={13} />}
            </button>
          )}
          {/* Slide counter */}
          <span className="text-[10px] font-semibold" style={{ color: themeColor }}>
            {slideIdx + 1} / {slides.length}
          </span>
        </div>
      </div>

      {/* Progress dots */}
      <div className="flex gap-1 px-4 pt-3">
        {slides.map((_, i) => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-all duration-300"
            style={{
              background: i < slideIdx ? themeColor : i === slideIdx ? `${themeColor}60` : "#E5E7EB",
            }}
          />
        ))}
      </div>

      {/* Slide */}
      <AnimatePresence mode="wait">
        <motion.div
          key={slideIdx}
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -24 }}
          className="px-4 pt-4 pb-3 space-y-3 min-h-[160px]"
        >
          <h3 className="text-base font-bold text-[#1F2937] leading-snug">{slide.title}</h3>

          {/* Bullets */}
          <ul className="space-y-2">
            {slide.bullets.map((bullet, i) => (
              <AnimatePresence key={i}>
                {i < visibleBullets && (
                  <motion.li
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-start gap-2.5 text-sm text-[#374151] leading-snug"
                  >
                    <span className="shrink-0 font-bold mt-0.5 text-sm" style={{ color: themeColor }}>→</span>
                    <span>{bullet}</span>
                  </motion.li>
                )}
              </AnimatePresence>
            ))}
          </ul>

          {/* Bullet count hint */}
          {!allBulletsShown && (
            <p className="text-[10px] text-[#9CA3AF]">
              {visibleBullets} / {slide.bullets.length} points shown
            </p>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Narration script */}
      {showNarration && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="overflow-hidden"
        >
          <div
            className="mx-4 mb-3 rounded-lg px-3 py-2.5 text-xs text-[#6B7280] leading-relaxed italic"
            style={{ background: `${themeColor}06`, border: `1px solid ${themeColor}12` }}
          >
            {slide.narration}
          </div>
        </motion.div>
      )}

      {/* Controls */}
      <div
        className="px-4 py-2.5 flex items-center justify-between"
        style={{ borderTop: `1px solid ${themeColor}10` }}
      >
        <div className="flex items-center gap-1">
          <button
            onClick={goBack}
            disabled={slideIdx === 0 && visibleBullets === 0}
            className="p-1.5 rounded-lg text-[#9CA3AF] hover:text-[#374151] disabled:opacity-30 transition-colors"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={() => setShowNarration((s) => !s)}
            className="text-[10px] px-2 py-1 rounded transition-colors"
            style={{
              color: showNarration ? themeColor : "#9CA3AF",
              background: showNarration ? `${themeColor}10` : "transparent",
            }}
          >
            {showNarration ? "Hide script" : "Read script"}
          </button>
        </div>

        {completed ? (
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600">
            <CheckCircle2 size={13} />
            Complete
          </div>
        ) : (
          <button
            onClick={advance}
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
            style={{ background: themeColor, color: "#fff" }}
          >
            {advanceLabel}
            <ChevronRight size={12} />
          </button>
        )}
      </div>
    </div>
  );
}
