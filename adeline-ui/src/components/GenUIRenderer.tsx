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

import { useState } from "react";
import { clsx } from "clsx";
import type { LessonBlockResponse, Evidence, MindMapData, TimelineData, MnemonicData, NarratedSlideData } from "@/lib/brain-client";
import { MindMap } from "@/components/gen-ui/patterns/MindMap";
import { Timeline } from "@/components/gen-ui/patterns/Timeline";
import { WeightTierBadge } from "@/components/lessons/WeightTierBadge";
import { DistortionFlag } from "@/components/lessons/DistortionFlag";
import { KeystoneConcept } from "@/components/lessons/KeystoneConcept";
import { DistractionBox } from "@/components/lessons/DistractionBox";
import { SourceBadge } from "./SourceBadge";

// ── Block type constants ───────────────────────────────────────────────────────

type BrainBlockType =
  | "PRIMARY_SOURCE"
  | "LAB_MISSION"
  | "EXPERIMENT"
  | "NARRATIVE"
  | "RESEARCH_MISSION"
  | "QUIZ"
  | "TEXT"
  | "MIND_MAP"
  | "TIMELINE"
  | "MNEMONIC"
  | "NARRATED_SLIDE";

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
    <div className="mt-3 pt-3 border-t border-[#E7DAC3] space-y-2">
      <div className="flex flex-wrap items-center gap-2">
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
      {evidence.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {evidence.map((ev, i) => (
            <SourceBadge
              key={ev.source_id || i}
              sourceType={(ev as any).source_type ?? "PRIMARY_SOURCE"}
              sourceTitle={ev.source_title}
              sourceUrl={ev.source_url}
              citationYear={ev.witness_citation?.year ?? undefined}
            />
          ))}
        </div>
      )}
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
  MIND_MAP:         "bg-[#166534] text-white",
  TIMELINE:         "bg-[#1E3A5F] text-white",
  MNEMONIC:         "bg-[#6B21A8] text-white",
  NARRATED_SLIDE:   "bg-[#1D4ED8] text-white",
};

const LABEL_NAMES: Record<BrainBlockType, string> = {
  PRIMARY_SOURCE:   "Primary Source",
  LAB_MISSION:      "Lab Mission",
  EXPERIMENT:       "Sovereign Lab",
  NARRATIVE:        "Narrative",
  RESEARCH_MISSION: "Research Mission",
  QUIZ:             "Quiz",
  TEXT:             "Reading",
  MIND_MAP:         "Mind Map",
  TIMELINE:         "Timeline",
  MNEMONIC:         "Mnemonic",
  NARRATED_SLIDE:   "Lesson Slides",
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
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#FFFBF4", border: "1.5px solid #9A3F4A30" }}
    >
      <BlockLabel type="PRIMARY_SOURCE" />
      <div className="text-[#2F4731] leading-[1.8] whitespace-pre-wrap" style={{ fontFamily: "var(--font-kalam), cursive" }}>
        <p className="text-base first-letter:text-3xl first-letter:font-bold first-letter:text-[#9A3F4A] first-letter:float-left first-letter:mr-1 first-letter:leading-none">{content}</p>
      </div>
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── LAB_MISSION block ─────────────────────────────────────────────────────────

function LabMissionBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#F0FDF4", border: "1.5px dashed #2F4731" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🌱</span>
        <BlockLabel type="LAB_MISSION" />
      </div>
      <p
        className="text-base text-[#2F4731] leading-[1.8] whitespace-pre-wrap font-medium"
        style={{ fontFamily: "var(--font-swanky), cursive" }}
      >
        {block.content}
      </p>
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
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#FFFEF7", border: "1.5px solid #BD680920" }}
    >
      <BlockLabel type="NARRATIVE" />
      <p
        className="text-lg text-[#2F4731] leading-[1.9] whitespace-pre-wrap"
        style={{ fontFamily: "var(--font-kalam), cursive" }}
      >
        {content}
      </p>
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── RESEARCH_MISSION block ────────────────────────────────────────────────────

function ResearchMissionBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#FEF2F2", border: "1.5px solid #991B1B40" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">🔍</span>
        <BlockLabel type="RESEARCH_MISSION" />
      </div>
      <p
        className="text-base text-[#991B1B] leading-[1.8] whitespace-pre-wrap font-bold"
        style={{ fontFamily: "var(--font-permanent-marker), cursive" }}
      >
        {block.content}
      </p>
      <p className="text-xs text-[#2F4731]/50 italic" style={{ fontFamily: "var(--font-kalam), cursive" }}>
        No verified archive source was found. This is your research mission.
      </p>
    </div>
  );
}

