"use client";

/**
 * AudioDialogue — Podcast-style teacher/student conversation block.
 *
 * Renders a sequential speaker-bubble UI for AUDIO_DIALOGUE blocks.
 * Lines are revealed one at a time (typewriter cadence) with optional
 * per-line audio playback via the /brain/lesson/narrate/{filename} endpoint.
 *
 * Misconception lines receive a distinct amber highlight so corrections
 * stand out visually and are memorable.
 *
 * Props match AudioDialogueData in adeline-brain/app/schemas/api_models.py.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Pause,
  SkipForward,
  Volume2,
  VolumeX,
  AlertTriangle,
  CheckCircle2,
  MessageCircle,
} from "lucide-react";

// ── Types (mirrors DialogueLine + AudioDialogueData in api_models.py) ────────

export interface DialogueLine {
  speaker: "teacher" | "student";
  speaker_name?: string;
  text: string;
  audio_url?: string | null;
  addresses_misconception?: boolean;
  pause_after_ms?: number;
}

export interface AudioDialogueData {
  topic: string;
  lines: DialogueLine[];
  total_duration_estimate_secs?: number;
}

export interface AudioDialogueProps {
  /** The structured dialogue data from AUDIO_DIALOGUE block */
  data: AudioDialogueData;
  /** Learning track — drives header accent color */
  track?: string;
  /** Called when the student completes all dialogue lines */
  onComplete?: () => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

// ── Track accent colors ───────────────────────────────────────────────────────

