"use client";

import { useState, useEffect } from "react";
import { fetchStudentState } from "@/lib/brain-client";
import type { StudentState, MasteryBand } from "@/lib/brain-client";

const BAND_COLOR: Record<MasteryBand, string> = {
  NOVICE:      "#94A3B8",
  DEVELOPING:  "#BD6809",
  PROFICIENT:  "#2F4731",
  ADVANCED:    "#9A3F4A",
};

const TRACK_LABELS: Record<string, string> = {
  TRUTH_HISTORY:        "History",
  CREATION_SCIENCE:     "Science",
  ENGLISH_LITERATURE:   "Literature",
  DISCIPLESHIP:         "Faith",
  GOVERNMENT_ECONOMICS: "Gov/Econ",
  HOMESTEADING:         "Homestead",
  HEALTH_NATUROPATHY:   "Health",
  JUSTICE_CHANGEMAKING: "Justice",
};

interface StudentStatusBarProps {
  studentId?: string;
}

export function StudentStatusBar({ studentId = "demo-student-001" }: StudentStatusBarProps) {
  const [state, setState] = useState<StudentState | null>(null);

  useEffect(() => {
    fetchStudentState(studentId)
      .then(setState)
      .catch(() => {/* silently fail — status bar is non-critical */});
  }, [studentId]);

  if (!state) return null;

  const tracks = Object.entries(state.tracks);

  return (
    <div className="flex flex-wrap gap-2">
      {tracks.map(([track, data]) => (
        <div
          key={track}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
          style={{
            background: `${BAND_COLOR[data.mastery_band]}18`,
            color: BAND_COLOR[data.mastery_band],
            border: `1px solid ${BAND_COLOR[data.mastery_band]}40`,
          }}
          title={`${data.mastery_band} · ${(data.mastery_score * 100).toFixed(0)}% mastery · ${data.lesson_count} lessons`}
        >
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: BAND_COLOR[data.mastery_band] }}
          />
          {TRACK_LABELS[track] ?? track}
          <span className="opacity-60">{Math.round(data.mastery_score * 100)}%</span>
        </div>
      ))}
    </div>
  );
}