// ── QUIZ block ────────────────────────────────────────────────────────────────

function QuizBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#EEF2FF", border: "1.5px solid #4F46E5" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">❓</span>
        <BlockLabel type="QUIZ" />
      </div>
      <p
        className="text-lg text-[#312E81] leading-[1.7] whitespace-pre-wrap font-bold"
        style={{ fontFamily: "var(--font-kranky), cursive" }}
      >
        {block.content}
      </p>
      <textarea
        className="w-full mt-1 px-3 py-2 text-base text-[#2F4731] bg-white border border-[#4F46E5]/30 rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
        style={{ fontFamily: "var(--font-kalam), cursive" }}
        rows={3}
        placeholder="Write your answer here..."
      />
    </div>
  );
}

// ── TEXT / fallback block ─────────────────────────────────────────────────────

function TextBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div className="rounded-xl p-5 space-y-2" style={{ background: "#F9FAFB" }}>
      <BlockLabel type="TEXT" />
      <p
        className="text-base text-[#374151] leading-[1.8] whitespace-pre-wrap"
        style={{ fontFamily: "var(--font-kalam), cursive" }}
      >
        {block.content}
      </p>
    </div>
  );
}

// ── MIND_MAP block ────────────────────────────────────────────────────────────

function MindMapBlock({ block }: { block: LessonBlockResponse }) {
  if (!block.mind_map_data) return null;
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1.5px solid #BBF7D0" }}>
      <MindMap data={block.mind_map_data} />
    </div>
  );
}

// ── TIMELINE block ────────────────────────────────────────────────────────────

function TimelineBlock({ block }: { block: LessonBlockResponse }) {
  if (!block.timeline_data) return null;
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1.5px solid #BFDBFE" }}>
      <Timeline data={block.timeline_data} evidence={block.evidence} />
    </div>
  );
}

// ── MNEMONIC block ────────────────────────────────────────────────────────────

function MnemonicBlock({ block }: { block: LessonBlockResponse }) {
  const data = block.mnemonic_data;
  if (!data) return null;
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#FAF5FF", border: "1.5px solid #E9D5FF" }}
    >
      <BlockLabel type="MNEMONIC" />
      <p className="text-xs text-[#6B21A8] font-semibold uppercase tracking-widest">
        {data.concept}
      </p>
      <div className="flex gap-1 flex-wrap">
        {data.acronym.split("").map((letter, i) => (
          <div key={i} className="text-center">
            <div className="text-2xl font-black text-[#6B21A8] leading-none">{letter}</div>
            <div className="text-[10px] text-[#374151] mt-1 max-w-[48px] leading-tight">
              {data.words[i] ?? ""}
            </div>
          </div>
        ))}
      </div>
      <p className="text-sm text-[#374151] italic border-t border-[#E9D5FF] pt-2">
        {data.tip}
      </p>
    </div>
  );
}

// ── NARRATED_SLIDE block ──────────────────────────────────────────────────────

