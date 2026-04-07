"use client";

import { useState } from "react";
import { useLesson } from "@/hooks/useLesson";
import LessonRenderer from "@/components/lessons/LessonRenderer";
import { useAuth } from "@/lib/useAuth";
import { BotanicalDivider } from "@/components/icons";
import type { Track } from "@/lib/brain-client";

// ── Track config ──────────────────────────────────────────────────────────────

const TRACKS: { id: Track; label: string; color: string }[] = [
  { id: "CREATION_SCIENCE",     label: "Creation & Science",      color: "#6B7F5E" }, // sage
  { id: "HEALTH_NATUROPATHY",   label: "Health & Naturopathy",    color: "#8C6D3F" }, // ochre
  { id: "HOMESTEADING",         label: "Homesteading",            color: "#6B7F5E" }, // sage
  { id: "GOVERNMENT_ECONOMICS", label: "Gov & Economics",         color: "#4A5E72" }, // slate
  { id: "JUSTICE_CHANGEMAKING", label: "Justice & Change",        color: "#4A5E72" }, // slate
  { id: "DISCIPLESHIP",         label: "Discipleship",            color: "#6B4E6B" }, // plum
  { id: "TRUTH_HISTORY",        label: "Truth-Based History",     color: "#9A3F4A" }, // paradise
  { id: "ENGLISH_LITERATURE",   label: "English & Literature",    color: "#3D1419" }, // fuschia
];

const GRADES = ["K","1","2","3","4","5","6","7","8","9","10","11","12"];

// ── Skeleton loader ───────────────────────────────────────────────────────────

function LessonSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="sketch-card"
          style={{ height: i === 1 ? "8rem" : "6rem", opacity: 1 - i * 0.2 }}
        />
      ))}
    </div>
  );
}

// ── Opportunities sidebar ─────────────────────────────────────────────────────

