"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wind, Eye, Activity, CheckCircle2 } from "lucide-react";

type ResetMode = "breathe" | "ground" | "move";
type BreathPhase = "inhale" | "hold_in" | "exhale" | "hold_out";

const BREATH_PHASES: { phase: BreathPhase; label: string; seconds: number }[] = [
  { phase: "inhale",   label: "Breathe in…",  seconds: 4 },
  { phase: "hold_in",  label: "Hold…",         seconds: 4 },
  { phase: "exhale",   label: "Breathe out…",  seconds: 4 },
  { phase: "hold_out", label: "Hold…",         seconds: 4 },
];

const GROUND_STEPS = [
  { count: 5, icon: "👁️", prompt: "Name 5 things you can see right now" },
  { count: 4, icon: "✋", prompt: "Name 4 things you can physically feel" },
  { count: 3, icon: "👂", prompt: "Name 3 sounds you can hear" },
  { count: 2, icon: "👃", prompt: "Name 2 things you can smell" },
  { count: 1, icon: "👄", prompt: "Name 1 thing you can taste" },
];

export interface FocusResetProps {
  mode?: ResetMode;
  message?: string;
  move_prompt?: string;
  move_seconds?: number;
  onComplete?: () => void;
  onStateChange?: (state: Record<string, unknown>) => void;
  state?: Record<string, unknown>;
  callbacks?: string[];
}

// ── Breathe mode ──────────────────────────────────────────────────────────────

