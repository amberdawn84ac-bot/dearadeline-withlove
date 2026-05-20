"use client";

import type { LessonRenderMode } from "@/lib/brain-client";

const MODES: { value: LessonRenderMode; label: string; icon: string }[] = [
  { value: "standard_lesson",          label: "Standard",         icon: "📖" },
  { value: "visual_deep_dive",         label: "Visual Deep Dive", icon: "🔬" },
  { value: "sketchnote_infographic",   label: "Infographic",      icon: "🗺" },
  { value: "animated_sketchnote_lesson", label: "Living Sketchnote", icon: "✏️" },
];

interface Props {
  value: LessonRenderMode;
  onChange: (mode: LessonRenderMode) => void;
  disabled?: boolean;
}

export default function RenderModeSelector({ value, onChange, disabled }: Props) {
  return (
    <div
      className="inline-flex rounded-xl border border-[#BD6809]/30 overflow-hidden bg-[#FFFEF7]"
      role="group"
      aria-label="Lesson render mode"
    >
      {MODES.map((mode) => {
        const active = mode.value === value;
        return (
          <button
            key={mode.value}
            onClick={() => onChange(mode.value)}
            disabled={disabled}
            aria-pressed={active}
            className={`
              flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono transition-colors
              ${active
                ? "bg-[#3D1419] text-[#FFFEF7]"
                : "text-[#3D1419]/70 hover:bg-[#BD6809]/10 hover:text-[#3D1419]"
              }
              disabled:opacity-50 disabled:cursor-not-allowed
              border-r border-[#BD6809]/20 last:border-r-0
            `}
          >
            <span>{mode.icon}</span>
            <span className="hidden sm:inline">{mode.label}</span>
          </button>
        );
      })}
    </div>
  );
}