const TRACK_ACCENT: Record<string, string> = {
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

// ── Speaker avatar configs ────────────────────────────────────────────────────

const TEACHER_AVATAR = {
  bg:    "#F0FDF4",
  ring:  "#2F4731",
  label: "#2F4731",
  emoji: "🎓",
};

const STUDENT_AVATAR = {
  bg:    "#EFF6FF",
  ring:  "#1D4ED8",
  label: "#1D4ED8",
  emoji: "🧑",
};

// ── AudioDialogue ─────────────────────────────────────────────────────────────

export function AudioDialogue({
  data,
  track,
  onComplete,
  onStateChange,
  state,
  callbacks: _callbacks,
}: AudioDialogueProps) {
  const lines = data.lines ?? [];
  const accent = TRACK_ACCENT[track ?? ""] ?? "#1D4ED8";

  // Resume from persisted state if available
  const [visibleCount, setVisibleCount] = useState<number>(
    (state?.visibleCount as number) ?? 0,
  );
  const [autoPlay, setAutoPlay] = useState<boolean>(true);
  const [audioEnabled, setAudioEnabled] = useState<boolean>(true);
  const [completed, setCompleted] = useState<boolean>(
    !!(state?.completed),
  );
  const [audioPlaying, setAudioPlaying] = useState<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const autoAdvanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Persist state on every visible-count change ───────────────────────────
  useEffect(() => {
    onStateChange?.({ visibleCount, completed });
  }, [visibleCount, completed, onStateChange]);

  // ── Auto-advance: reveal next line after current one's pause_after_ms ────
  const clearAutoAdvance = useCallback(() => {
    if (autoAdvanceTimerRef.current) {
      clearTimeout(autoAdvanceTimerRef.current);
      autoAdvanceTimerRef.current = null;
    }
  }, []);

  const advanceLine = useCallback(() => {
    setVisibleCount((prev) => {
      const next = prev + 1;
      if (next >= lines.length) {
        setCompleted(true);
        onComplete?.();
      }
      return next;
    });
  }, [lines.length, onComplete]);

  const scheduleAutoAdvance = useCallback(
    (lineIdx: number) => {
      if (!autoPlay) return;
      const line = lines[lineIdx];
      if (!line) return;
      const pauseMs = line.pause_after_ms ?? 400;
      // If there is audio for this line and audio is enabled, wait for audio
      // to finish before scheduling the auto-advance — handled via onended.
      if (line.audio_url && audioEnabled) return;
      autoAdvanceTimerRef.current = setTimeout(() => {
        advanceLine();
      }, pauseMs + 600);
    },
    [autoPlay, audioEnabled, lines, advanceLine],
  );

  // ── Audio playback per line ───────────────────────────────────────────────
  const playLineAudio = useCallback(
    (line: DialogueLine, onEnd: () => void) => {
      if (!line.audio_url || !audioEnabled) { onEnd(); return; }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
      const audio = new Audio(line.audio_url);
      audioRef.current = audio;
      audio.onended = () => {
        setAudioPlaying(false);
        onEnd();
      };
      audio.onerror = () => {
        setAudioPlaying(false);
        onEnd();
      };
      setAudioPlaying(true);
      audio.play().catch(() => {
        setAudioPlaying(false);
        onEnd();
      });
    },
    [audioEnabled],
  );

  // Whenever visibleCount increases, play audio for the new line then schedule advance
  useEffect(() => {
    if (visibleCount === 0) return;
    const lineIdx = visibleCount - 1;
    const line = lines[lineIdx];
    if (!line) return;

    clearAutoAdvance();

    if (line.audio_url && audioEnabled && autoPlay) {
      playLineAudio(line, () => {
        const pauseMs = line.pause_after_ms ?? 400;
        autoAdvanceTimerRef.current = setTimeout(advanceLine, pauseMs);
      });
    } else {
      scheduleAutoAdvance(lineIdx);
    }

    // Scroll new bubble into view
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [visibleCount]); // eslint-disable-line react-hooks/exhaustive-deps

  // Start auto-play on mount — reveal first line after a short delay
  useEffect(() => {
    if (visibleCount === 0 && !completed) {
      autoAdvanceTimerRef.current = setTimeout(() => {
        advanceLine();
      }, 600);
    }
    return () => clearAutoAdvance();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
      clearAutoAdvance();
    };
  }, [clearAutoAdvance]);

  // ── Controls ──────────────────────────────────────────────────────────────
  const handleSkip = useCallback(() => {
    clearAutoAdvance();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      setAudioPlaying(false);
    }
    advanceLine();
  }, [clearAutoAdvance, advanceLine]);

  const handleToggleAudio = useCallback(() => {
    setAudioEnabled((prev) => !prev);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      setAudioPlaying(false);
    }
  }, []);

  const handleToggleAutoPlay = useCallback(() => {
    setAutoPlay((prev) => {
      if (!prev) {
        // Resuming — schedule the next line
        scheduleAutoAdvance(visibleCount - 1);
      } else {
        clearAutoAdvance();
      }
      return !prev;
    });
  }, [visibleCount, scheduleAutoAdvance, clearAutoAdvance]);

  const handleManualRevealNext = useCallback(() => {
    clearAutoAdvance();
    advanceLine();
  }, [clearAutoAdvance, advanceLine]);

  const isFinished = completed || visibleCount >= lines.length;
  const canAdvance = !isFinished && visibleCount < lines.length;

  // ── Duration badge ────────────────────────────────────────────────────────
  const durationLabel =
    data.total_duration_estimate_secs && data.total_duration_estimate_secs > 0
      ? `~${Math.ceil(data.total_duration_estimate_secs / 60)} min`
      : null;

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `1.5px solid ${accent}20`, background: "#FAFAFA" }}
    >
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: accent, color: "#fff" }}
      >
        <div className="flex items-center gap-2">
          <MessageCircle size={16} />
          <span className="text-sm font-bold tracking-wide">Audio Dialogue</span>
          {durationLabel && (
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: "rgba(255,255,255,0.2)" }}
            >
              {durationLabel}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Audio toggle */}
          <button
            onClick={handleToggleAudio}
            className="opacity-80 hover:opacity-100 transition-opacity"
            title={audioEnabled ? "Mute audio" : "Unmute audio"}
          >
            {audioEnabled ? (
              <Volume2 size={15} />
            ) : (
              <VolumeX size={15} />
            )}
          </button>
          {/* Auto-play toggle */}
          <button
            onClick={handleToggleAutoPlay}
            className="opacity-80 hover:opacity-100 transition-opacity"
            title={autoPlay ? "Pause auto-advance" : "Resume auto-advance"}
          >
            {autoPlay ? <Pause size={15} /> : <Play size={15} />}
          </button>
        </div>
      </div>

      {/* ── Topic label ───────────────────────────────────────────────────── */}
      {data.topic && (
        <div
          className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: accent, background: `${accent}0D` }}
        >
          {data.topic}
        </div>
      )}

      {/* ── Dialogue bubbles ──────────────────────────────────────────────── */}
      <div
        ref={containerRef}
        className="px-4 py-3 space-y-3 overflow-y-auto"
        style={{ maxHeight: 420 }}
      >
        <AnimatePresence initial={false}>
          {lines.slice(0, visibleCount).map((line, idx) => {
            const isTeacher = line.speaker === "teacher";
            const avatar = isTeacher ? TEACHER_AVATAR : STUDENT_AVATAR;
            const speakerName = line.speaker_name ?? (isTeacher ? "Adeline" : "Alex");
            const isMisconception = line.addresses_misconception === true;
            const isLastVisible = idx === visibleCount - 1;

            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className={`flex gap-3 ${isTeacher ? "flex-row" : "flex-row-reverse"}`}
              >
                {/* Avatar */}
                <div
                  className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm"
                  style={{
                    background: avatar.bg,
                    border: `2px solid ${avatar.ring}`,
                  }}
                  title={speakerName}
                >
                  {avatar.emoji}
                </div>

                {/* Bubble */}
                <div className={`flex flex-col gap-1 max-w-[80%] ${isTeacher ? "items-start" : "items-end"}`}>
                  {/* Speaker name */}
                  <span
                    className="text-[10px] font-bold uppercase tracking-wider"
                    style={{ color: avatar.label }}
                  >
                    {speakerName}
                  </span>

                  {/* Misconception banner */}
                  {isMisconception && (
                    <div
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold"
                      style={{
                        background: "#FEF9C3",
                        border: "1px solid #CA8A04",
                        color: "#78350F",
                      }}
                    >
                      <AlertTriangle size={11} />
                      Common misconception addressed
                    </div>
                  )}

                  {/* Text bubble */}
                  <div
                    className="px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed"
                    style={
                      isMisconception
                        ? {
                            background: "#FEFCE8",
                            border: "1.5px solid #CA8A04",
                            color: "#451A03",
                          }
                        : isTeacher
                        ? {
                            background: "#fff",
                            border: `1.5px solid ${TEACHER_AVATAR.ring}20`,
                            color: "#1F2937",
                          }
                        : {
                            background: "#EFF6FF",
                            border: `1.5px solid ${STUDENT_AVATAR.ring}20`,
                            color: "#1E3A8A",
                          }
                    }
                  >
                    {line.text}

                    {/* Audio playing indicator */}
                    {isLastVisible && audioPlaying && (
                      <span
                        className="inline-flex items-center gap-0.5 ml-2 align-middle"
                        aria-label="Audio playing"
                      >
                        {[0, 1, 2].map((i) => (
                          <motion.span
                            key={i}
                            className="inline-block w-0.5 rounded-full"
                            style={{ height: 10, background: accent }}
                            animate={{ scaleY: [0.4, 1, 0.4] }}
                            transition={{
                              duration: 0.6,
                              repeat: Infinity,
                              delay: i * 0.15,
                            }}
                          />
                        ))}
                      </span>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Thinking indicator while next line loads */}
        {!isFinished && visibleCount > 0 && (
          <motion.div
            key="typing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex gap-3"
          >
            <div
              className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm"
              style={{ background: TEACHER_AVATAR.bg, border: `2px solid ${TEACHER_AVATAR.ring}` }}
            >
              {TEACHER_AVATAR.emoji}
            </div>
            <div className="flex items-end pb-1">
              <div
                className="flex gap-1 px-3 py-2.5 rounded-2xl"
                style={{ background: "#fff", border: `1.5px solid ${TEACHER_AVATAR.ring}20` }}
              >
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: "#9CA3AF" }}
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* ── Controls bar ──────────────────────────────────────────────────── */}
      {!isFinished ? (
        <div
          className="px-4 py-3 flex items-center justify-between border-t"
          style={{ borderColor: `${accent}15` }}
        >
          {/* Progress */}
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              {lines.map((_, i) => (
                <div
                  key={i}
                  className="h-1 w-3 rounded-full transition-colors"
                  style={{
                    background: i < visibleCount ? accent : "#E5E7EB",
                  }}
                />
              ))}
            </div>
            <span className="text-[10px] text-[#9CA3AF]">
              {visibleCount} / {lines.length}
            </span>
          </div>

          {/* Manual next (when auto-play is paused) */}
          {(!autoPlay || !canAdvance) && canAdvance && (
            <button
              onClick={handleManualRevealNext}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: accent }}
            >
              Next <SkipForward size={12} />
            </button>
          )}
        </div>
      ) : (
        /* Completion footer */
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="px-4 py-3 flex items-center gap-2 border-t"
          style={{ borderColor: `${accent}15`, background: "#F0FDF4" }}
        >
          <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
          <span className="text-xs font-semibold text-emerald-700">
            Dialogue complete — {lines.filter((l) => l.addresses_misconception).length > 0
              ? `${lines.filter((l) => l.addresses_misconception).length} misconception${lines.filter((l) => l.addresses_misconception).length > 1 ? "s" : ""} clarified`
              : "nice work!"}
          </span>
        </motion.div>
      )}
    </div>
  );
}

export default AudioDialogue;