function OpportunitiesPanel({ track }: { track: Track }) {
  const SAMPLE = [
    {
      id: "opp-001",
      title: "Oklahoma History Center Field Study",
      location: "Oklahoma City, OK",
      track: "TRUTH_HISTORY" as Track,
      grades: ["5","6","7","8"],
      description: "Guided tour of Oklahoma Territory documents, land run maps, and Indigenous nation treaties.",
    },
    {
      id: "opp-002",
      title: "Kerr Center Sustainable Agriculture Tour",
      location: "Poteau, OK",
      track: "HOMESTEADING" as Track,
      grades: ["3","4","5","6"],
      description: "Hands-on homestead science — soil health, seed saving, and water stewardship.",
    },
  ].filter((o) => o.track === track || true); // show all, filtered by track in production

  return (
    <aside className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="font-sketch text-xs bg-fuschia text-parchment-50 px-2 py-0.5 rounded-sm uppercase tracking-widest">
          Admin
        </span>
        <p className="font-sketch text-sm text-fuschia">Local Opportunities</p>
      </div>
      {SAMPLE.map((opp) => (
        <div key={opp.id} className="sketch-card space-y-1 text-sm">
          <p className="font-sketch text-paradise">{opp.title}</p>
          <p className="font-mono text-xs text-fuschia/50">{opp.location}</p>
          <p className="font-body text-xs text-fuschia/70 leading-relaxed">{opp.description}</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {opp.grades.map((g) => (
              <span key={g} className="font-mono text-xs bg-parchment-200 text-fuschia/60 px-1.5 py-0.5 rounded-sm">
                Gr {g}
              </span>
            ))}
          </div>
        </div>
      ))}
    </aside>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function LessonPage() {
  const { user } = useAuth();
  const { lesson, loading, error, generate, reset } = useLesson();

  const [topic, setTopic]         = useState("");
  const [track, setTrack]         = useState<Track>("TRUTH_HISTORY");
  const [grade, setGrade]         = useState("8");
  const [isHomestead, setIsHomestead] = useState(false);
  const [showScores, setShowScores]   = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;
    generate({
      student_id: user?.id ?? '',
      topic: topic.trim(),
      track,
      grade_level: grade,
      is_homestead: isHomestead,
    });
  }

  // Track badges from lesson OAS standards
  const activeTrackIds = lesson
    ? Array.from(new Set([lesson.track, ...TRACKS.map((t) => t.id).filter(() => false)]))
    : [];

  return (
    <div className="space-y-8">

      {/* ── Search bar ───────────────────────────────────────────── */}
      <section className="sketch-card space-y-4">
        <div className="space-y-0.5">
          <h2 className="font-sketch text-xl text-fuschia">Ask Adeline</h2>
          <p className="font-body text-xs text-fuschia/50">
            Enter a topic or learning objective. Adeline will retrieve verified primary sources.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Topic input */}
          <div className="relative">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Homesteading stewardship requires three pillars: soil health, water conservation, and crop rotation."
              className="w-full bg-parchment-50 border-2 border-fuschia font-body text-sm text-fuschia
                         placeholder:text-fuschia/30 px-4 py-3 pr-12
                         focus:outline-none focus:border-paradise transition-colors"
            />
            {topic && (
              <button
                type="button"
                onClick={() => { setTopic(""); reset(); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-fuschia/40 hover:text-fuschia font-sketch text-lg"
              >
                ×
              </button>
            )}
          </div>

          {/* Controls row */}
          <div className="flex flex-wrap gap-3 items-end">
            {/* Track selector */}
            <div className="space-y-1">
              <label className="font-sketch text-xs text-fuschia/60 uppercase tracking-widest">Track</label>
              <select
                value={track}
                onChange={(e) => setTrack(e.target.value as Track)}
                className="bg-parchment-50 border-2 border-fuschia font-body text-xs text-fuschia
                           px-2 py-1.5 focus:outline-none focus:border-paradise"
              >
                {TRACKS.map((t) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Grade selector */}
            <div className="space-y-1">
              <label className="font-sketch text-xs text-fuschia/60 uppercase tracking-widest">Grade</label>
              <select
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="bg-parchment-50 border-2 border-fuschia font-body text-xs text-fuschia
                           px-2 py-1.5 focus:outline-none focus:border-paradise"
              >
                {GRADES.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>

            {/* Homestead toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => setIsHomestead(!isHomestead)}
                className={`w-10 h-5 border-2 border-fuschia relative transition-colors ${isHomestead ? "bg-sage" : "bg-parchment-50"}`}
              >
                <div className={`absolute top-0.5 w-3.5 h-3.5 bg-fuschia transition-all ${isHomestead ? "left-4" : "left-0.5"}`} />
              </div>
              <span className="font-sketch text-xs text-fuschia/70">Homestead Lens</span>
            </label>

            {/* Score debug toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showScores}
                onChange={(e) => setShowScores(e.target.checked)}
                className="accent-paradise"
              />
              <span className="font-sketch text-xs text-fuschia/50">Show scores</span>
            </label>

            <button
              type="submit"
              disabled={loading || !topic.trim()}
              className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed ml-auto"
            >
              {loading ? "Retrieving..." : "Generate Lesson"}
            </button>
          </div>
        </form>
      </section>

      {/* ── Track badges (active lesson) ─────────────────────────── */}
      {lesson && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest mr-1">Tracks fulfilled:</span>
          {TRACKS.filter((t) => t.id === lesson.track).map((t) => (
            <span
              key={t.id}
              className="font-sketch text-xs px-2 py-0.5 rounded-full text-parchment-50 uppercase tracking-wide"
              style={{ background: t.color }}
            >
              {t.label}
            </span>
          ))}
          {lesson.oas_standards?.map((s) => (
            <span
              key={s.standard_id}
              className="font-mono text-xs bg-parchment-200 text-fuschia/60 px-2 py-0.5 rounded-sm border border-fuschia/20"
              title={s.text}
            >
              {s.standard_id} · Gr {s.grade}
            </span>
          ))}
        </div>
      )}

      {/* ── States ───────────────────────────────────────────────── */}
      {error && (
        <div className="witness-alert rounded">
          <p className="font-sketch text-sm">Could not reach adeline-brain</p>
          <p className="font-mono text-xs mt-1 opacity-70">{error}</p>
        </div>
      )}

      {loading && <LessonSkeleton />}

      {/* ── Lesson + sidebar ─────────────────────────────────────── */}
      {lesson && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-8">
          <LessonRenderer lesson={lesson} isHomestead={isHomestead} showScores={showScores} />

          <div className="space-y-6">
            <BotanicalDivider />
            <OpportunitiesPanel track={lesson.track} />
          </div>
        </div>
      )}

      {/* ── Empty prompt ─────────────────────────────────────────── */}
      {!lesson && !loading && !error && (
        <div className="text-center py-16 space-y-3 opacity-50">
          <p className="font-sketch text-3xl text-fuschia">Ask Adeline a question.</p>
          <p className="font-body text-sm text-fuschia/60">
            She will search the archives and show only what can be verified.
          </p>
        </div>
      )}

    </div>
  );
}
