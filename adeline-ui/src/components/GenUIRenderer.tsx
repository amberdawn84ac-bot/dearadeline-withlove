"use client";

/**
 * GenUIRenderer — Renders structured lesson blocks from adeline-brain.
 *
 * Handles all 6 block types emitted by the multi-agent orchestrator:
 *   PRIMARY_SOURCE  (HistorianAgent / ScienceAgent)
 *   LAB_MISSION     (ScienceAgent — HOMESTEADING / CREATION_SCIENCE)
 *   NARRATIVE       (DiscipleshipAgent — worldview-aligned content)
 *   RESEARCH_MISSION (any agent fallback — no verified source found)
 *   QUIZ            (future — scaffold route)
 *   TEXT            (plain content — catch-all)
 *
 * Evidence from the Witness Protocol is displayed on PRIMARY_SOURCE blocks.
 * Cross-track OAS standards are shown in a GraphRAG sidebar section.
 */

import { clsx } from "clsx";
import type { LessonBlockResponse, Evidence } from "@/lib/brain-client";

// ── Block type constants ───────────────────────────────────────────────────────

type BrainBlockType =
  | "PRIMARY_SOURCE"
  | "LAB_MISSION"
  | "EXPERIMENT"
  | "NARRATIVE"
  | "RESEARCH_MISSION"
  | "QUIZ"
  | "TEXT";

// ── OAS Standard entry ────────────────────────────────────────────────────────

interface OASStandard {
  standard_id: string;
  text: string;
  grade: number;
  lesson_hook: string;
  source_type?: "primary" | "cross_track";
  connected_track?: string;
  bridge_standard_text?: string;
}

// ── GenUIRenderer props ───────────────────────────────────────────────────────

interface GenUIRendererProps {
  lessonId: string;
  blocks: LessonBlockResponse[];
  isHomestead: boolean;
  oasStandards?: OASStandard[];
  agentName?: string;
  creditHours?: number;
}

// ── Witness verdict badge ─────────────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: Evidence["verdict"] }) {
  const styles: Record<Evidence["verdict"], { bg: string; text: string; icon: string }> = {
    VERIFIED:         { bg: "#F0FDF4", text: "#166534", icon: "✓" },
    ARCHIVE_SILENT:   { bg: "#FEF9C3", text: "#713F12", icon: "◎" },
    RESEARCH_MISSION: { bg: "#FEF2F2", text: "#991B1B", icon: "?" },
  };
  const s = styles[verdict];
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
      style={{ background: s.bg, color: s.text }}
    >
      {s.icon} {verdict.replace(/_/g, " ")}
    </span>
  );
}

// ── Evidence footer ───────────────────────────────────────────────────────────

