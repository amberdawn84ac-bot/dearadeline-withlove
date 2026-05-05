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

import { useState, useEffect } from "react";
import { clsx } from "clsx";
import { motion } from "framer-motion";
import type { LessonBlockResponse, Evidence, MindMapData, TimelineData, MnemonicData, NarratedSlideData, QuizData, FlashcardData } from "@/lib/brain-client";
import { MindMap } from "@/components/gen-ui/patterns/MindMap";
import { Timeline } from "@/components/gen-ui/patterns/Timeline";
import { QuizCard } from "@/components/gen-ui/patterns/QuizCard";
import { Flashcard } from "@/components/gen-ui/patterns/Flashcard";
import { ScaffoldedProblem } from "@/components/gen-ui/patterns/ScaffoldedProblem";
import { HardThingChallenge } from "@/components/gen-ui/patterns/HardThingChallenge";
import { DragDropTimeline } from "@/components/gen-ui/patterns/DragDropTimeline";
import { LiveChart } from "@/components/gen-ui/patterns/LiveChart";
import { SocraticDebate } from "@/components/gen-ui/patterns/SocraticDebate";
import { ProjectBuilder } from "@/components/gen-ui/patterns/ProjectBuilder";
import { FocusReset } from "@/components/gen-ui/patterns/FocusReset";
import { TaskScaffold } from "@/components/gen-ui/patterns/TaskScaffold";
import { GlowGrow } from "@/components/gen-ui/patterns/GlowGrow";
import { InsightReport } from "@/components/gen-ui/patterns/InsightReport";
import { MnemonicCard } from "@/components/gen-ui/patterns/MnemonicCard";
import { NarratedSlides } from "@/components/gen-ui/patterns/NarratedSlides";
import { EmbeddedInterrupt } from "@/components/gen-ui/patterns/EmbeddedInterrupt";
import AnimatedSketchnoteRenderer from "@/components/gen-ui/patterns/AnimatedSketchnoteRenderer";
import { TextSelectionMenu } from "@/components/gen-ui/TextSelectionMenu";
import { WeightTierBadge } from "@/components/lessons/WeightTierBadge";
import { DistortionFlag } from "@/components/lessons/DistortionFlag";
import { KeystoneConcept } from "@/components/lessons/KeystoneConcept";
import { DistractionBox } from "@/components/lessons/DistractionBox";
import { SourceBadge } from "./SourceBadge";
import Link from "next/link";

// ── Component Registry (safe, whitelisted only) ────────────────────────────────
// Only components in this registry can be rendered by GENUI_ASSEMBLY blocks.
// This prevents arbitrary code execution from LLM outputs.

const componentRegistry: Record<string, React.ComponentType<any>> = {
  // Assessment
  InteractiveQuiz:   QuizCard,
  GlowGrow:          GlowGrow,
  // Socratic / project
  ScaffoldedProblem: ScaffoldedProblem,
  SocraticDebate:    SocraticDebate,
  HardThingChallenge: HardThingChallenge,
  ProjectBuilder:    ProjectBuilder,
  // Timeline / sequencing
  DragDropTimeline:  DragDropTimeline,
  // Mastery / insight
  LiveChart:         LiveChart,
  InsightReport:     InsightReport,
  // Memory / vocabulary
  MnemonicCard:      MnemonicCard,
  // Neuroadaptive
  FocusReset:        FocusReset,
  TaskScaffold:      TaskScaffold,
  // Presentation
  NarratedSlides:    NarratedSlides,
  EmbeddedInterrupt: EmbeddedInterrupt,
};

// ── DynamicComponent Wrapper ─────────────────────────────────────────────────────
// Hydrates whitelisted components with local state and re-renders on changes.

interface DynamicComponentProps {
  componentType: string;
  props: Record<string, any>;
  initialState?: Record<string, any>;
  callbacks?: string[];
  onStateChange?: (newState: Record<string, any>) => void;
}

function DynamicComponent({
  componentType,
  props,
  initialState = {},
  callbacks = [],
  onStateChange,
}: DynamicComponentProps) {
  const [localState, setLocalState] = useState(initialState);
  const [localProps, setLocalProps] = useState(props);

  const Component = componentRegistry[componentType];

  if (!Component) {
    return (
      <div
        className="rounded-xl p-4 space-y-2"
        style={{ background: "#FEF2F2", border: "1.5px solid #991B1B40" }}
      >
        <BlockLabel type="GENUI_ASSEMBLY" />
        <p className="text-sm text-[#991B1B]">Unknown component: {componentType}</p>
      </div>
    );
  }

  const handleStateChange = (newState: Record<string, any>) => {
    setLocalState(newState);
    onStateChange?.(newState);
  };

  // Handle re-render triggers from backend callback
  useEffect(() => {
    if (props !== localProps) {
      setLocalProps(props);
    }
  }, [props]);

  return (
    <Component
      {...localProps}
      state={localState}
      onStateChange={handleStateChange}
      callbacks={callbacks}
    />
  );
}

