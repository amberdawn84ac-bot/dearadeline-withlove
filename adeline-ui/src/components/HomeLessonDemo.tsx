"use client";

/**
 * HomeLessonDemo — Live "Try Adeline" widget for the marketing homepage.
 *
 * Calls /brain/lesson/stream and streams a real lesson block back to the
 * visitor without requiring an account. Uses the demo student.
 */
import { useState } from "react";
import { streamLesson } from "@/lib/brain-client";
import type { LessonResponse, LessonBlockResponse, Track } from "@/lib/brain-client";

const DEMO_TRACKS: { id: Track; label: string; emoji: string }[] = [
  { id: "TRUTH_HISTORY",        label: "Truth & History",       emoji: "📜" },
  { id: "CREATION_SCIENCE",     label: "Creation Science",      emoji: "🌿" },
  { id: "HOMESTEADING",         label: "Homesteading",          emoji: "🏡" },
  { id: "DISCIPLESHIP",         label: "Discipleship",          emoji: "✝️" },
  { id: "GOVERNMENT_ECONOMICS", label: "Gov & Economics",       emoji: "⚖️" },
  { id: "ENGLISH_LITERATURE",   label: "English & Literature",  emoji: "📖" },
];

const DEMO_STUDENT = "demo-visitor-001";

export function HomeLessonDemo() {
  const [track, setTrack]       = useState<Track>("TRUTH_HISTORY");
  const [topic, setTopic]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [blocks, setBlocks]     = useState<LessonBlockResponse[]>([]);
  const [error, setError]       = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setBlocks([]);
    setStreamStatus(null);
    setError("");
    try {
      for await (const event of streamLesson({
        student_id:   DEMO_STUDENT,
        track,
        topic:        topic.trim(),
        grade_level:  "8",
        is_homestead: false,
      })) {
        if (event.type === "status") {
          setStreamStatus(event.message);
        } else if (event.type === "block") {
          setBlocks((prev) => [...prev, event.block]);
        } else if (event.type === "done") {
          setLoading(false);
          setStreamStatus(null);
        } else if (event.type === "error") {
          setError(event.message);
          setLoading(false);
          setStreamStatus(null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach Adeline");
    } finally {
      setLoading(false);
      setStreamStatus(null);
    }
  }

  const firstVerifiedBlock = blocks.find(
    (b) => b.evidence?.[0]?.verdict === "VERIFIED",
  ) ?? blocks[0];

  return (
    <div className="w-full max-w-2xl mx-auto space-y-5">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Track picker */}
        <div className="flex flex-wrap gap-2">
          {DEMO_TRACKS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTrack(t.id)}
              className="px-3 py-1.5 rounded-full text-xs font-bold transition-all border-2"
              style={{
                background:   track === t.id ? "#2F4731" : "transparent",
                color:        track === t.id ? "#fff"    : "#2F4731",
                borderColor:  "#2F4731",
              }}
            >
              {t.emoji} {t.label}
            </button>
          ))}
        </div>

        {/* Topic input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={`Ask Adeline about ${DEMO_TRACKS.find((t) => t.id === track)?.label ?? "any topic"}…`}
            className="flex-1 px-4 py-3 rounded-xl border-2 border-[#E7DAC3] bg-white text-sm font-medium text-[#2F4731] placeholder:text-[#2F4731]/30 focus:outline-none focus:border-[#BD6809]"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !topic.trim()}
            className="px-6 py-3 rounded-xl text-sm font-black text-white uppercase tracking-wider disabled:opacity-40 transition-all hover:brightness-110"
            style={{ background: "#BD6809" }}
          >
            {loading ? "…" : "Ask"}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <p className="text-xs text-red-600 font-medium">
          {error} — is adeline-brain running?
        </p>
      )}

      {/* Loading — shows progressive status messages */}
      {loading && (
        <div className="rounded-2xl border-2 border-[#E7DAC3] p-6 space-y-3">
          {blocks.length === 0 ? (
            <div className="animate-pulse space-y-3">
              <div className="h-3 bg-[#E7DAC3] rounded w-3/4" />
              <div className="h-3 bg-[#E7DAC3] rounded w-full" />
              <div className="h-3 bg-[#E7DAC3] rounded w-5/6" />
            </div>
          ) : null}
          {streamStatus && (
            <p className="text-xs text-[#2F4731]/50 italic">{streamStatus}</p>
          )}
        </div>
      )}

      {/* First verified lesson block — appears as soon as it streams in */}
      {firstVerifiedBlock && (
        <div
          className="rounded-2xl border-2 p-6 space-y-4"
          style={{
            background:   "#FFFEF7",
            borderColor:  firstVerifiedBlock.evidence?.[0]?.verdict === "VERIFIED"
              ? "#9A3F4A" : "#E7DAC3",
          }}
        >
          {/* Source badge */}
          {firstVerifiedBlock.evidence?.[0] && (
            <div className="flex items-center gap-2">
              <span
                className="text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider"
                style={{
                  background: firstVerifiedBlock.evidence[0].verdict === "VERIFIED"
                    ? "#F0FDF4" : "#FEF9C3",
                  color: firstVerifiedBlock.evidence[0].verdict === "VERIFIED"
                    ? "#166534" : "#854D0E",
                }}
              >
                {firstVerifiedBlock.evidence[0].verdict === "VERIFIED" ? "✓ Verified Source" : "⚠ Investigating"}
              </span>
              {firstVerifiedBlock.evidence[0].source_title && (
                <span className="text-xs text-[#2F4731]/50 truncate max-w-[240px]">
                  {firstVerifiedBlock.evidence[0].source_title}
                </span>
              )}
            </div>
          )}

          {/* Content */}
          <p
            className="text-sm text-[#2F4731] leading-relaxed whitespace-pre-line"
            style={{ fontFamily: "'Kalam', cursive" }}
          >
            {firstVerifiedBlock.content}
          </p>

          {/* Link to full lesson */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[#E7DAC3]">
            <a
              href="/lesson"
              className="ml-auto text-[10px] font-black uppercase tracking-wider text-[#BD6809] hover:underline"
            >
              Full lesson →
            </a>
          </div>
        </div>
      )}

      {/* Research mission fallback */}
      {blocks.length > 0 && !firstVerifiedBlock && !loading && (
        <div className="rounded-2xl border-2 border-[#FEF3C7] bg-[#FFFBEB] p-5 text-sm text-[#92400E]">
          No verified archive source found for this topic yet. Adeline has assigned it as a Research Mission.
        </div>
      )}
    </div>
  );
}
