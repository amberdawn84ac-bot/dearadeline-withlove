"use client";

/**
 * LessonRenderer — maps a LessonResponse from adeline-brain to styled blocks.
 *
 * Delegates all block chrome to BlockWrapper:
 *   PRIMARY_SOURCE   → Paradise border + Verified Seal + citation footer
 *   RESEARCH_MISSION → Papaya dashed sticky-note
 *   NARRATIVE        → Standard sketch-card
 */

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import BlockWrapper from "@/components/lessons/BlockWrapper";
import ArchiveSilent from "@/components/lessons/ArchiveSilent";
import { BotanicalDivider } from "@/components/icons";
import { sealJournal } from "@/lib/brain-client";
import type { LessonResponse, LessonBlockResponse } from "@/lib/brain-client";

interface LessonRendererProps {
  lesson: LessonResponse;
  isHomestead?: boolean;
  showScores?: boolean;
  /** student_id to use when sealing — defaults to demo */
  studentId?: string;
}

// ── Seal Journal button + toast ───────────────────────────────────────────────

type SealState = "idle" | "loading" | "sealed" | "error";

function SealButton({
  lesson,
  studentId,
}: {
  lesson: LessonResponse;
  studentId: string;
}) {
  const router = useRouter();
  const [state, setState] = useState<SealState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const verifiedCount = lesson.blocks.filter(
    (b) => b.evidence[0]?.verdict === "VERIFIED",
  ).length;

  const handleSeal = useCallback(async () => {
    setState("loading");
    setErrorMsg("");
    try {
      const evidenceSources = lesson.blocks
        .filter(
          (b) =>
            b.block_type === "PRIMARY_SOURCE" &&
            b.evidence[0]?.verdict === "VERIFIED",
        )
        .map((b) => ({
          title: b.evidence[0].source_title,
          url: b.evidence[0].source_url,
          author: b.evidence[0].witness_citation?.author ?? "",
          year: b.evidence[0].witness_citation?.year ?? null,
        }));

      await sealJournal({
        student_id: studentId,
        lesson_id: lesson.lesson_id,
        track: lesson.track,
        completed_blocks: verifiedCount,
        oas_standards: lesson.oas_standards?.map((s) => ({
          standard_id: s.standard_id,
          text: s.text,
          grade: s.grade,
        })),
        evidence_sources: evidenceSources,
      });
      setState("sealed");
      // Brief pause so the toast is visible, then navigate
      setTimeout(() => router.push("/dashboard"), 1400);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Seal failed");
      setState("error");
    }
  }, [lesson, studentId, verifiedCount, router]);

  return (
    <div className="space-y-2">
      {/* Toast */}
      {state === "sealed" && (
        <div
          className="flex items-center gap-2 border border-paradise bg-parchment-100 px-4 py-2"
          role="status"
        >
          <span className="font-sketch text-paradise text-sm">Journal Sealed</span>
          <span className="font-mono text-xs text-fuschia/50">→ opening dashboard…</span>
        </div>
      )}
      {state === "error" && (
        <p className="font-mono text-xs text-papaya">{errorMsg}</p>
      )}

      <button
        onClick={handleSeal}
        disabled={state === "loading" || state === "sealed"}
        className="font-sketch text-sm px-5 py-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        style={{
          background: state === "sealed" ? "#7D333D" : "#9A3F4A",
          color: "#FDF8F0",
          border: "2px solid #7D333D",
          boxShadow: state === "sealed" ? "none" : "3px 3px 0 #7D333D",
        }}
      >
        {state === "loading"
          ? "Sealing…"
          : state === "sealed"
          ? "Sealed"
          : "Seal Journal"}
      </button>
    </div>
  );
}

// ── Block content renderers ───────────────────────────────────────────────────

function PrimarySourceContent({ block, isHomestead }: { block: LessonBlockResponse; isHomestead: boolean }) {
  const content = isHomestead && block.homestead_content ? block.homestead_content : block.content;
  return (
    <p className="font-body text-fuschia leading-relaxed whitespace-pre-line text-sm">
      {content}
    </p>
  );
}

function ResearchMissionContent({ block }: { block: LessonBlockResponse }) {
  const score = block.evidence[0]?.similarity_score;
  return (
    <div className="space-y-3">
      <ArchiveSilent similarityScore={score} showScore />
      <p className="font-body text-sm text-fuschia/80 whitespace-pre-line leading-relaxed">
        {block.content}
      </p>
    </div>
  );
}

function NarrativeContent({ block, isHomestead }: { block: LessonBlockResponse; isHomestead: boolean }) {
  const content = isHomestead && block.homestead_content ? block.homestead_content : block.content;
  return (
    <p className="font-body text-fuschia leading-relaxed text-sm">
      {content}
    </p>
  );
}

// ── OAS Standards footer ──────────────────────────────────────────────────────

const TRACK_LABELS: Record<string, string> = {
  CREATION_SCIENCE:     "Creation & Science",
  HEALTH_NATUROPATHY:   "Health & Naturopathy",
  HOMESTEADING:         "Homesteading",
  GOVERNMENT_ECONOMICS: "Government & Economics",
  JUSTICE_CHANGEMAKING: "Justice & Change-making",
  DISCIPLESHIP:         "Discipleship",
  TRUTH_HISTORY:        "Truth History",
  ENGLISH_LITERATURE:   "English Literature",
};