// ── Animation variants for staggered block entrance ────────────────────────────

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.1,
    },
  },
};

const blockVariants = {
  hidden: { 
    opacity: 0, 
    y: 20,
    scale: 0.98,
  },
  visible: { 
    opacity: 1, 
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 260,
      damping: 25,
    },
  },
};

// ── Block type constants ───────────────────────────────────────────────────────

type BrainBlockType =
  | "PRIMARY_SOURCE"
  | "LAB_MISSION"
  | "EXPERIMENT"
  | "NARRATIVE"
  | "RESEARCH_MISSION"
  | "QUIZ"
  | "FLASHCARD"
  | "TEXT"
  | "MIND_MAP"
  | "TIMELINE"
  | "MNEMONIC"
  | "NARRATED_SLIDE"
  | "BOOK_SUGGESTION"
  | "INTERACTIVE_SIM"
  | "HIGHLIGHT_ASK"
  | "GENUI_ASSEMBLY"
  | "ANIMATED_SKETCHNOTE_LESSON";

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
  studentId?: string;
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
  FLASHCARD:        "bg-[#0E7490] text-white",
  TEXT:             "bg-[#D1D5DB] text-[#374151]",
  MIND_MAP:         "bg-[#166534] text-white",
  TIMELINE:         "bg-[#1E3A5F] text-white",
  MNEMONIC:         "bg-[#6B21A8] text-white",
  NARRATED_SLIDE:   "bg-[#1D4ED8] text-white",
  BOOK_SUGGESTION:  "bg-[#78350F] text-white",
  INTERACTIVE_SIM:           "bg-[#065F46] text-white",
  HIGHLIGHT_ASK:             "bg-[#374151] text-white",
  GENUI_ASSEMBLY:            "bg-[#7C3AED] text-white",
  ANIMATED_SKETCHNOTE_LESSON: "bg-[#3D1419] text-[#FFFEF7]",
};

const LABEL_NAMES: Record<BrainBlockType, string> = {
  PRIMARY_SOURCE:   "Primary Source",
  LAB_MISSION:      "Lab Mission",
  EXPERIMENT:       "Sovereign Lab",
  NARRATIVE:        "Narrative",
  RESEARCH_MISSION: "Research Mission",
  QUIZ:             "Quiz",
  FLASHCARD:        "Flashcard",
  TEXT:             "Reading",
  MIND_MAP:         "Mind Map",
  TIMELINE:         "Timeline",
  MNEMONIC:         "Mnemonic",
  NARRATED_SLIDE:   "Lesson Slides",
  BOOK_SUGGESTION:  "Suggested Reading",
  INTERACTIVE_SIM:           "Interactive",
  HIGHLIGHT_ASK:             "Highlight & Ask",
  GENUI_ASSEMBLY:            "Dynamic Component",
  ANIMATED_SKETCHNOTE_LESSON: "Living Sketchnote",
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

// ── Lesson content renderer — paragraph-aware, Life of Fred style ────────────
// Splits content on blank lines, renders first paragraph as a large hook,
// subsequent paragraphs at a comfortable reading size with generous spacing.

function LessonContent({
  content,
  fontFamily = "var(--font-kalam), cursive",
  color = "#2F4731",
}: {
  content: string;
  fontFamily?: string;
  color?: string;
}) {
  const paragraphs = content
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  if (paragraphs.length === 0) return null;

  return (
    <div className="space-y-5">
      {paragraphs.map((para, i) => {
        // Bold/italic markdown — **text** and *text*
        const formatted = para
          .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
          .replace(/\*(.+?)\*/g, "<em>$1</em>");

        return (
          <p
            key={i}
            className={i === 0 ? "text-xl leading-[1.85]" : "text-[17px] leading-[1.85]"}
            style={{ fontFamily, color }}
            dangerouslySetInnerHTML={{ __html: formatted }}
          />
        );
      })}
    </div>
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
      <LessonContent content={content} color="#2F4731" />
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
      <LessonContent content={block.content} fontFamily="var(--font-swanky), cursive" color="#2F4731" />
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
      <LessonContent content={content} color="#2F4731" />
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
      <p className="text-sm text-[#2F4731]/50 italic" style={{ fontFamily: "var(--font-kalam), cursive" }}>
        No verified archive source was found. This is your research mission.
      </p>
    </div>
  );
}

// ── QUIZ block ────────────────────────────────────────────────────────────────

function QuizBlock({ block }: { block: LessonBlockResponse }) {
  // If adapter generated structured quiz_data, use the interactive QuizCard
  if (block.quiz_data) {
    const qd = block.quiz_data;
    const options = qd.options.map((o) => o.text);
    const correctIndex = qd.options.findIndex((o) => o.is_correct);
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 px-1">
          <span className="text-lg">❓</span>
          <BlockLabel type="QUIZ" />
        </div>
        <QuizCard
          question={qd.question}
          options={options}
          correctIndex={correctIndex >= 0 ? correctIndex : 0}
          explanation={qd.explanation}
        />
      </div>
    );
  }
  // Fallback: open-ended text response
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

// ── FLASHCARD block ───────────────────────────────────────────────────────────

function FlashcardBlock({ block }: { block: LessonBlockResponse }) {
  if (block.flashcard_data) {
    const fd = block.flashcard_data;
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 px-1">
          <span className="text-lg">🃏</span>
          <BlockLabel type="FLASHCARD" />
        </div>
        <Flashcard
          term={fd.front}
          definition={fd.back}
          category={fd.category}
        />
      </div>
    );
  }
  // Fallback if no structured data
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#ECFEFF", border: "1.5px solid #0E7490" }}
    >
      <BlockLabel type="FLASHCARD" />
      <LessonContent content={block.content} color="#0C4A6E" />
    </div>
  );
}

