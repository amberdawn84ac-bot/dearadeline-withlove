"use client";

/**
 * SpacedRepWidget — SM-2 spaced repetition review session widget.
 *
 * Adapted from cascade-adeline/src/components/dashboard/SpacedRepWidget.tsx.
 * Connects to adeline-brain /lesson/scaffold for concept recall scoring.
 * Quality scale: 0=blank, 2=wrong, 3=hard, 4=good, 5=easy (SM-2 standard).
 */

import { useState, useEffect, useCallback } from "react";
import { Brain, CheckCircle, RefreshCw, ChevronRight } from "lucide-react";
import { useStudent } from "@/lib/useStudent";

interface DueReview {
  review_id: string;
  concept_id: string;
  concept_name: string;
  track: string;
  repetitions: number;
  overdue_days: number;
}

interface ReviewsApiResponse {
  reviews: DueReview[];
}

type ReviewPhase = "idle" | "showing" | "rating" | "done";

const QUALITY_LABELS = [
  { value: 0, label: "Blank",  styles: { background: "#FEF2F2", color: "#991B1B", border: "1px solid #FCA5A5" } },
  { value: 2, label: "Wrong",  styles: { background: "#FFF7ED", color: "#9A3412", border: "1px solid #FDC08E" } },
  { value: 3, label: "Hard",   styles: { background: "#FEFCE8", color: "#713F12", border: "1px solid #FDE68A" } },
  { value: 4, label: "Good",   styles: { background: "#EFF6FF", color: "#1E40AF", border: "1px solid #BFDBFE" } },
  { value: 5, label: "Easy",   styles: { background: "#F0FDF4", color: "#166534", border: "1px solid #86EFAC" } },
];

