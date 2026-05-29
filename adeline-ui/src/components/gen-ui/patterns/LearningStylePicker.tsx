"use client";

import { useState } from "react";
import { motion } from "framer-motion";

interface LearningStylePickerProps {
  studentId: string;
  lessonTopic?: string;
  onComplete?: (modality: string) => void;
}

const CHOICES = [
  {
    modality: "visual",
    emoji: "🎨",
    label: "Watch & See",
    description: "Animations, diagrams, and visual stories help me most",
  },
  {
    modality: "auditory",
    emoji: "🎧",
    label: "Listen & Learn",
    description: "Narration, explanations, and talking it through",
  },
  {
    modality: "kinesthetic",
    emoji: "🛠️",
    label: "Do & Explore",
    description: "Hands-on activities, simulations, and building things",
  },
  {
    modality: "reading",
    emoji: "📖",
    label: "Read & Think",
    description: "Reading carefully and working through ideas in my head",
  },
];

export function LearningStylePicker({ studentId, lessonTopic, onComplete }: LearningStylePickerProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handlePick(modality: string) {
    setSelected(modality);
    setSaving(true);
    try {
      await fetch(`/api/students/${studentId}/modality-preference`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ modality }),
      });
      setSaved(true);
      onComplete?.(modality);
    } catch {
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  if (saved) {
    const choice = CHOICES.find((c) => c.modality === selected);
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center"
      >
        <p className="text-2xl mb-2">{choice?.emoji}</p>
        <p className="font-semibold text-emerald-800">Got it — {choice?.label}!</p>
        <p className="text-sm text-emerald-600 mt-1">
          Adeline will start shaping your lessons around how you learn best.
        </p>
      </motion.div>
    );
  }

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 space-y-4">
      <div>
        <p className="font-semibold text-amber-900 text-base">
          Quick question — how did today&apos;s lesson land?
        </p>
        {lessonTopic && (
          <p className="text-sm text-amber-700 mt-0.5">
            Which part of <span className="font-medium">{lessonTopic}</span> helped you most?
          </p>
        )}
        {!lessonTopic && (
          <p className="text-sm text-amber-700 mt-0.5">
            Which style of learning clicks best for you?
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {CHOICES.map((c) => (
          <motion.button
            key={c.modality}
            whileTap={{ scale: 0.97 }}
            disabled={saving}
            onClick={() => handlePick(c.modality)}
            className={`rounded-xl border-2 p-4 text-left transition-all ${
              selected === c.modality
                ? "border-amber-500 bg-amber-100"
                : "border-amber-200 bg-white hover:border-amber-400 hover:bg-amber-50"
            }`}
          >
            <p className="text-xl mb-1">{c.emoji}</p>
            <p className="font-semibold text-amber-900 text-sm">{c.label}</p>
            <p className="text-xs text-amber-700 mt-0.5 leading-snug">{c.description}</p>
          </motion.button>
        ))}
      </div>

      <p className="text-xs text-amber-600 text-center">
        You can always change this later. Adeline will keep learning from you either way.
      </p>
    </div>
  );
}