function EvidenceFooter({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return null;
  const ev = evidence[0];
  return (
    <div className="mt-3 pt-3 border-t border-[#E7DAC3] flex flex-wrap items-center gap-2">
      <VerdictBadge verdict={ev.verdict} />
      <span className="text-[11px] text-[#2F4731]/60 truncate max-w-xs">
        {ev.source_url ? (
          <a
            href={ev.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-[#BD6809] transition-colors"
          >
            {ev.source_title}
          </a>
        ) : (
          ev.source_title
        )}
        {ev.witness_citation.author && ` · ${ev.witness_citation.author}`}
        {ev.witness_citation.year && ` (${ev.witness_citation.year})`}
      </span>
      <span className="text-[10px] text-[#2F4731]/40 ml-auto shrink-0">
        {(ev.similarity_score * 100).toFixed(0)}% match
      </span>
    </div>
  );
}

// ── Block type label ──────────────────────────────────────────────────────────

const LABEL_STYLES: Record<BrainBlockType, string> = {
  PRIMARY_SOURCE:   "bg-[#9A3F4A] text-white",
  LAB_MISSION:      "bg-[#2F4731] text-white",
  EXPERIMENT:       "bg-[#BD6809] text-black",
  NARRATIVE:        "bg-[#BD6809] text-white",
  RESEARCH_MISSION: "bg-[#6B7280] text-white",
  QUIZ:             "bg-[#4F46E5] text-white",
  TEXT:             "bg-[#D1D5DB] text-[#374151]",
};

const LABEL_NAMES: Record<BrainBlockType, string> = {
  PRIMARY_SOURCE:   "Primary Source",
  LAB_MISSION:      "Lab Mission",
  EXPERIMENT:       "Sovereign Lab",
  NARRATIVE:        "Narrative",
  RESEARCH_MISSION: "Research Mission",
  QUIZ:             "Quiz",
  TEXT:             "Reading",
};

function BlockLabel({ type }: { type: string }) {
  const t = type as BrainBlockType;
  return (
    <span
      className={clsx(
        "inline-block text-[10px] font-bold px-2 py-0.5 uppercase tracking-widest rounded-sm shrink-0",
        LABEL_STYLES[t] ?? "bg-[#D1D5DB] text-[#374151]"
      )}
    >
      {LABEL_NAMES[t] ?? type.replace(/_/g, " ")}
    </span>
  );
}

// ── PRIMARY_SOURCE block ──────────────────────────────────────────────────────

function PrimarySourceBlock({
  block,
  isHomestead,
}: {
  block: LessonBlockResponse;
  isHomestead: boolean;
}) {
  const content =
    isHomestead && block.homestead_content ? block.homestead_content : block.content;
  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ background: "#FFFBF4", border: "1.5px solid #9A3F4A30" }}
    >
      <BlockLabel type="PRIMARY_SOURCE" />
      <p className="text-sm text-[#2F4731] leading-relaxed whitespace-pre-wrap">{content}</p>
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── LAB_MISSION block ─────────────────────────────────────────────────────────

function LabMissionBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ background: "#F0FDF4", border: "1.5px dashed #2F4731" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🌱</span>
        <BlockLabel type="LAB_MISSION" />
      </div>
      <p className="text-sm text-[#2F4731] leading-relaxed whitespace-pre-wrap">{block.content}</p>
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── EXPERIMENT block (Sovereign Lab) ─────────────────────────────────────────

function ExperimentBlock({ block }: { block: LessonBlockResponse }) {
  // The block may carry experiment_data in its raw dict (passed through as extra field)
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#FDF6E9", border: "2px solid #BD6809" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-xl">🧪</span>
        <BlockLabel type="EXPERIMENT" />
        <span className="ml-auto text-xs font-black uppercase tracking-wider text-[#BD6809]">
          Sovereign Lab
        </span>
      </div>
      <p
        className="text-base text-[#2F4731] leading-relaxed whitespace-pre-wrap font-medium"
        style={{ fontFamily: "var(--font-kalam), cursive" }}
      >
        {block.content}
      </p>
      <div className="flex items-center gap-3 pt-2 border-t border-[#BD6809]/20">
        <span className="text-xs text-[#BD6809] font-bold">
          🎬 Film This — Your video IS the portfolio
        </span>
      </div>
    </div>
  );
}

// ── NARRATIVE block ───────────────────────────────────────────────────────────

function NarrativeBlock({
  block,
  isHomestead,
}: {
  block: LessonBlockResponse;
  isHomestead: boolean;
}) {
  const content =
    isHomestead && block.homestead_content ? block.homestead_content : block.content;
  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ background: "#FFFEF7", border: "1.5px solid #BD680920" }}
    >
      <BlockLabel type="NARRATIVE" />
      <p className="text-sm text-[#2F4731] leading-relaxed whitespace-pre-wrap italic">{content}</p>
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── RESEARCH_MISSION block ────────────────────────────────────────────────────

function ResearchMissionBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ background: "#FEF2F2", border: "1.5px solid #991B1B40" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🔍</span>
        <BlockLabel type="RESEARCH_MISSION" />
      </div>
      <p className="text-sm text-[#991B1B] leading-relaxed whitespace-pre-wrap">{block.content}</p>
      <p className="text-xs text-[#2F4731]/50 italic">
        No verified archive source was found. This is a student research opportunity.
      </p>
    </div>
  );
}

// ── QUIZ block ────────────────────────────────────────────────────────────────

function QuizBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ background: "#EEF2FF", border: "1.5px solid #4F46E5" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">❓</span>
        <BlockLabel type="QUIZ" />
      </div>
      <p className="text-sm text-[#312E81] leading-relaxed whitespace-pre-wrap">{block.content}</p>
      <textarea
        className="w-full mt-1 px-3 py-2 text-sm text-[#2F4731] bg-white border border-[#4F46E5]/30 rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
        rows={3}
        placeholder="Write your answer here…"
      />
    </div>
  );
}