export function SpacedRepWidget() {
  const { student } = useStudent();
  const studentId = student?.id ?? '';
  const [dueReviews, setDueReviews] = useState<DueReview[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [phase, setPhase]           = useState<ReviewPhase>("idle");
  const [loading, setLoading]       = useState(true);
  const [reviewed, setReviewed]     = useState(0);

  const fetchDue = useCallback(async () => {
    if (!studentId) return;
    setLoading(true);
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
      const res = await fetch(`/brain/learning/reviews/${encodeURIComponent(studentId)}`, { headers });
      if (!res.ok) return;
      const data: ReviewsApiResponse = await res.json();
      setDueReviews(data.reviews ?? []);
    } catch {
      setDueReviews([]);
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => { fetchDue(); }, [fetchDue]);

  const current = dueReviews[currentIdx];

  const startReview = () => {
    if (!dueReviews.length) return;
    setCurrentIdx(0);
    setPhase("showing");
    setReviewed(0);
  };

  const revealAnswer = () => setPhase("rating");

  const submitRating = async (quality: number) => {
    if (!current) return;

    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    await fetch("/brain/learning/reviews", {
      method: "POST",
      headers,
      body: JSON.stringify({
        student_id: studentId,
        concept_id: current.concept_id,
        quality,
      }),
    }).catch(console.error);

    setReviewed((prev) => prev + 1);
    const next = currentIdx + 1;
    if (next < dueReviews.length) {
      setCurrentIdx(next);
      setPhase("showing");
    } else {
      setPhase("done");
    }
  };

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        className="rounded-2xl p-4 space-y-2"
        style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
      >
        <div className="flex items-center gap-2 text-[#2F4731] text-sm font-bold">
          <Brain size={15} /> Memory Review
        </div>
        <p className="text-xs text-[#2F4731]/40">Loading…</p>
      </div>
    );
  }

  // ── Nothing due ───────────────────────────────────────────────────────────────
  if (!dueReviews.length) {
    return (
      <div
        className="rounded-2xl p-4 space-y-3"
        style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
      >
        <div className="flex items-center gap-2 text-[#2F4731] text-sm font-bold">
          <Brain size={15} /> Memory Review
        </div>
        <div className="flex items-center gap-2 text-xs text-[#2F4731]/70">
          <CheckCircle size={13} style={{ color: "#22c55e" }} />
          Nothing due — all caught up! 🌿
        </div>
      </div>
    );
  }

  // ── Idle / start ─────────────────────────────────────────────────────────────
  if (phase === "idle") {
    return (
      <div
        className="rounded-2xl p-4 space-y-3"
        style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[#2F4731] text-sm font-bold">
            <Brain size={15} /> Memory Review
          </div>
          <span
            className="text-[11px] font-bold px-2 py-0.5 rounded-full text-white"
            style={{ background: "#BD6809" }}
          >
            {dueReviews.length} due
          </span>
        </div>
        <p className="text-xs text-[#2F4731]/65 leading-relaxed">
          Concepts due for spaced-repetition review using the SM-2 algorithm.
        </p>
        <button
          onClick={startReview}
          className="w-full flex items-center justify-center gap-2 text-sm font-bold text-white rounded-xl py-2 transition-opacity hover:opacity-90"
          style={{ background: "#2F4731" }}
        >
          Review Now <ChevronRight size={14} />
        </button>
      </div>
    );
  }

  // ── Done ──────────────────────────────────────────────────────────────────────
  if (phase === "done") {
    return (
      <div
        className="rounded-2xl p-4 space-y-3"
        style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
      >
        <div className="flex items-center gap-2 text-[#2F4731] text-sm font-bold">
          <Brain size={15} /> Memory Review
        </div>
        <div className="text-center py-2 space-y-1">
          <div className="text-2xl">🎉</div>
          <p className="text-sm font-bold text-[#2F4731]">
            {reviewed} concept{reviewed !== 1 ? "s" : ""} reviewed!
          </p>
          <p className="text-xs text-[#2F4731]/60">
            Intervals updated — next review scheduled automatically.
          </p>
        </div>
        <button
          onClick={() => { fetchDue(); setPhase("idle"); }}
          className="w-full flex items-center justify-center gap-2 text-xs font-bold text-[#2F4731] rounded-xl py-2 transition-opacity hover:opacity-80"
          style={{ background: "#E7DAC3" }}
        >
          <RefreshCw size={12} /> Refresh
        </button>
      </div>
    );
  }

  // ── Active review (showing / rating) ─────────────────────────────────────────
  return (
    <div
      className="rounded-2xl p-4 space-y-3"
      style={{ background: "#FFFEF7", border: "1px solid #E7DAC3" }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#2F4731] text-sm font-bold">
          <Brain size={15} /> Memory Review
        </div>
        <span className="text-[11px] text-[#2F4731]/50">
          {currentIdx + 1} / {dueReviews.length}
        </span>
      </div>

      {/* Concept card */}
      <div
        className="rounded-xl p-3 space-y-1"
        style={{ background: "#fff", border: "1px solid #E7DAC3" }}
      >
        <p className="text-sm font-bold text-[#2F4731]">
          {current?.concept_name}
          {(current?.overdue_days ?? 0) > 0 && (
            <span className="ml-2 text-[10px] font-normal" style={{ color: "#BD6809" }}>
              {Math.round(current.overdue_days)}d overdue
            </span>
          )}
        </p>
        <p className="text-[10px] text-[#2F4731]/50 uppercase tracking-wider">
          {current?.track?.replace(/_/g, " ")}
          {" · "}
          Review #{(current?.repetitions ?? 0) + 1}
        </p>
      </div>

      {phase === "showing" ? (
        <button
          onClick={revealAnswer}
          className="w-full text-sm font-bold text-white rounded-xl py-2 transition-opacity hover:opacity-90"
          style={{ background: "#BD6809" }}
        >
          How well did you remember?
        </button>
      ) : (
        <div className="space-y-2">
          <p className="text-[10px] text-[#2F4731]/50 text-center uppercase tracking-wider">
            Rate your recall:
          </p>
          <div className="grid grid-cols-5 gap-1.5">
            {QUALITY_LABELS.map(({ value, label, styles }) => (
              <button
                key={value}
                onClick={() => submitRating(value)}
                className="rounded-lg py-1.5 text-[11px] font-bold transition-opacity hover:opacity-80"
                style={styles}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
