"use client";

/**
 * /dashboard — 8-Track Progress Dashboard
 *
 * Fetches track_progress + recent activity from adeline-brain.
 * Falls back gracefully when the brain is offline (demo mode).
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchTrackProgress } from "@/lib/brain-client";

// ── Track configuration ───────────────────────────────────────────────────────

type TrackId =
  | "CREATION_SCIENCE"
  | "HEALTH_NATUROPATHY"
  | "HOMESTEADING"
  | "GOVERNMENT_ECONOMICS"
  | "JUSTICE_CHANGEMAKING"
  | "DISCIPLESHIP"
  | "TRUTH_HISTORY"
  | "ENGLISH_LITERATURE";

const TRACKS: { id: TrackId; label: string; num: number; color: string }[] = [
  { id: "CREATION_SCIENCE",     label: "God's Creation & Science",    num: 1, color: "#9A3F4A" }, // Paradise
  { id: "HEALTH_NATUROPATHY",   label: "Health & Naturopathy",        num: 2, color: "#BD6809" }, // Papaya
  { id: "HOMESTEADING",         label: "Homesteading & Stewardship",  num: 3, color: "#3D1419" }, // Fuschia
  { id: "GOVERNMENT_ECONOMICS", label: "Government & Economics",      num: 4, color: "#9A3F4A" },
  { id: "JUSTICE_CHANGEMAKING", label: "Justice & Change-making",     num: 5, color: "#BD6809" },
  { id: "DISCIPLESHIP",         label: "Discipleship & Discernment",  num: 6, color: "#3D1419" },
  { id: "TRUTH_HISTORY",        label: "Truth-Based History",         num: 7, color: "#9A3F4A" },
  { id: "ENGLISH_LITERATURE",   label: "English & Literature",        num: 8, color: "#BD6809" },
];

const STUDENT_ID = "demo-student-001";
const BRAIN_URL = "/brain";

async function downloadTranscript() {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/generate/${STUDENT_ID}`,
    { headers: { "X-User-Role": "STUDENT" } },
  );
  if (!res.ok) throw new Error(`Transcript error: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `adeline-transcript-${STUDENT_ID}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

// Soft maximum — circle fills at MAX_LESSONS lessons
const MAX_LESSONS = 10;

// ── Progress Circle (SVG) ─────────────────────────────────────────────────────

function ProgressCircle({
  count,
  color,
  label,
  num,
}: {
  count: number;
  color: string;
  label: string;
  num: number;
}) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const filled = Math.min(count / MAX_LESSONS, 1);
  const dashOffset = circumference * (1 - filled);

  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="relative w-24 h-24">
        <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
          {/* Track background ring */}
          <circle
            cx="48"
            cy="48"
            r={radius}
            fill="none"
            stroke="#F0D9B0"
            strokeWidth="6"
          />
          {/* Progress arc */}
          <circle
            cx="48"
            cy="48"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            transform="rotate(-90 48 48)"
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        {/* Center count */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-sketch text-xl leading-none"
            style={{ color }}
          >
            {count}
          </span>
          <span className="font-mono text-xs" style={{ color, opacity: 0.5 }}>
            sealed
          </span>
        </div>
      </div>
      <p
        className="font-sketch text-xs leading-snug max-w-[7rem]"
        style={{ color }}
      >
        {num}. {label}
      </p>
    </div>
  );
}

// ── Recent Activity ───────────────────────────────────────────────────────────

interface RecentEntry {
  lesson_id: string;
  track: string;
  completed_blocks: number;
  sealed_at: string | null;
}