// ── TEXT / fallback block ─────────────────────────────────────────────────────

function TextBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div className="rounded-xl p-4 space-y-2" style={{ background: "#F9FAFB" }}>
      <BlockLabel type="TEXT" />
      <p className="text-sm text-[#374151] leading-relaxed whitespace-pre-wrap">{block.content}</p>
    </div>
  );
}

// ── Cross-track standards section ─────────────────────────────────────────────

function OASStandardsSection({ standards }: { standards: OASStandard[] }) {
  const primary    = standards.filter((s) => s.source_type !== "cross_track");
  const crossTrack = standards.filter((s) => s.source_type === "cross_track");

  if (!standards.length) return null;

  return (
    <div
      className="rounded-xl p-4 space-y-3 mt-2"
      style={{ background: "#F8FFF9", border: "1px solid #2F473130" }}
    >
      <span className="text-sm font-bold text-[#2F4731] tracking-wide">
        Oklahoma Academic Standards
      </span>

      {primary.length > 0 && (
        <ul className="space-y-1.5">
          {primary.map((s) => (
            <li key={s.standard_id} className="text-xs text-[#2F4731]">
              <span className="font-bold text-[#BD6809]">{s.standard_id}</span>
              {" — "}
              {s.text}
              {s.lesson_hook && (
                <span className="block text-[#2F4731]/50 italic mt-0.5 pl-3">
                  ↳ {s.lesson_hook}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {crossTrack.length > 0 && (
        <>
          <p className="text-[10px] font-bold text-[#2F4731]/50 uppercase tracking-wider">
            Connected Tracks (GraphRAG)
          </p>
          <ul className="space-y-1.5">
            {crossTrack.map((s) => (
              <li key={s.standard_id} className="text-xs text-[#2F4731]/70">
                <span className="font-semibold text-[#BD6809]/80">{s.standard_id}</span>
                {" · "}
                <span className="italic">{s.connected_track?.replace(/_/g, " ")}</span>
                {" — "}
                {s.text}
                {s.bridge_standard_text && (
                  <span className="block text-[#2F4731]/40 italic mt-0.5 pl-3">
                    Bridge: {s.bridge_standard_text}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// ── Agent + credit footer ─────────────────────────────────────────────────────

function AgentCreditFooter({
  agentName,
  creditHours,
}: {
  agentName?: string;
  creditHours?: number;
}) {
  if (!agentName && !creditHours) return null;
  return (
    <div className="flex items-center justify-between text-[10px] text-[#2F4731]/40 pt-2 border-t border-[#E7DAC3] mt-4">
      {agentName && <span>Generated by {agentName}</span>}
      {creditHours !== undefined && creditHours > 0 && (
        <span>{creditHours} credit hour{creditHours !== 1 ? "s" : ""} awarded</span>
      )}
    </div>
  );
}

// ── GenUIRenderer ─────────────────────────────────────────────────────────────

export default function GenUIRenderer({
  lessonId: _lessonId,
  blocks,
  isHomestead,
  oasStandards = [],
  agentName,
  creditHours,
}: GenUIRendererProps) {
  return (
    <div className="space-y-4">
      {blocks
        .filter((b) => !b.is_silenced)
        .map((block) => {
          const type = block.block_type as BrainBlockType;

          switch (type) {
            case "PRIMARY_SOURCE":
              return (
                <PrimarySourceBlock
                  key={block.block_id}
                  block={block}
                  isHomestead={isHomestead}
                />
              );
            case "LAB_MISSION":
              return <LabMissionBlock key={block.block_id} block={block} />;
            case "EXPERIMENT":
              return <ExperimentBlock key={block.block_id} block={block} />;
            case "NARRATIVE":
              return (
                <NarrativeBlock key={block.block_id} block={block} isHomestead={isHomestead} />
              );
            case "RESEARCH_MISSION":
              return <ResearchMissionBlock key={block.block_id} block={block} />;
            case "QUIZ":
              return <QuizBlock key={block.block_id} block={block} />;
            default:
              return <TextBlock key={block.block_id} block={block} />;
          }
        })}

      {oasStandards.length > 0 && <OASStandardsSection standards={oasStandards} />}

      <AgentCreditFooter agentName={agentName} creditHours={creditHours} />
    </div>
  );
}
