"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  Users,
  TrendingUp,
  CheckCircle,
  GraduationCap,
} from "lucide-react";
import { fetchStudentState } from "@/lib/brain-client";
import type { StudentState, MasteryBand } from "@/lib/brain-client";

const BAND_COLOR: Record<MasteryBand, string> = {
  NOVICE:      "#94A3B8",
  DEVELOPING:  "#BD6809",
  PROFICIENT:  "#2F4731",
  ADVANCED:    "#9A3F4A",
};

const TRACK_LABELS: Record<string, string> = {
  CREATION_SCIENCE:     "Creation Science",
  HEALTH_NATUROPATHY:   "Health & Naturopathy",
  HOMESTEADING:         "Homesteading",
  GOVERNMENT_ECONOMICS: "Government & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Changemaking",
  DISCIPLESHIP:         "Discipleship",
  TRUTH_HISTORY:        "Truth & History",
  ENGLISH_LITERATURE:   "English & Literature",
  APPLIED_MATHEMATICS:  "Applied Mathematics",
  CREATIVE_ECONOMY:     "Creative Economy",
};

// Demo student list — replace with real auth-based lookup when auth is wired
const DEMO_STUDENTS = [
  { id: "demo-student-001", name: "Demo Student", gradeLevel: "8" },
];

type Panel = "overview" | "students";

export default function TeacherDashboard() {
  const [activePanel, setActivePanel] = useState<Panel>("overview");
  const [studentStates, setStudentStates] = useState<
    Array<{ id: string; name: string; gradeLevel: string; state: StudentState }>
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const results = await Promise.all(
        DEMO_STUDENTS.map(async (s) => {
          const state = await fetchStudentState(s.id, "ADMIN");
          return { ...s, state };
        })
      );
      setStudentStates(results);
    } catch {
      /* silently handle — show empty state */
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const totalLessons = studentStates.reduce((sum, s) => {
    return (
      sum +
      Object.values(s.state.tracks).reduce((t, tm) => t + tm.lesson_count, 0)
    );
  }, 0);

  const masteredStandards = studentStates.reduce((sum, s) => {
    return (
      sum +
      Object.values(s.state.tracks).reduce(
        (t, tm) => t + tm.mastered_standards_count,
        0
      )
    );
  }, 0);

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-[#FFFEF7] to-[#F5F0E8]">
      {/* Header */}
      <div className="p-6 border-b border-[#E7DAC3] bg-white/80 backdrop-blur-sm">
        <h1
          className="text-3xl font-bold text-[#2F4731]"
          style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
        >
          Teacher Dashboard
        </h1>
        <p className="text-sm text-[#2F4731]/60 italic mt-1">
          Monitor student mastery across the 10-Track Constitution
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-[#E7DAC3] bg-white/50">
        {(
          [
            { id: "overview", label: "Overview", icon: TrendingUp },
            { id: "students", label: "Students", icon: Users },
          ] as const
        ).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActivePanel(id)}
            className="flex-1 py-3 px-4 text-sm font-medium transition-colors flex items-center justify-center gap-2"
            style={
              activePanel === id
                ? {
                    background: "#2F4731",
                    color: "#FFFEF7",
                    borderBottom: "2px solid #BD6809",
                  }
                : { color: "#2F4731", background: "transparent" }
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-full gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
            <p className="text-[#2F4731]/60 italic">Loading student data…</p>
          </div>
        ) : (
          <>
            {activePanel === "overview" && (
              <div className="max-w-4xl mx-auto space-y-6">
                {/* Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    {
                      label: "Students",
                      value: DEMO_STUDENTS.length,
                      color: "#2F4731",
                    },
                    {
                      label: "Total Lessons",
                      value: totalLessons,
                      color: "#BD6809",
                    },
                    {
                      label: "Standards Mastered",
                      value: masteredStandards,
                      color: "#9A3F4A",
                    },
                  ].map(({ label, value, color }) => (
                    <div
                      key={label}
                      className="rounded-2xl p-5 bg-white border border-[#E7DAC3]"
                    >
                      <p
                        className="text-xs font-bold uppercase tracking-widest mb-2"
                        style={{ color, opacity: 0.7 }}
                      >
                        {label}
                      </p>
                      <p
                        className="text-4xl font-bold"
                        style={{ color }}
                      >
                        {value}
                      </p>
                    </div>
                  ))}
                </div>

                {/* 8-Track grid */}
                <div className="bg-white border border-[#E7DAC3] rounded-2xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-[#E7DAC3]">
                    <h2 className="font-bold text-[#2F4731]">
                      10-Track Mastery Overview
                    </h2>
                    <p className="text-sm text-[#2F4731]/60">
                      Average across all students
                    </p>
                  </div>
                  <div className="divide-y divide-[#E7DAC3]">
                    {Object.entries(TRACK_LABELS).map(([track, label]) => {
                      const scores = studentStates.map(
                        (s) => s.state.tracks[track]?.mastery_score ?? 0
                      );
                      const avg =
                        scores.length
                          ? scores.reduce((a, b) => a + b, 0) / scores.length
                          : 0;
                      const pct = Math.round(avg * 100);
                      const band: MasteryBand =
                        avg >= 0.85
                          ? "ADVANCED"
                          : avg >= 0.6
                          ? "PROFICIENT"
                          : avg >= 0.3
                          ? "DEVELOPING"
                          : "NOVICE";

                      return (
                        <div
                          key={track}
                          className="px-6 py-3 flex items-center gap-4"
                        >
                          <p className="text-sm font-medium text-[#2F4731] w-44 shrink-0">
                            {label}
                          </p>
                          <div className="flex-1 bg-[#F5F0E8] rounded-full h-2 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${pct}%`,
                                background: BAND_COLOR[band],
                              }}
                            />
                          </div>
                          <span
                            className="text-xs font-bold w-10 text-right"
                            style={{ color: BAND_COLOR[band] }}
                          >
                            {pct}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {activePanel === "students" && (
              <div className="max-w-4xl mx-auto space-y-4">
                {studentStates.length === 0 ? (
                  <div className="text-center py-16">
                    <CheckCircle className="w-12 h-12 text-[#2F4731]/20 mx-auto mb-3" />
                    <p className="text-[#2F4731]/60">No student data available.</p>
                  </div>
                ) : (
                  studentStates.map(({ id, name, gradeLevel, state }) => (
                    <div
                      key={id}
                      className="bg-white border border-[#E7DAC3] rounded-2xl overflow-hidden"
                    >
                      <div className="px-6 py-4 border-b border-[#E7DAC3] flex items-center justify-between">
                        <div>
                          <h3 className="font-bold text-[#2F4731]">{name}</h3>
                          <p className="text-xs text-[#2F4731]/60">
                            Grade {gradeLevel}
                          </p>
                        </div>
                        <GraduationCap className="w-5 h-5 text-[#BD6809]" />
                      </div>
                      <div className="px-6 py-4">
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(state.tracks).map(([track, tm]) => (
                            <div key={track} className="flex items-center gap-2">
                              <div
                                className="w-2 h-2 rounded-full shrink-0"
                                style={{ background: BAND_COLOR[tm.mastery_band] }}
                              />
                              <div className="min-w-0">
                                <p className="text-xs font-semibold text-[#2F4731] truncate">
                                  {TRACK_LABELS[track] ?? track}
                                </p>
                                <p
                                  className="text-[10px]"
                                  style={{ color: BAND_COLOR[tm.mastery_band] }}
                                >
                                  {tm.mastery_band} ·{" "}
                                  {Math.round(tm.mastery_score * 100)}% ·{" "}
                                  {tm.lesson_count} lessons
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
