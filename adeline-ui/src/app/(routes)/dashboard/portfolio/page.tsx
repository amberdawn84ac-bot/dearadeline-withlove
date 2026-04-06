"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, Loader2, BookOpen, Hammer, Zap } from "lucide-react";
import {
  downloadMasteryPortfolio,
  fetchStudentState,
  listActivities,
} from "@/lib/brain-client";
import type { ActivityEntry, Track } from "@/lib/brain-client";

const TRACK_LABELS: Record<string, string> = {
  CREATION_SCIENCE: "Creation Science",
  HEALTH_NATUROPATHY: "Health & Naturopathy",
  HOMESTEADING: "Homesteading",
  GOVERNMENT_ECONOMICS: "Government & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Changemaking",
  DISCIPLESHIP: "Discipleship",
  TRUTH_HISTORY: "Truth & History",
  ENGLISH_LITERATURE: "English & Literature",
  APPLIED_MATHEMATICS: "Applied Mathematics",
  CREATIVE_ECONOMY: "Creative Economy",
};

const TRACK_COLOR: Record<string, string> = {
  CREATION_SCIENCE: "#166534",
  HEALTH_NATUROPATHY: "#9A3F4A",
  HOMESTEADING: "#166534",
  GOVERNMENT_ECONOMICS: "#2F4731",
  JUSTICE_CHANGEMAKING: "#9A3F4A",
  DISCIPLESHIP: "#BD6809",
  TRUTH_HISTORY: "#2F4731",
  ENGLISH_LITERATURE: "#BD6809",
  APPLIED_MATHEMATICS: "#2F4731",
  CREATIVE_ECONOMY: "#BD6809",
};

// TODO: Replace with actual auth context
const STUDENT_ID = "demo-student-001";

export default function PortfolioPage() {
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [totalCredits, setTotalCredits] = useState(0);
  const [trackCount, setTrackCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [actData, stateData] = await Promise.allSettled([
        listActivities(STUDENT_ID),
        fetchStudentState(STUDENT_ID),
      ]);

      if (actData.status === "fulfilled") {
        setActivities(actData.value.activities);
        setTotalCredits(actData.value.total_credits);
      }

      if (stateData.status === "fulfilled") {
        const activeTracks = Object.values(stateData.value.tracks).filter(
          (t) => t.lesson_count > 0,
        ).length;
        setTrackCount(activeTracks);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await downloadMasteryPortfolio(STUDENT_ID);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `adeline-portfolio-${STUDENT_ID}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to download portfolio.",
      );
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="px-6 py-8 border-b border-[#E7DAC3] flex items-start justify-between">
          <div>
            <h1
              className="text-4xl font-bold text-[#2F4731]"
              style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
            >
              My Portfolio
            </h1>
            <p className="text-sm text-[#2F4731]/60 mt-2">
              What you&apos;ve made, built, grown, published, and sold.
            </p>
          </div>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white transition-all hover:brightness-110 disabled:opacity-50"
            style={{ background: "#2F4731" }}
          >
            {downloading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Download PDF
          </button>
        </div>

        {/* Stats */}
        <div className="px-6 py-6 grid grid-cols-3 gap-4">
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-[#2F4731]/50 mb-1">
              Accomplishments
            </p>
            <p className="text-3xl font-bold text-[#2F4731]">
              {activities.length}
            </p>
          </div>
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-[#BD6809]/70 mb-1">
              Credits Earned
            </p>
            <p className="text-3xl font-bold text-[#BD6809]">
              {totalCredits.toFixed(1)}
            </p>
          </div>
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-[#9A3F4A]/70 mb-1">
              Active Tracks
            </p>
            <p className="text-3xl font-bold text-[#9A3F4A]">{trackCount}</p>
          </div>
        </div>

        {/* Content */}
        <div className="px-6">
          {loading && (
            <div className="flex items-center justify-center py-16 gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-[#BD6809]" />
              <p className="text-[#2F4731]/60 italic">
                Loading your portfolio...
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border-2 border-[#9A3F4A]/30 bg-[#FEF2F2] p-6 text-center mb-6">
              <p className="text-sm font-bold text-[#9A3F4A]">{error}</p>
              <button
                onClick={loadPortfolio}
                className="mt-3 text-xs font-bold text-[#9A3F4A] underline"
              >
                Try again
              </button>
            </div>
          )}

          {!loading && activities.length === 0 && !error && (
            <div className="text-center py-16 space-y-4">
              <p className="text-5xl">🌱</p>
              <h2
                className="text-2xl font-bold text-[#2F4731]"
                style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
              >
                Your portfolio is waiting
              </h2>
              <p className="text-sm text-[#2F4731]/60 max-w-md mx-auto">
                Complete projects, finish books, and report real-world activities
                to build your record of accomplishments. Each one earns credit
                on your transcript.
              </p>
            </div>
          )}

          {!loading && activities.length > 0 && (
            <div className="space-y-3">
              {activities.map((act) => {
                const color =
                  TRACK_COLOR[act.primary_track] ?? "#2F4731";
                const label =
                  TRACK_LABELS[act.primary_track] ?? act.primary_track;

                return (
                  <div
                    key={act.activity_id}
                    className="rounded-2xl border border-[#E7DAC3] bg-white p-5 flex items-start gap-4"
                  >
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white"
                      style={{ background: color }}
                    >
                      {act.credit_type === "CREATIVE" ? (
                        <Hammer className="w-5 h-5" />
                      ) : act.credit_type === "HOMESTEAD" ? (
                        <Zap className="w-5 h-5" />
                      ) : (
                        <BookOpen className="w-5 h-5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-[#2F4731] text-sm">
                        {act.course_title}
                      </h3>
                      <p className="text-xs text-[#2F4731]/60 mt-0.5 line-clamp-2">
                        {act.activity_description}
                      </p>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span
                          className="text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full text-white"
                          style={{ background: color }}
                        >
                          {label}
                        </span>
                        <span className="text-[10px] text-[#2F4731]/40">
                          {act.credit_hours} credits
                        </span>
                        <span className="text-[10px] text-[#2F4731]/40">
                          {new Date(act.sealed_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
