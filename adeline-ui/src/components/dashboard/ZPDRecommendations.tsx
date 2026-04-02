"use client";

/**
 * ZPDRecommendations — Shows a student's top Zone of Proximal Development concepts.
 *
 * Adapted from cascade-adeline/src/components/learning/ZPDRecommendations.tsx.
 * Consumes the adeline-brain /lesson/student-state endpoint which returns
 * per-track mastery scores, then surfaces the tracks with the highest
 * learning opportunity (high enough prereq readiness, not yet mastered).
 */

import { useEffect, useState } from "react";
import { Target, Zap, TrendingUp } from "lucide-react";
import { fetchStudentState, type StudentState, type Track } from "@/lib/brain-client";

interface ZPDConcept {
  track: Track;
  label: string;
  masteryScore: number;
  mastery_band: string;
  lesson_count: number;
  mastered_standards_count: number;
}

const TRACK_LABELS: Record<Track, string> = {
  TRUTH_HISTORY:        "Truth & History",
  CREATION_SCIENCE:     "Creation Science",
  HOMESTEADING:         "Homesteading",
  GOVERNMENT_ECONOMICS: "Govt & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Changemaking",
  DISCIPLESHIP:         "Discipleship",
  HEALTH_NATUROPATHY:   "Health & Naturopathy",
  ENGLISH_LITERATURE:   "English Literature",
  APPLIED_MATHEMATICS:  "Applied Mathematics",
  CREATIVE_ECONOMY:     "Creative Economy",
};

const TRACK_COLORS: Record<Track, string> = {
  TRUTH_HISTORY:        "#3D1419",
  CREATION_SCIENCE:     "#2F4731",
  HOMESTEADING:         "#2F4731",
  GOVERNMENT_ECONOMICS: "#BD6809",
  JUSTICE_CHANGEMAKING: "#9A3F4A",
  DISCIPLESHIP:         "#4F46E5",
  HEALTH_NATUROPATHY:   "#047857",
  ENGLISH_LITERATURE:   "#7C3AED",
  APPLIED_MATHEMATICS:  "#0369A1",
  CREATIVE_ECONOMY:     "#B45309",
};

const BAND_LABEL: Record<string, string> = {
  NOVICE:      "Beginning",
  DEVELOPING:  "Developing",
  PROFICIENT:  "Proficient",
  ADVANCED:    "Advanced",
};

interface ZPDRecommendationsProps {
  studentId: string;
  limit?: number;
}

export function ZPDRecommendations({ studentId, limit = 3 }: ZPDRecommendationsProps) {
  const [concepts, setConcepts] = useState<ZPDConcept[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  useEffect(() => {
    fetchStudentState(studentId)
      .then((state: StudentState) => {
        const zpd: ZPDConcept[] = Object.entries(state.tracks)
          .map(([track, data]) => ({
            track: track as Track,
            label: TRACK_LABELS[track as Track] ?? track,
            masteryScore:             data.mastery_score,
            mastery_band:             data.mastery_band,
            lesson_count:             data.lesson_count,
            mastered_standards_count: data.mastered_standards_count,
          }))
          // ZPD = not mastered yet (< 0.8) but has started (lesson_count > 0) OR untouched
          .filter((c) => c.masteryScore < 0.8)
          // Sort by: started tracks first, then by score ascending (most room to grow)
          .sort((a, b) => {
            const aStarted = a.lesson_count > 0 ? 1 : 0;
            const bStarted = b.lesson_count > 0 ? 1 : 0;
            if (aStarted !== bStarted) return bStarted - aStarted;
            return a.masteryScore - b.masteryScore;
          })
          .slice(0, limit);
        setConcepts(zpd);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [studentId, limit]);

  if (loading) {
    return (
      <div
        className="rounded-2xl p-5 space-y-3"
        style={{ background: "#F8FFF9", border: "1px solid #2F473120" }}
      >
        <div className="flex items-center gap-2 text-[#2F4731]">
          <Target size={16} />
          <span className="text-sm font-bold">Your Learning Zone</span>
        </div>
        <p className="text-xs text-[#2F4731]/50">Loading your ZPD…</p>
      </div>
    );
  }

  if (error) return null;

  if (!concepts.length) {
    return (
      <div
        className="rounded-2xl p-5 space-y-2"
        style={{ background: "#F8FFF9", border: "1px solid #2F473120" }}
      >
        <div className="flex items-center gap-2 text-[#2F4731]">
          <Target size={16} />
          <span className="text-sm font-bold">Your Learning Zone</span>
        </div>
        <p className="text-xs text-[#2F4731]/60">
          Outstanding! All 8 tracks show strong mastery. Keep exploring deeper concepts.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl p-5 space-y-4"
      style={{ background: "#F8FFF9", border: "1px solid #2F473120" }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#2F4731]">
          <Target size={16} />
          <span className="text-sm font-bold">Your Learning Zone</span>
        </div>
        <span className="text-[10px] text-[#2F4731]/40 uppercase tracking-wider">
          ZPD · {concepts.length} tracks
        </span>
      </div>

      <div className="space-y-3">
        {concepts.map((concept, i) => {
          const color = TRACK_COLORS[concept.track];
          const pct   = Math.round(concept.masteryScore * 100);
          return (
            <div
              key={concept.track}
              className="rounded-xl p-3 space-y-2"
              style={{ background: "#fff", border: `1px solid ${color}20` }}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                  style={{ background: color }}
                >
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-[#2F4731] truncate">{concept.label}</p>
                  <p className="text-[10px] text-[#2F4731]/50">
                    {BAND_LABEL[concept.mastery_band] ?? concept.mastery_band}
                    {concept.lesson_count > 0 && ` · ${concept.lesson_count} lesson${concept.lesson_count !== 1 ? "s" : ""}`}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-xs font-bold" style={{ color }}>
                    {pct}%
                  </span>
                </div>
              </div>

              {/* Mastery progress bar */}
              <div className="w-full h-1.5 bg-[#F3F4F6] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, background: color }}
                />
              </div>

              <div className="flex items-center gap-3 text-[10px] text-[#2F4731]/50">
                <span className="flex items-center gap-1">
                  <Zap size={9} />
                  {concept.mastered_standards_count} standard{concept.mastered_standards_count !== 1 ? "s" : ""} mastered
                </span>
                <span className="flex items-center gap-1 ml-auto">
                  <TrendingUp size={9} />
                  {Math.round((1 - concept.masteryScore) * 100)}% growth potential
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-[10px] text-[#2F4731]/40 italic">
        ZPD: concepts with sufficient prereq mastery but not yet achieved — ideal for next learning.
      </p>
    </div>
  );
}