// ── INTERACTIVE_SIM block (placeholder) ──────────────────────────────────────

function InteractiveSimBlock({ block }: { block: LessonBlockResponse }) {
  const sim = (block as any).interactive_sim_data;
  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#ECFDF5", border: "2px dashed #065F46" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">⚙️</span>
        <BlockLabel type="INTERACTIVE_SIM" />
        <span className="ml-auto text-xs font-bold text-[#065F46] uppercase tracking-wider">
          Coming Soon
        </span>
      </div>
      <p className="font-bold text-[#065F46]">{sim?.title ?? block.content}</p>
      {sim?.instructions && (
        <p className="text-sm text-[#2F4731]/70 italic">{sim.instructions}</p>
      )}
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
      <p className="text-sm text-[#6B21A8] font-semibold uppercase tracking-widest">
        {data.concept}
      </p>
      <div className="flex gap-1 flex-wrap">
        {data.acronym.split("").map((letter, i) => (
          <div key={i} className="text-center">
            <div className="text-2xl font-black text-[#6B21A8] leading-none">{letter}</div>
            <div className="text-xs text-[#374151] mt-1 max-w-[56px] leading-tight">
              {data.words[i] ?? ""}
            </div>
          </div>
        ))}
      </div>
      <p className="text-base text-[#374151] italic border-t border-[#E9D5FF] pt-2">
        {data.tip}
      </p>
    </div>
  );
}

// ── NARRATED_SLIDE block ──────────────────────────────────────────────────────

function NarratedSlideBlock({ block }: { block: LessonBlockResponse }) {
  const data = block.narrated_slide_data;
  if (!data || data.slides.length === 0) return null;
  return <NarratedSlides data={data} />;
}

// ── BOOK_SUGGESTION block ──────────────────────────────────────────────────────