function BreatheMode({ onDone }: { onDone: () => void }) {
  const CYCLES = 3;
  const [cycle, setCycle] = useState(0);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [tick, setTick] = useState(0);
  const [done, setDone] = useState(false);

  const phase = BREATH_PHASES[phaseIdx];

  useEffect(() => {
    if (done) return;
    const id = setInterval(() => {
      setTick((t) => {
        if (t + 1 >= phase.seconds) {
          const nextPhase = (phaseIdx + 1) % BREATH_PHASES.length;
          if (nextPhase === 0) {
            const nextCycle = cycle + 1;
            if (nextCycle >= CYCLES) { setDone(true); return 0; }
            setCycle(nextCycle);
          }
          setPhaseIdx(nextPhase);
          return 0;
        }
        return t + 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [phaseIdx, phase.seconds, cycle, done]);

  const progress = tick / phase.seconds;
  const circleScale =
    phase.phase === "inhale"   ? 0.6 + 0.4 * progress :
    phase.phase === "exhale"   ? 1 - 0.4 * progress :
    phase.phase === "hold_in"  ? 1 : 0.6;

  if (done) {
    return (
      <div className="flex flex-col items-center gap-3 py-4">
        <CheckCircle2 size={40} className="text-emerald-500" />
        <p className="text-sm font-semibold text-[#374151]">Great reset! You're ready.</p>
        <button
          onClick={onDone}
          className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#2F4731] text-white"
        >
          Continue Learning
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 py-4">
      <div className="relative flex items-center justify-center" style={{ width: 120, height: 120 }}>
        <motion.div
          animate={{ scale: circleScale * 1.3, opacity: 0.2 }}
          transition={{ duration: 0.5 }}
          className="absolute rounded-full bg-blue-300"
          style={{ width: 120, height: 120 }}
        />
        <motion.div
          animate={{ scale: circleScale }}
          transition={{ duration: 0.5 }}
          className="absolute rounded-full bg-blue-200"
          style={{ width: 100, height: 100 }}
        />
        <span className="relative text-sm font-bold text-blue-700">
          {phase.seconds - tick}s
        </span>
      </div>
      <p className="text-base font-semibold text-[#374151]">{phase.label}</p>
      <p className="text-[11px] text-[#9CA3AF]">Cycle {cycle + 1} of {CYCLES}</p>
      <div className="flex gap-1.5">
        {BREATH_PHASES.map((p, i) => (
          <div
            key={p.phase}
            className="w-2 h-2 rounded-full transition-colors"
            style={{ background: i === phaseIdx ? "#3B82F6" : "#E5E7EB" }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Ground mode ───────────────────────────────────────────────────────────────

function GroundMode({ onDone }: { onDone: () => void }) {
  const [stepIdx, setStepIdx] = useState(0);
  const totalBoxes = GROUND_STEPS.reduce((s, g) => s + g.count, 0);
  const [checked, setChecked] = useState<boolean[]>(Array(totalBoxes).fill(false));

  const stepOffset = GROUND_STEPS.slice(0, stepIdx).reduce((s, g) => s + g.count, 0);
  const step = GROUND_STEPS[stepIdx];
  const done = stepIdx >= GROUND_STEPS.length;

  const stepChecked = Array.from({ length: step?.count ?? 0 }, (_, i) => checked[stepOffset + i]);
  const allChecked = stepChecked.every(Boolean);

  if (done) {
    return (
      <div className="flex flex-col items-center gap-3 py-4">
        <CheckCircle2 size={40} className="text-emerald-500" />
        <p className="text-sm font-semibold text-[#374151]">You're grounded. Focus restored.</p>
        <button
          onClick={onDone}
          className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#2F4731] text-white"
        >
          Continue Learning
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{step.icon}</span>
        <p className="text-sm font-semibold text-[#374151]">{step.prompt}</p>
      </div>
      <div className="space-y-1.5">
        {Array.from({ length: step.count }).map((_, i) => (
          <label key={i} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={checked[stepOffset + i]}
              onChange={() => {
                const next = [...checked];
                next[stepOffset + i] = !next[stepOffset + i];
                setChecked(next);
              }}
              className="w-4 h-4 accent-emerald-500"
            />
            <span className={`text-xs ${checked[stepOffset + i] ? "line-through text-[#9CA3AF]" : "text-[#374151]"}`}>
              Thing {i + 1}
            </span>
          </label>
        ))}
      </div>
      <button
        onClick={() => setStepIdx((s) => s + 1)}
        disabled={!allChecked}
        className="mt-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-40"
        style={{
          background: allChecked ? "#2F4731" : "#E5E7EB",
          color: allChecked ? "#fff" : "#9CA3AF",
        }}
      >
        {stepIdx < GROUND_STEPS.length - 1 ? "Next →" : "All done →"}
      </button>
      <div className="flex gap-1 pt-1">
        {GROUND_STEPS.map((_, i) => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-colors"
            style={{
              background: i < stepIdx ? "#10B981" : i === stepIdx ? "#6EE7B7" : "#E5E7EB",
            }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Move mode ─────────────────────────────────────────────────────────────────

function MoveMode({ prompt, seconds, onDone }: { prompt: string; seconds: number; onDone: () => void }) {
  const [started, setStarted] = useState(false);
  const [remaining, setRemaining] = useState(seconds);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!started || done) return;
    const id = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) { setDone(true); return 0; }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [started, done]);

  if (done) {
    return (
      <div className="flex flex-col items-center gap-3 py-4">
        <CheckCircle2 size={40} className="text-emerald-500" />
        <p className="text-sm font-semibold text-[#374151]">Energy reset complete!</p>
        <button
          onClick={onDone}
          className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#2F4731] text-white"
        >
          Continue Learning
        </button>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="flex flex-col items-center gap-3 py-2">
        <p className="text-sm text-[#374151] text-center">{prompt}</p>
        <p className="text-[11px] text-[#9CA3AF]">{seconds} seconds</p>
        <button
          onClick={() => setStarted(true)}
          className="px-4 py-2 rounded-lg text-sm font-semibold bg-[#2F4731] text-white"
        >
          Start Timer
        </button>
      </div>
    );
  }

  const pct = (remaining / seconds) * 100;
  const C = 2 * Math.PI * 34;

  return (
    <div className="flex flex-col items-center gap-3 py-2">
      <p className="text-sm font-semibold text-[#374151] text-center">{prompt}</p>
      <div className="relative flex items-center justify-center" style={{ width: 80, height: 80 }}>
        <svg width="80" height="80" className="-rotate-90">
          <circle cx="40" cy="40" r="34" fill="none" stroke="#E5E7EB" strokeWidth="6" />
          <circle
            cx="40" cy="40" r="34" fill="none" stroke="#10B981"
            strokeWidth="6"
            strokeDasharray={C}
            strokeDashoffset={C * (1 - pct / 100)}
            style={{ transition: "stroke-dashoffset 1s linear" }}
          />
        </svg>
        <span className="absolute text-lg font-bold text-[#374151]">{remaining}</span>
      </div>
      <p className="text-[11px] text-[#9CA3AF]">seconds remaining</p>
    </div>
  );
}

// ── FocusReset ────────────────────────────────────────────────────────────────

export function FocusReset({
  mode = "breathe",
  message,
  move_prompt = "Stand up and do 10 jumping jacks!",
  move_seconds = 30,
  onComplete,
  onStateChange,
  state,
}: FocusResetProps) {
  const [completed, setCompleted] = useState(!!state?.completed);
  const [activeMode, setActiveMode] = useState<ResetMode>(mode);

  const handleDone = () => {
    setCompleted(true);
    onStateChange?.({ completed: true, mode: activeMode });
    onComplete?.();
  };

  const MODES: { key: ResetMode; label: string; icon: React.ReactNode; color: string }[] = [
    { key: "breathe", label: "Breathe", icon: <Wind size={12} />,     color: "#3B82F6" },
    { key: "ground",  label: "Ground",  icon: <Eye size={12} />,      color: "#10B981" },
    { key: "move",    label: "Move",    icon: <Activity size={12} />, color: "#F59E0B" },
  ];

  const modeColor = MODES.find((m) => m.key === activeMode)?.color ?? "#3B82F6";

  if (completed) {
    return (
      <div
        className="rounded-2xl px-4 py-3 flex items-center gap-2 text-sm"
        style={{ background: "#F0FDF4", border: "1.5px solid #BBF7D0" }}
      >
        <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
        <span className="text-[#374151]">Focus reset complete. Back to learning!</span>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: `1.5px solid ${modeColor}30`, background: "#FAFBFF" }}
    >
      <div
        className="px-4 py-2.5 flex items-center justify-between"
        style={{ background: `${modeColor}08`, borderBottom: `1px solid ${modeColor}15` }}
      >
        <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: modeColor }}>
          Focus Reset
        </span>
        <div className="flex gap-1">
          {MODES.map((m) => (
            <button
              key={m.key}
              onClick={() => setActiveMode(m.key)}
              className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-colors"
              style={{
                background: activeMode === m.key ? m.color : "transparent",
                color: activeMode === m.key ? "#fff" : "#9CA3AF",
              }}
            >
              {m.icon}{m.label}
            </button>
          ))}
        </div>
      </div>

      {message && (
        <div className="px-4 pt-3 pb-0">
          <p className="text-xs text-[#6B7280] leading-relaxed italic">"{message}"</p>
        </div>
      )}

      <div className="px-4 pb-4 pt-2">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeMode}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
          >
            {activeMode === "breathe" && <BreatheMode onDone={handleDone} />}
            {activeMode === "ground"  && <GroundMode  onDone={handleDone} />}
            {activeMode === "move"    && <MoveMode prompt={move_prompt} seconds={move_seconds} onDone={handleDone} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