function RecentActivity({ entries }: { entries: RecentEntry[] }) {
  if (!entries.length) {
    return (
      <p className="font-body text-xs text-fuschia/40 italic">
        No lessons sealed yet. Open the Journal to begin.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((e) => {
        const track = TRACKS.find((t) => t.id === e.track);
        const date = e.sealed_at
          ? new Date(e.sealed_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })
          : "—";
        return (
          <div
            key={e.lesson_id}
            className="flex items-center justify-between gap-4 border-b border-fuschia/10 pb-2"
          >
            <div className="space-y-0.5">
              <p
                className="font-sketch text-xs"
                style={{ color: track?.color ?? "#3D1419" }}
              >
                {track?.label ?? e.track}
              </p>
              <p className="font-mono text-xs text-fuschia/40">
                {e.completed_blocks} verified block{e.completed_blocks !== 1 ? "s" : ""}
              </p>
            </div>
            <span className="font-mono text-xs text-fuschia/30 shrink-0">{date}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Dashboard Page ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [progress, setProgress] = useState<Record<string, number>>({});
  const [recent, setRecent] = useState<RecentEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [prog, rec] = await Promise.all([
          fetchTrackProgress(STUDENT_ID),
          fetch(`${BRAIN_URL}/journal/recent/${STUDENT_ID}`, {
            headers: { "X-User-Role": "STUDENT" },
            cache: "no-store",
          }).then((r) => (r.ok ? r.json() : { entries: [] })),
        ]);
        setProgress(prog);
        setRecent((rec as { entries: RecentEntry[] }).entries ?? []);
      } catch {
        setOffline(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const totalSealed = Object.values(progress).reduce((a: number, b: number) => a + b, 0);
  const tracksActive = Object.keys(progress).length;

  async function handleDownload() {
    setDownloading(true);
    setDownloadError("");
    try {
      await downloadTranscript();
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-10 max-w-4xl mx-auto">

      {/* Header */}
      <section className="flex items-center justify-between flex-wrap gap-4">
        <div className="space-y-0.5">
          <p className="font-sketch text-xs text-papaya uppercase tracking-widest">
            Student Transcript
          </p>
          <h2 className="font-sketch text-2xl text-fuschia">8-Track Progress</h2>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="space-y-1">
            <button
              onClick={handleDownload}
              disabled={downloading || loading || totalSealed === 0}
              className="font-sketch text-sm px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              style={{
                background: "#3D1419",
                color: "#FDF8F0",
                border: "2px solid #2A0D12",
                boxShadow: downloading ? "none" : "3px 3px 0 #2A0D12",
              }}
            >
              {downloading ? "Building PDF…" : "↓ Download Transcript"}
            </button>
            {downloadError && (
              <p className="font-mono text-xs text-papaya">{downloadError}</p>
            )}
          </div>
          <Link href="/lesson" className="btn-primary text-sm">
            + Open Journal
          </Link>
        </div>
      </section>

      {/* Offline banner */}
      {offline && (
        <div className="witness-alert rounded">
          <p className="font-sketch text-sm">adeline-brain is offline</p>
          <p className="font-body text-xs mt-1 opacity-70">
            Start the brain service to see live progress. Showing empty state.
          </p>
        </div>
      )}

      {/* Summary stats */}
      {!loading && !offline && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: "Lessons Sealed", value: totalSealed },
            { label: "Tracks Active", value: tracksActive },
            { label: "Tracks Remaining", value: 8 - tracksActive },
          ].map((s) => (
            <div key={s.label} className="sketch-card text-center space-y-1 py-4">
              <p className="font-sketch text-3xl text-paradise">{s.value}</p>
              <p className="font-sketch text-xs text-fuschia/50 uppercase tracking-widest">
                {s.label}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Progress Circles */}
      <section className="sketch-card space-y-6">
        <h3 className="font-sketch text-sm text-fuschia/60 uppercase tracking-widest">
          Track Mastery
        </h3>
        {loading ? (
          <div className="grid grid-cols-4 sm:grid-cols-8 gap-6 animate-pulse">
            {TRACKS.map((t) => (
              <div key={t.id} className="flex flex-col items-center gap-2">
                <div className="w-24 h-24 rounded-full bg-parchment-200" />
                <div className="h-3 w-16 bg-parchment-200 rounded" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-6">
            {TRACKS.map((t) => (
              <ProgressCircle
                key={t.id}
                count={progress[t.id] ?? 0}
                color={t.color}
                label={t.label}
                num={t.num}
              />
            ))}
          </div>
        )}
      </section>

      {/* Recent Activity */}
      <section className="sketch-card space-y-4">
        <h3 className="font-sketch text-sm text-fuschia/60 uppercase tracking-widest">
          Recent Activity
        </h3>
        {loading ? (
          <div className="space-y-3 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 bg-parchment-200 rounded" />
            ))}
          </div>
        ) : (
          <RecentActivity entries={recent} />
        )}
      </section>

    </div>
  );
}