function BookSuggestionBlock({ block }: { block: LessonBlockResponse }) {
  const bookId = (block as any).book_id || "";
  const bookTitle = (block as any).book_title || "Suggested Book";
  const bookAuthor = (block as any).book_author || "";
  const epubUrl = (block as any).epub_url || "";
  const coverUrl = (block as any).cover_url || "";
  const lexileLevel = (block as any).lexile_level;

  return (
    <div
      className="rounded-xl p-5 space-y-3"
      style={{ background: "#FFFBEB", border: "1.5px solid #78350F40" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">📚</span>
        <BlockLabel type="BOOK_SUGGESTION" />
      </div>
      <div className="flex gap-4">
        {coverUrl && (
          <img
            src={coverUrl}
            alt={bookTitle}
            className="w-20 h-28 object-cover rounded-lg shadow-sm bg-[#E7DAC3]"
          />
        )}
        <div className="flex-1 space-y-2">
          <h3 className="font-bold text-[#78350F] text-lg leading-tight">{bookTitle}</h3>
          {bookAuthor && (
            <p className="text-sm text-[#2F4731]/70">by {bookAuthor}</p>
          )}
          {lexileLevel && (
            <span className="inline-block px-2 py-0.5 text-xs font-bold bg-[#E7DAC3] text-[#2F4731] rounded-full">
              {lexileLevel}L
            </span>
          )}
          {block.content && (
            <p
              className="text-sm text-[#374151] leading-relaxed"
              style={{ fontFamily: "var(--font-kalam), cursive" }}
            >
              {block.content}
            </p>
          )}
        </div>
      </div>
      {bookId && epubUrl && (
        <Link
          href={`/dashboard/reading-nook?bookId=${bookId}&url=${encodeURIComponent(epubUrl)}`}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#78350F] text-white rounded-lg hover:bg-[#2F4731] transition-colors font-semibold text-sm"
        >
          📖 Open in Reading Nook
        </Link>
      )}
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

// ── GenUIRenderer (internal — use GenUIRendererWithHighlightAsk as default export) ──

function GenUIRenderer({
  lessonId: _lessonId,
  blocks,
  isHomestead,
  oasStandards = [],
  agentName,
  creditHours,
  studentId,
}: GenUIRendererProps) {
  const visibleBlocks = blocks.filter((b) => !b.is_silenced);

  return (
    <motion.div 
      className="space-y-4"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {visibleBlocks.map((block, index) => {
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
            case "FLASHCARD":
              blockContent = <FlashcardBlock block={block} />;
              break;
            case "INTERACTIVE_SIM":
              blockContent = <InteractiveSimBlock block={block} />;
              break;
            case "GENUI_ASSEMBLY":
              const assemblyData = (block as any).genui_assembly_data;
              blockContent = (
                <DynamicComponent
                  componentType={assemblyData?.component_type || "InteractiveQuiz"}
                  props={assemblyData?.props || {}}
                  initialState={assemblyData?.initial_state || {}}
                  callbacks={assemblyData?.callbacks || []}
                  onStateChange={async (newState) => {
                    // Send to backend to update BKT/ZPD
                    try {
                      const response = await fetch("/api/genui/callback", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                          student_id: studentId ?? "",
                          lesson_id: _lessonId,
                          component_type: assemblyData?.component_type,
                          event: "onStateChange",
                          state: newState,
                          block_id: block.block_id,
                        }),
                      });
                      if (response.ok) {
                        const data = await response.json();
                        console.log("[GENUI] BKT updated:", data.updated_mastery);
                      }
                    } catch (error) {
                      console.error("[GENUI] Callback failed:", error);
                    }
                  }}
                />
              );
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
            case "ANIMATED_SKETCHNOTE_LESSON":
              blockContent = block.animated_sketchnote_data
                ? <AnimatedSketchnoteRenderer lesson={block.animated_sketchnote_data as any} />
                : <TextBlock block={block} />;
              break;
            case "BOOK_SUGGESTION":
              blockContent = <BookSuggestionBlock block={block} />;
              break;
            default:
              blockContent = <TextBlock block={block} />;
          }

          return (
            <motion.div 
              key={block.block_id}
              variants={blockVariants}
              layout
            >
              {blockContent}
              {/* Reality Layer */}
              {(block as any).reality_layer && (
                <motion.div 
                  className="space-y-2 mt-2"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
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
                </motion.div>
              )}
            </motion.div>
          );
        })}

      {oasStandards.length > 0 && (
        <motion.div variants={blockVariants}>
          <OASStandardsSection standards={oasStandards} />
        </motion.div>
      )}

      <motion.div
        variants={blockVariants}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: visibleBlocks.length * 0.15 + 0.3 }}
      >
        <AgentCreditFooter agentName={agentName} creditHours={creditHours} />
      </motion.div>
    </motion.div>
  );
}

// ── GenUIRenderer with Highlight & Ask ────────────────────────────────────────
// Composes the renderer with TextSelectionMenu — students can highlight any
// text and ask Adeline about it. The menu floats above the selection.

export default function GenUIRendererWithHighlightAsk(props: GenUIRendererProps) {
  const handleAskAboutSelection = async (selectedText: string) => {
    // Fire-and-forget: the AdelineChatPanel picks this up via a custom event
    window.dispatchEvent(
      new CustomEvent("adeline:highlight-ask", {
        detail: { text: selectedText, lessonId: props.lessonId },
      })
    );
  };

  return (
    <>
      <TextSelectionMenu
        onAskAboutSelection={handleAskAboutSelection}
        minChars={15}
        maxChars={400}
      />
      <GenUIRenderer {...props} />
    </>
  );
}
