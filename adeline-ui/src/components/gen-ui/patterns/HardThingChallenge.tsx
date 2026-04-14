"use client";

/**
 * HardThingChallenge — Discipleship component for applying biblical principles.
 * Used in GENUI_ASSEMBLY blocks for discipleship tracks.
 */

import { useState } from "react";
import { Target, Heart, CheckCircle2 } from "lucide-react";

interface HardThingChallengeProps {
  state: Record<string, any>;
  onStateChange: (newState: Record<string, any>) => void;
  callbacks?: string[];
  // Component-specific props
  principle: string;
  scripture?: string;
  challenge: string;
  commitmentPrompt: string;
}

export function HardThingChallenge({
  state,
  onStateChange,
  callbacks = [],
  principle,
  scripture,
  challenge,
  commitmentPrompt,
}: HardThingChallengeProps) {
  const [progress, setProgress] = useState(state.progress || 0);
  const [committed, setCommitted] = useState(state.committed || false);
  const [reflection, setReflection] = useState(state.reflection || "");

  const handleCommit = () => {
    if (!committed && reflection.trim()) {
      setCommitted(true);
      onStateChange({ ...state, progress: 100, committed: true, reflection });
      if (callbacks.includes("onComplete")) {
        console.log("[HardThingChallenge] Commitment made");
      }
    }
  };

  const progressLevels = [
    { label: "Not Started", threshold: 0 },
    { label: "Considering", threshold: 25 },
    { label: "Planning", threshold: 50 },
    { label: "In Progress", threshold: 75 },
    { label: "Committed", threshold: 100 },
  ];

  const currentLevel = progressLevels.find((level) => progress >= level.threshold) || progressLevels[0];

  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: "#FFFEF7", border: "2px solid #78350F40" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🙏</span>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-[#78350F] text-white">
          Hard Thing Challenge
        </span>
      </div>

      <div className="space-y-2">
        {scripture && (
          <div className="p-3 rounded-lg bg-[#FEF3C7] border border-[#78350F]/20">
            <p className="text-xs text-[#78350F] italic">"{scripture}"</p>
          </div>
        )}
        <p className="text-sm font-bold text-[#78350F]">{principle}</p>
        <p className="text-sm text-[#2F4731] leading-relaxed">{challenge}</p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-[#374151]/60">
          <span>Progress</span>
          <span>{currentLevel.label}</span>
        </div>
        <div className="w-full h-2 rounded-full bg-[#E7DAC3] overflow-hidden">
          <div
            className="h-full bg-[#78350F] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {!committed ? (
        <div className="space-y-3">
          <p className="text-sm text-[#2F4731]">{commitmentPrompt}</p>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="Write your reflection and commitment..."
            className="w-full px-3 py-2 text-sm border border-[#E7DAC3] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#78350F] resize-none"
            rows={3}
          />
          <button
            onClick={handleCommit}
            disabled={!reflection.trim()}
            className="w-full px-4 py-2 text-sm font-semibold bg-[#78350F] text-white rounded-lg hover:bg-[#2F4731] disabled:opacity-40 transition-colors flex items-center justify-center gap-2"
          >
            <Heart size={16} />
            Commit to This Challenge
          </button>
        </div>
      ) : (
        <div className="p-4 rounded-lg bg-[#D4EDDA] border border-[#28A745] space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={20} className="text-green-600" />
            <p className="text-sm font-semibold text-[#155724]">Commitment Made</p>
          </div>
          <p className="text-xs text-[#155724] italic">{reflection}</p>
          <p className="text-xs text-[#155724]/70">
            Remember: Growth happens in the doing, not just the planning.
          </p>
        </div>
      )}
    </div>
  );
}
