"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Play, Pause, ExternalLink, Clock, CheckCircle2 } from "lucide-react";
import { fireGenUICallback } from "@/lib/genui-callback";

export interface SimulationEmbedProps {
  title: string;
  description?: string;
  simulationUrl: string;
  provider?: "phet" | "geogebra" | "desmos" | "custom";
  estimatedMinutes?: number;
  competencies?: string[];
  track?: string;
  studentId?: string;
  lessonId?: string;
  blockId?: string;
  onComplete?: (state: { timeSpentMs: number; interacted: boolean }) => void;
  onStateChange?: (state: Record<string, unknown>) => void;
}

export function SimulationEmbed({
  title,
  description,
  simulationUrl,
  provider = "phet",
  estimatedMinutes = 5,
  competencies = [],
  track,
  studentId,
  lessonId,
  blockId,
  onComplete,
  onStateChange,
}: SimulationEmbedProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [timeSpent, setTimeSpent] = useState(0);
  const [completed, setCompleted] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedAt = useRef(Date.now());

  const themeColor = track === "CREATION_SCIENCE" ? "#2F4731" : "#6B3A2A";
  const accentColor = track === "CREATION_SCIENCE" ? "#8BAE6B" : "#C27C4E";

  useEffect(() => {
    if (isActive && !completed) {
      intervalRef.current = setInterval(() => {
        setTimeSpent((t) => t + 1);
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isActive, completed]);

  useEffect(() => {
    onStateChange?.({ timeSpent, isActive, isLoaded });
  }, [timeSpent, isActive, isLoaded, onStateChange]);

  const handleComplete = () => {
    setCompleted(true);
    setIsActive(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
    onComplete?.({ timeSpentMs: Date.now() - mountedAt.current, interacted: timeSpent > 10 });
    fireGenUICallback({ studentId, lessonId, componentType: "SimulationEmbed", event: "onComplete", state: { timeSpentMs: Date.now() - mountedAt.current, interacted: timeSpent > 10 }, blockId, track });
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const providerLabel = {
    phet: "PhET Interactive Simulations",
    geogebra: "GeoGebra",
    desmos: "Desmos",
    custom: "Interactive Simulation",
  }[provider];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${themeColor}20`, background: "#FFFEF7" }}
    >
      {/* Header */}
      <div
        className="px-5 py-3 flex items-center justify-between"
        style={{ background: `${themeColor}08` }}
      >
        <div>
          <h3 className="font-semibold text-sm" style={{ color: themeColor }}>
            {title}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">{providerLabel}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <Clock size={12} />
            {formatTime(timeSpent)} / ~{estimatedMinutes}m
          </span>
          {completed && (
            <span className="flex items-center gap-1 text-xs font-medium" style={{ color: accentColor }}>
              <CheckCircle2 size={14} />
              Complete
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      {description && (
        <p className="px-5 py-2 text-sm text-gray-600 border-b border-gray-100">
          {description}
        </p>
      )}

      {/* Simulation iframe */}
      <div className="relative" style={{ height: "420px" }}>
        {!isLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto mb-3" style={{ borderColor: accentColor }} />
              <p className="text-sm text-gray-500">Loading simulation…</p>
            </div>
          </div>
        )}
        <iframe
          src={simulationUrl}
          className="w-full h-full border-0"
          onLoad={() => {
            setIsLoaded(true);
            setIsActive(true);
          }}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope"
          sandbox="allow-scripts allow-same-origin allow-popups"
          title={title}
        />
      </div>

      {/* Footer controls */}
      <div className="px-5 py-3 flex items-center justify-between border-t border-gray-100">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsActive(!isActive)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{
              background: isActive ? `${themeColor}10` : `${accentColor}20`,
              color: isActive ? themeColor : accentColor,
            }}
          >
            {isActive ? <Pause size={12} /> : <Play size={12} />}
            {isActive ? "Pause" : "Resume"}
          </button>
          <a
            href={simulationUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ExternalLink size={12} />
            Open full
          </a>
        </div>

        {!completed && timeSpent >= 30 && (
          <button
            onClick={handleComplete}
            className="px-4 py-1.5 rounded-lg text-xs font-medium text-white transition-colors"
            style={{ background: accentColor }}
          >
            Mark Complete
          </button>
        )}
      </div>

      {/* Competency tags */}
      {competencies.length > 0 && (
        <div className="px-5 pb-3 flex flex-wrap gap-1.5">
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
      )}
    </motion.div>
  );
}