function OASFooter({ standards }: { standards: LessonResponse["oas_standards"] }) {
  if (!standards?.length) return null;

  const primary    = standards.filter((s) => s.source_type !== "cross_track");
  const crossTrack = standards.filter((s) => s.source_type === "cross_track");

  // Deduplicate cross-track entries by connected_track for the "connects to" badges
  const connectedTracks = [...new Set(crossTrack.map((s) => s.connected_track).filter(Boolean))];

  return (
    <div className="pt-4 border-t border-fuschia/10 space-y-4">

      {/* Primary standards */}
      {primary.length > 0 && (
        <div className="space-y-2">
          <p className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
            Oklahoma Academic Standards Met
          </p>
          <div className="space-y-2">
            {primary.map((s) => (
              <div key={s.standard_id} className="flex gap-3 items-start">
                <span className="font-mono text-xs bg-parchment-200 text-fuschia/60 px-2 py-0.5 rounded-sm shrink-0">
                  {s.standard_id} · Gr {s.grade}
                </span>
                {s.lesson_hook && (
                  <p className="font-body text-xs text-fuschia/50 italic leading-snug">
                    &ldquo;{s.lesson_hook}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cross-track connections */}
      {connectedTracks.length > 0 && (
        <div className="space-y-2">
          <p className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
            This Lesson Connects To
          </p>
          <div className="flex flex-wrap gap-2">
            {connectedTracks.map((track) => {
              const examples = crossTrack.filter((s) => s.connected_track === track);
              return (
                <div
                  key={track}
                  className="group relative"
                  title={examples[0]?.bridge_standard_text || ""}
                >
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-sketch border-2 border-[#E7DAC3] bg-[#FFFEF7] text-[#2F4731] hover:border-[#BD6809] hover:text-[#BD6809] transition-colors cursor-default">
                    <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60" />
                    {TRACK_LABELS[track!] ?? track}
                  </span>
                </div>
              );
            })}
          </div>
          {/* Show the bridge reasoning for the first cross-track connection */}
          {crossTrack[0]?.bridge_standard_text && (
            <p className="font-body text-xs text-fuschia/40 italic leading-snug">
              via: &ldquo;{crossTrack[0].bridge_standard_text}&rdquo;
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── LessonRenderer ────────────────────────────────────────────────────────────

export default function LessonRenderer({
  lesson,
  isHomestead = false,
  showScores = false,
  studentId = "demo-student-001",
}: LessonRendererProps) {
  return (
    <article className="space-y-6 max-w-2xl">

      {/* Header */}
      <header className="space-y-1">
        <p className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
          {lesson.track.replace(/_/g, " ")}
        </p>
        <h1 className="font-sketch text-2xl text-fuschia leading-snug">{lesson.title}</h1>
        {lesson.has_research_missions && (
          <p className="font-body text-xs text-papaya italic">
            Some content is pending verified sources — Research Missions assigned below.
          </p>
        )}
      </header>

      <BotanicalDivider />

      {/* Blocks */}
      <div className="space-y-5">
        {lesson.blocks.map((block) => {
          if (block.is_silenced) return null;

          return (
            <BlockWrapper key={block.block_id} block={block} showScores={showScores}>
              {block.block_type === "PRIMARY_SOURCE" && (
                <PrimarySourceContent block={block} isHomestead={isHomestead} />
              )}
              {block.block_type === "RESEARCH_MISSION" && (
                <ResearchMissionContent block={block} />
              )}
              {(block.block_type === "NARRATIVE" || !["PRIMARY_SOURCE","RESEARCH_MISSION"].includes(block.block_type)) && (
                <NarrativeContent block={block} isHomestead={isHomestead} />
              )}
            </BlockWrapper>
          );
        })}
      </div>

      {/* OAS Standards */}
      <OASFooter standards={lesson.oas_standards} />

      {/* Agent + CASE credits */}
      {(lesson.agent_name || lesson.credits_awarded?.length > 0) && (
        <div className="flex flex-wrap items-center gap-3 pt-3">
          {lesson.agent_name && (
            <span className="font-mono text-[10px] px-2 py-0.5 rounded-full"
              style={{ background: "#F0FDF4", color: "#166534" }}>
              {lesson.agent_name}
            </span>
          )}
          {lesson.credits_awarded?.[0] && (
            <span className="font-mono text-[10px] px-2 py-0.5 rounded-full"
              style={{ background: "#FDF6E9", color: "#BD6809" }}>
              {lesson.credits_awarded[0].credit_hours} credit hr
              {" · "}{lesson.credits_awarded[0].credit_type}
            </span>
          )}
        </div>
      )}

      {/* Seal Journal */}
      <div className="pt-6 border-t border-fuschia/10 flex items-center justify-between flex-wrap gap-3">
        <p className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
          {lesson.blocks.filter((b) => b.evidence[0]?.verdict === "VERIFIED").length} verified{" "}
          &bull; {lesson.blocks.length} total blocks
        </p>
        <SealButton lesson={lesson} studentId={studentId} />
      </div>

    </article>
  );
}