function NarratedSlideBlock({ block }: { block: LessonBlockResponse }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [showNarration, setShowNarration] = useState(false);
  const data = block.narrated_slide_data;
  if (!data || data.slides.length === 0) return null;
  const slide = data.slides[currentSlide];
  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: "#EFF6FF", border: "1.5px solid #BFDBFE" }}
    >
      <div className="flex items-center justify-between">
        <BlockLabel type="NARRATED_SLIDE" />
        <span className="text-xs text-[#1D4ED8] opacity-70">
          {data.total_duration_minutes} min
        </span>
      </div>
      {/* Slide header */}
      <div>
        <p className="text-[10px] text-[#1D4ED8] font-bold uppercase tracking-widest mb-1">
          Slide {slide.slide_number} of {data.slides.length}
        </p>
        <h3 className="font-bold text-[#1E3A5F] text-base">{slide.title}</h3>
      </div>
      {/* Bullets */}
      <ul className="space-y-1.5">
        {slide.bullets.map((bullet, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-[#374151]">
            <span className="text-[#1D4ED8] font-bold mt-0.5">→</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
      {/* Narration accordion */}
      <button
        onClick={() => setShowNarration((s) => !s)}
        className="text-xs text-[#1D4ED8] font-semibold underline"
      >
        {showNarration ? "Hide narration script ▲" : "Show narration script ▼"}
      </button>
      {showNarration && (
        <p className="text-xs text-[#374151] bg-white rounded-lg p-3 italic border border-[#BFDBFE]">
          {slide.narration}
        </p>
      )}
      {/* Navigation */}
      <div className="flex items-center justify-between pt-1">
        <button
          onClick={() => { setCurrentSlide((s) => Math.max(0, s - 1)); setShowNarration(false); }}
          disabled={currentSlide === 0}
          className="text-xs px-3 py-1.5 rounded-lg font-semibold text-white disabled:opacity-40"
          style={{ background: "#1D4ED8" }}
        >
          ← Prev
        </button>
        <div className="flex gap-1">
          {data.slides.map((_, i) => (
            <button
              key={i}
              onClick={() => { setCurrentSlide(i); setShowNarration(false); }}
              className="w-2 h-2 rounded-full transition-colors"
              style={{ background: i === currentSlide ? "#1D4ED8" : "#BFDBFE" }}
            />
          ))}
        </div>
        <button
          onClick={() => { setCurrentSlide((s) => Math.min(data.slides.length - 1, s + 1)); setShowNarration(false); }}
          disabled={currentSlide === data.slides.length - 1}
          className="text-xs px-3 py-1.5 rounded-lg font-semibold text-white disabled:opacity-40"
          style={{ background: "#1D4ED8" }}
        >
          Next →
        </button>
      </div>
      {/* Audio placeholder */}
      <div className="flex items-center gap-2 pt-1 opacity-40">
        <span className="text-[#1D4ED8] text-sm">▶</span>
        <span className="text-xs text-[#374151]">Audio coming soon</span>
      </div>
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

          let blockContent;
          switch (type) {
            case "PRIMARY_SOURCE":
              blockContent = (
                <PrimarySourceBlock
                  block={block}
                  isHomestead={isHomestead}
                />
              );
              break;
            case "LAB_MISSION":
              blockContent = <LabMissionBlock block={block} />;
              break;
            case "EXPERIMENT":
              blockContent = <ExperimentBlock block={block} />;
              break;
            case "NARRATIVE":
              blockContent = (
                <NarrativeBlock block={block} isHomestead={isHomestead} />
              );
              break;
            case "RESEARCH_MISSION":
              blockContent = <ResearchMissionBlock block={block} />;
              break;
            case "QUIZ":
              blockContent = <QuizBlock block={block} />;
              break;
            case "MIND_MAP":
              blockContent = <MindMapBlock block={block} />;
              break;
            case "TIMELINE":
              blockContent = <TimelineBlock block={block} />;
              break;
            case "MNEMONIC":
              blockContent = <MnemonicBlock block={block} />;
              break;
            case "NARRATED_SLIDE":
              blockContent = <NarratedSlideBlock block={block} />;
              break;
            default:
              blockContent = <TextBlock block={block} />;
          }

          return (
            <div key={block.block_id}>
              {blockContent}
              {/* Reality Layer */}
              {(block as any).reality_layer && (
                <div className="space-y-2 mt-2">
                  <WeightTierBadge tier={(block as any).reality_layer.weight_tier} />
                  {(block as any).reality_layer.keystone_concept && (
                    <KeystoneConcept
                      concept={(block as any).reality_layer.keystone_concept.concept}
                      firstIntroduced={(block as any).reality_layer.keystone_concept.first_introduced}
                      repetitionNumber={(block as any).reality_layer.keystone_concept.repetition_number}
                      context={(block as any).reality_layer.keystone_concept.context}
                    />
                  )}
                  {((block as any).reality_layer.distortion_flags || []).map((flag: any, i: number) => (
                    <DistortionFlag
                      key={`distortion-${block.block_id}-${i}`}
                      commonClaim={flag.common_claim}
                      whatsHidden={flag.whats_hidden}
                      whatActuallyHappens={flag.what_actually_happens}
                      whyItMatters={flag.why_it_matters}
                    />
                  ))}
                  {((block as any).reality_layer.distraction_boxes || []).map((box: any, i: number) => (
                    <DistractionBox
                      key={`distraction-${block.block_id}-${i}`}
                      topic={box.topic}
                      reason={box.reason}
                      whenToReturn={box.when_to_return}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}

      {oasStandards.length > 0 && <OASStandardsSection standards={oasStandards} />}

      <AgentCreditFooter agentName={agentName} creditHours={creditHours} />
    </div>
  );
}
