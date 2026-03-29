"use client";

/**
 * ZPDProgress — Shows the student's Zone of Proximal Development state.
 * Displays grade level, overall mastery bar, credit hours per track,
 * and a "next challenge" prompt.
 */

import { useEffect, useState } from "react";
import { BookOpen, TrendingUp, Award } from "lucide-react";
import { fetchStudentState, type StudentState } from "@/lib/brain-client";

const TRACK_LABELS: Record<string, string> = {
  TRUTH_HISTORY:        "Truth & History",
  CREATION_SCIENCE:     "Creation Science",
  HOMESTEADING:         "Homesteading",
  GOVERNMENT_ECONOMICS: "Govt & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Changemaking",
  DISCIPLESHIP:         "Discipleship",
  HEALTH_NATUROPATHY:   "Health & Naturopathy",
  ENGLISH_LITERATURE:   "English Literature",
};

interface ZPDProgressProps {
  studentId: string;
}

function SkeletonBar() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-5 w-32 rounded bg-[#E7DAC3]" />
      <div className="h-3 w-full rounded bg-[#E7DAC3]" />
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-3 w-24 rounded bg-[#E7DAC3]" />
            <div className="flex-1 h-2 rounded bg-[#E7DAC3]" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ZPDProgress({ studentId }: ZPDProgressProps) {
  const [state, setState] = useState<StudentState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStudentState(studentId)
      .then(setState)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) {
    return (
      <div className="rounded-2xl p-5" style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}>
        <SkeletonBar />
      </div>
    );
  }

  if (error || !state) {
    return (
      <div className="rounded-2xl p-5 text-sm text-[#9A3F4A]" style={{ border: "1px solid #E7DAC3" }}>
        Could not load progress data.
      </div>
    );
  }

  // Aggregate verified_blocks_count proxy: sum of lesson_count across tracks
  const totalLessons = Object.values(state.tracks).reduce((sum, t) => sum + t.lesson_count, 0);
  const masteryPct = Math.min(100, Math.round((totalLessons / 20) * 100));
  const isReadyForChallenge = masteryPct >= 80;

  // Collect tracks that have any credit (lesson_count > 0)
  const activeTracks = Object.entries(state.tracks)
    .filter(([, data]) => data.lesson_count > 0)
    .sort(([, a], [, b]) => b.mastery_score - a.mastery_score);

  return (
    <div className="rounded-2xl p-5 space-y-4" style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}>
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#2F4731]">
          <TrendingUp size={16} />
          <span className="text-sm font-bold">Your Progress</span>
        </div>
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-full"
          style={{ background: "#BD6809", color: "#fff" }}
        >
          Grade {state.grade_level}
        </span>
      </div>

      {/* Mastery bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-[#2F4731]">
          <span className="font-semibold">Mastery</span>
          <span className="font-bold text-[#BD6809]">{masteryPct}%</span>
        </div>
        <div className="w-full h-3 rounded-full bg-[#F3F0EA] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${masteryPct}%`,
              background: masteryPct >= 80 ? "#2F4731" : "#BD6809",
            }}
          />
        </div>
        <p className="text-[10px] text-[#2F4731]/60">
          {isReadyForChallenge
            ? "You're ready for harder content. Push deeper into a track."
            : `Ready for harder content when bar hits 80% — ${80 - masteryPct}% to go.`}
        </p>
      </div>

      {/* Per-track credit hours */}
      {activeTracks.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[#2F4731]">
            <Award size={13} />
            <span className="text-xs font-semibold">Credits by Track</span>
          </div>
          <div className="space-y-1.5">
            {activeTracks.map(([track, data]) => {
              const pct = Math.round(data.mastery_score * 100);
              return (
                <div key={track} className="flex items-center gap-2">
                  <span className="text-[11px] text-[#2F4731]/70 w-32 shrink-0 truncate">
                    {TRACK_LABELS[track] ?? track}
                  </span>
                  <div className="flex-1 h-1.5 rounded-full bg-[#F3F0EA] overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${pct}%`, background: "#9A3F4A" }}
                    />
                  </div>
                  <span className="text-[10px] font-bold text-[#9A3F4A] w-8 text-right shrink-0">
                    {data.lesson_count}h
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTracks.length === 0 && (
        <div className="flex items-center gap-2 text-[#2F4731]/50 text-xs">
          <BookOpen size={13} />
          <span>Start your first lesson to see track progress here.</span>
        </div>
      )}
    </div>
  );
}
