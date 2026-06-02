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

export interface ExtendedEvidence extends Evidence {
  source_type?: "PRIMARY_SOURCE" | "DECLASSIFIED_GOV" | "ARCHIVE_ORG" | "ACADEMIC_JOURNAL" | "PERSONAL_COLLECTION";
}

export interface ExtendedBlockResponse extends LessonBlockResponse {
  interactive_sim_data?: {
    title?: string;
    instructions?: string;
    parameters?: Array<{ name: string; min: number; max: number; step: number; default: number; unit: string }>;
    guided_steps?: string[];
  };
  book_id?: string;
  book_title?: string;
  book_author?: string;
  epub_url?: string;
  cover_url?: string;
  data_tracking_data?: {
    metric_name?: string;
    description?: string;
    unit?: string;
    historical_data?: Array<{ timestamp: string; value: number; label?: string }>;
  };
  problem_data?: {
    title?: string;
    problem_text?: string;
    problem_type?: string;
    correct_answer?: string | number;
    hint?: string;
    solution_text?: string;
    solution_steps?: string[];
  };
  writing_data?: {
    title?: string;
    prompt?: string;
    requirements?: string[];
    rubric?: Record<string, string>;
  };
  highlight_ask_data?: {
    title?: string;
    instructions?: string;
  };
  peer_tutor_data?: {
    title?: string;
    description?: string;
  };
  discussion_forum_data?: {
    title?: string;
    topic?: string;
  };
  audio_dialogue_data?: {
    title?: string;
    description?: string;
    transcript?: string;
    choices?: string[];
    comprehension_questions?: string[];
  };
  embedded_interrupt_data?: {
    title?: string;
    prompt?: string;
    reflection_prompt?: string;
  };
}
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
import { ExperimentCard } from "@/components/gen-ui/patterns/ExperimentCard";
import { LabGuide } from "@/components/gen-ui/patterns/LabGuide";
import { CodePlayground } from "@/components/gen-ui/patterns/CodePlayground";
import { InteractiveConceptMap } from "@/components/gen-ui/patterns/InteractiveConceptMap";
import { MoleculeSimulator } from "@/components/gen-ui/patterns/MoleculeSimulator";
import { SimulationEmbed } from "@/components/gen-ui/patterns/SimulationEmbed";
import { VirtualManipulative } from "@/components/gen-ui/patterns/VirtualManipulative";
import { VideoExplanation } from "@/components/gen-ui/patterns/VideoExplanation";
import { TextExplanation } from "@/components/gen-ui/patterns/TextExplanation";
import { RealWorldApplication } from "@/components/gen-ui/patterns/RealWorldApplication";
import { StealthAssessment } from "@/components/gen-ui/patterns/StealthAssessment";
import { AdaptiveQuiz } from "@/components/gen-ui/patterns/AdaptiveQuiz";
import { MultiCompetencyWorkspace } from "@/components/gen-ui/patterns/MultiCompetencyWorkspace";
import { CorrectiveOverlay } from "@/components/gen-ui/patterns/CorrectiveOverlay";
import { LearningVelocityCard } from "@/components/gen-ui/patterns/LearningVelocityCard";
import { ProgressMap } from "@/components/gen-ui/patterns/ProgressMap";
import { AutoDiagram } from "@/components/gen-ui/patterns/AutoDiagram";
import { PeerTutoringCard } from "@/components/gen-ui/patterns/PeerTutoringCard";
import { DiscussionForum } from "@/components/gen-ui/patterns/DiscussionForum";
import { LessonRatingCard } from "@/components/gen-ui/patterns/LessonRatingCard";
import { AudioDialogue } from "@/components/gen-ui/patterns/AudioDialogue";
import { TextSelectionMenu } from "@/components/gen-ui/TextSelectionMenu";
import { WeightTierBadge } from "@/components/lessons/WeightTierBadge";
import { DistortionFlag } from "@/components/lessons/DistortionFlag";
import { KeystoneConcept } from "@/components/lessons/KeystoneConcept";
import { DistractionBox } from "@/components/lessons/DistractionBox";
import { SourceBadge } from "./SourceBadge";
import Link from "next/link";
import css from "./GenUIRenderer.module.css";

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
  Flashcard:         Flashcard,
  MindMap:           MindMap,
  // Neuroadaptive
  FocusReset:        FocusReset,
  TaskScaffold:      TaskScaffold,
  // Science / lab
  ExperimentCard:    ExperimentCard,
  LabGuide:          LabGuide,
  // Coding
  CodePlayground:    CodePlayground,
  // Knowledge mapping
  InteractiveConceptMap: InteractiveConceptMap,
  // Science simulation
  MoleculeSimulator:     MoleculeSimulator,
  // Presentation
  NarratedSlides:    NarratedSlides,
  EmbeddedInterrupt: EmbeddedInterrupt,
  // Adaptive Learning Path — multimodal
  SimulationEmbed:   SimulationEmbed,
  Simulation:        SimulationEmbed,   // alias
  VirtualManipulative: VirtualManipulative,
  VideoExplanation:  VideoExplanation,
  TextExplanation:   TextExplanation,
  TextDeep:          TextExplanation,   // alias — deeper reading, same renderer
  RealWorldApplication: RealWorldApplication,
  // Adaptive Learning Path — assessment
  StealthAssessment: StealthAssessment,
  AdaptiveQuiz:      AdaptiveQuiz,
  MultiCompetencyWorkspace: MultiCompetencyWorkspace,
  // Adaptive Learning Path — feedback
  CorrectiveOverlay: CorrectiveOverlay,
  // Adaptive Learning Path — visualization
  LearningVelocityCard: LearningVelocityCard,
  ProgressMap:       ProgressMap,
  AutoDiagram:       AutoDiagram,
  ConceptMap:        AutoDiagram,       // alias — concept map uses same diagram renderer
  // Collaborative Learning
  PeerTutoringCard:  PeerTutoringCard,
  DiscussionForum:   DiscussionForum,
  // ALU multimodal — Audio Dialogue
  AudioDialogue:     AudioDialogue,
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
      <div className={clsx("rounded-xl p-4 space-y-2", css.unknownComponent)}>
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
  | "ANIMATED_SKETCHNOTE_LESSON"
  // ALU-tier multimodal blocks
  | "AUDIO_DIALOGUE"
  | "EMBEDDED_INTERRUPT_INLINE"
  // New block types
  | "DATA_TRACKING"
  | "PROBLEM"
  | "WRITING"
  | "PEER_TUTOR"
  | "DISCUSSION_FORUM";

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
  const icons: Record<Evidence["verdict"], string> = {
    VERIFIED:         "✓",
    ARCHIVE_SILENT:   "◎",
    RESEARCH_MISSION: "?",
  };
  const badgeClass =
    verdict === "VERIFIED"         ? css.verdictVerified :
    verdict === "ARCHIVE_SILENT"   ? css.verdictArchiveSilent :
    css.verdictResearchMission;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider",
        badgeClass
      )}
    >
      {icons[verdict]} {verdict.replace(/_/g, " ")}
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
              sourceType={(ev as ExtendedEvidence).source_type ?? "PRIMARY_SOURCE"}
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
  AUDIO_DIALOGUE:              "bg-[#0E7490] text-white",
  EMBEDDED_INTERRUPT_INLINE:   "bg-[#374151] text-white",
  DATA_TRACKING:              "bg-[#0891B2] text-white",
  PROBLEM:                     "bg-[#7C2D12] text-white",
  WRITING:                     "bg-[#4338CA] text-white",
  PEER_TUTOR:                  "bg-[#BE185D] text-white",
  DISCUSSION_FORUM:            "bg-[#047857] text-white",
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
  AUDIO_DIALOGUE:              "Audio Dialogue",
  EMBEDDED_INTERRUPT_INLINE:   "Quick Check",
  DATA_TRACKING:              "Data Tracking",
  PROBLEM:                     "Math Problem",
  WRITING:                     "Writing",
  PEER_TUTOR:                  "Peer Tutor",
  DISCUSSION_FORUM:            "Discussion",
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

// ── Font / color helpers (avoid inline styles) ─────────────────────────────────

function _fontClass(fontFamily: string): string {
  if (fontFamily.includes("swanky")) return css.fontSwanky;
  if (fontFamily.includes("permanent-marker")) return css.fontPermanentMarker;
  if (fontFamily.includes("kranky")) return css.fontKranky;
  return css.fontKalam;
}

function _colorClass(color: string): string {
  const map: Record<string, string> = {
    "#2F4731": css.colorDarkGreen,
    "#991B1B": css.colorDarkRed,
    "#0C4A6E": css.colorDarkCyan,
    "#374151": css.colorGray,
    "#312E81": css.colorIndigo,
  };
  return map[color] || "";
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
        // Escape raw HTML first, then apply markdown so the italic regex
        // cannot consume asterisks inside already-converted <strong> tags.
        const escaped = para
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
        const formatted = escaped
          .replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>")
          .replace(/\*([^*]+?)\*/g, "<em>$1</em>");

        return (
          <p
            key={i}
            className={clsx(
              i === 0 ? "text-xl leading-[1.85]" : "text-[17px] leading-[1.85]",
              _fontClass(fontFamily),
              _colorClass(color)
            )}
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
    <div className={clsx("rounded-xl p-5 space-y-3", css.primarySource)}>
      <BlockLabel type="PRIMARY_SOURCE" />
      <LessonContent content={content} color="#2F4731" />
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── LAB_MISSION block ─────────────────────────────────────────────────────────

function LabMissionBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div className={clsx("rounded-xl p-5 space-y-3", css.labMission)}>
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
    <div className={clsx("rounded-xl p-5 space-y-3", css.experiment)}>
      <div className="flex items-center gap-2">
        <span className="text-xl">🧪</span>
        <BlockLabel type="EXPERIMENT" />
        <span className="ml-auto text-xs font-black uppercase tracking-wider text-[#BD6809]">
          Sovereign Lab
        </span>
      </div>
      <p className={clsx("text-base text-[#2F4731] leading-relaxed whitespace-pre-wrap font-medium", css.fontKalam)}>
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
    <div className={clsx("rounded-xl p-5 space-y-3", css.narrative)}>
      <BlockLabel type="NARRATIVE" />
      <LessonContent content={content} color="#2F4731" />
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}

// ── RESEARCH_MISSION block ────────────────────────────────────────────────────

function ResearchMissionBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div className={clsx("rounded-xl p-5 space-y-3", css.researchMission)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">🔍</span>
        <BlockLabel type="RESEARCH_MISSION" />
      </div>
      <p className={clsx("text-base text-[#991B1B] leading-[1.8] whitespace-pre-wrap font-bold", css.fontPermanentMarker)}>
        {block.content}
      </p>
      <p className={clsx("text-sm text-[#2F4731]/50 italic", css.fontKalam)}>
        No verified archive source was found. This is your research mission.
      </p>
    </div>
  );
}

// ── QUIZ block ────────────────────────────────────────────────────────────────

function QuizBlock({ block }: { block: LessonBlockResponse }) {
  // Path 1: adapter-generated quiz_data with {text, is_correct} option format
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

  // Path 2: enrichment-generated quiz stored as JSON in content field.
  // Gemini format: [{question, options: string[], correctIndex, explanation}]
  try {
    const parsed = JSON.parse(block.content);
    const questions: Array<{
      id?: string;
      question: string;
      options: string[];
      correctIndex: number;
      explanation?: string;
    }> = Array.isArray(parsed) ? parsed : [parsed];
    if (questions.length > 0 && questions[0].question && Array.isArray(questions[0].options)) {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <span className="text-lg">❓</span>
            <BlockLabel type="QUIZ" />
          </div>
          {questions.map((q, i) => (
            <QuizCard
              key={q.id ?? i}
              question={q.question}
              options={q.options}
              correctIndex={typeof q.correctIndex === "number" ? q.correctIndex : 0}
              explanation={q.explanation}
            />
          ))}
        </div>
      );
    }
  } catch {
    // not JSON — fall through to open-ended textarea
  }

  // Path 3: plain-text open-ended question (no structured data)
  return (
    <div className={clsx("rounded-xl p-5 space-y-3", css.quiz)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">❓</span>
        <BlockLabel type="QUIZ" />
      </div>
      <p className={clsx("text-lg text-[#312E81] leading-[1.7] whitespace-pre-wrap font-bold", css.fontKranky)}>
        {block.content}
      </p>
      <textarea
        className={clsx("w-full mt-1 px-3 py-2 text-base text-[#2F4731] bg-white border border-[#4F46E5]/30 rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-[#4F46E5]", css.fontKalam)}
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
    <div className={clsx("rounded-xl p-5 space-y-3", css.flashcard)}>
      <BlockLabel type="FLASHCARD" />
      <LessonContent content={block.content} color="#0C4A6E" />
    </div>
  );
}

// ── INTERACTIVE_SIM block ─────────────────────────────────────────────────────

function InteractiveSimBlock({ block }: { block: LessonBlockResponse }) {
  const sim = (block as ExtendedBlockResponse).interactive_sim_data;
  const [isRunning, setIsRunning] = useState(false);
  const [parameters, setParameters] = useState<Record<string, number>>({});
  const [results, setResults] = useState<Record<string, number>>({});

  const handleParameterChange = (param: string, value: number) => {
    setParameters({ ...parameters, [param]: value });
  };

  const handleRunSimulation = () => {
    setIsRunning(true);
    // Simulate calculation - in production this would call a simulation API
    setTimeout(() => {
      const simulatedResults: Record<string, number> = {};
      Object.keys(parameters).forEach(key => {
        simulatedResults[key] = parameters[key] * (0.8 + Math.random() * 0.4); // Simple simulation
      });
      setResults(simulatedResults);
      setIsRunning(false);
    }, 1000);
  };

  const handleReset = () => {
    setParameters({});
    setResults({});
    setIsRunning(false);
  };

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.interactiveSim)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">⚙️</span>
        <BlockLabel type="INTERACTIVE_SIM" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{sim?.title || 'Interactive Simulation'}</h3>
        <p className="text-sm text-[#4B3424]">{sim?.instructions || block.content}</p>
      </div>

      {/* Simulation Parameters */}
      {sim?.parameters && sim.parameters.length > 0 && (
        <div className="bg-[#FFF8EE] rounded-lg p-4 space-y-3">
          <h4 className="font-semibold text-sm text-[#2F4731]">Parameters</h4>
          <div className="grid grid-cols-2 gap-3">
            {sim.parameters.map((param, i) => (
              <div key={i}>
                <label className="block text-xs font-semibold text-[#2F4731] mb-1">
                  {param.name}
                </label>
                <input
                  type="range"
                  min={param.min || 0}
                  max={param.max || 100}
                  step={param.step || 1}
                  value={parameters[param.name] || param.default || 50}
                  onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="text-xs text-[#4B3424] text-center mt-1">
                  {parameters[param.name] || param.default || 50} {param.unit}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Simulation Controls */}
      <div className="flex gap-2">
        <button
          onClick={handleRunSimulation}
          disabled={isRunning || Object.keys(parameters).length === 0}
          className="flex-1 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold text-sm transition-colors"
        >
          {isRunning ? 'Running...' : 'Run Simulation'}
        </button>
        <button
          onClick={handleReset}
          className="px-4 py-2 border border-[#E7DAC3] text-[#2F4731] rounded-lg hover:bg-[#FFF8EE] font-semibold text-sm transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Results Display */}
      {Object.keys(results).length > 0 && (
        <div className="bg-white rounded-lg p-4 border border-[#E7DAC3] space-y-3">
          <h4 className="font-semibold text-sm text-[#2F4731]">Results</h4>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(results).map(([key, value]) => (
              <div key={key} className="bg-[#FFF8EE] rounded-lg p-3">
                <div className="text-xs text-[#4B3424] mb-1">{key}</div>
                <div className="font-bold text-[#2F4731]">{value.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Guided Exploration Mode */}
      {sim?.guided_steps && sim.guided_steps.length > 0 && (
        <div className="space-y-2">
          <button className="text-sm text-[#BD6809] hover:text-[#a05a08] font-semibold">
            Show Guided Exploration
          </button>
          <div className="bg-[#FFF8EE] rounded-lg p-3 space-y-2">
            {sim.guided_steps.map((step, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-[#4B3424]">
                <span className="font-bold text-[#BD6809]">{i + 1}.</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── TEXT / fallback block ─────────────────────────────────────────────────────

function TextBlock({ block }: { block: LessonBlockResponse }) {
  return (
    <div className={clsx("rounded-xl p-5 space-y-2", css.textBlock)}>
      <BlockLabel type="TEXT" />
      <LessonContent
        content={block.content}
        fontFamily="var(--font-kalam), cursive"
        color="#374151"
      />
    </div>
  );
}

// ── MIND_MAP block ────────────────────────────────────────────────────────────

function MindMapBlock({ block }: { block: LessonBlockResponse }) {
  if (!block.mind_map_data) return null;
  return (
    <div className={clsx("rounded-xl overflow-hidden", css.mindMap)}>
      <MindMap data={block.mind_map_data} />
    </div>
  );
}

// ── TIMELINE block ────────────────────────────────────────────────────────────

function TimelineBlock({ block }: { block: LessonBlockResponse }) {
  if (!block.timeline_data) return null;
  return (
    <div className={clsx("rounded-xl overflow-hidden", css.timeline)}>
      <Timeline data={block.timeline_data} evidence={block.evidence} />
    </div>
  );
}

// ── MNEMONIC block ────────────────────────────────────────────────────────────

function MnemonicBlock({ block }: { block: LessonBlockResponse }) {
  const data = block.mnemonic_data;
  if (!data) return null;
  return (
    <div className={clsx("rounded-xl p-5 space-y-3", css.mnemonic)}>
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
  const extBlock = block as ExtendedBlockResponse;
  const bookId = extBlock.book_id || "";
  const bookTitle = extBlock.book_title || "Suggested Book";
  const bookAuthor = extBlock.book_author || "";
  const epubUrl = extBlock.epub_url || "";
  const coverUrl = extBlock.cover_url || "";
  const lexileLevel = extBlock.lexile_level;

  return (
    <div className={clsx("rounded-xl p-5 space-y-3", css.bookSuggestion)}>
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
            <p className={clsx("text-sm text-[#374151] leading-relaxed", css.fontKalam)}>
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

// ── DATA_TRACKING block ───────────────────────────────────────────────────────

function DataTrackingBlock({ block }: { block: LessonBlockResponse }) {
  const tracking = (block as ExtendedBlockResponse).data_tracking_data;
  const [dataPoints, setDataPoints] = useState<Array<{ timestamp: string; value: number; label?: string }>>(tracking?.historical_data || []);
  const [newValue, setNewValue] = useState('');
  const [newLabel, setNewLabel] = useState('');

  const handleAddData = () => {
    if (newValue && !isNaN(parseFloat(newValue))) {
      setDataPoints([...dataPoints, {
        timestamp: new Date().toISOString(),
        value: parseFloat(newValue),
        label: newLabel || undefined
      }]);
      setNewValue('');
      setNewLabel('');
    }
  };

  const handleExportCSV = () => {
    const csv = [
      ['Timestamp', 'Value', 'Label'].join(','),
      ...dataPoints.map(dp => [
        new Date(dp.timestamp).toLocaleString(),
        dp.value,
        dp.label || ''
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tracking?.metric_name || 'data'}-tracking.csv`;
    a.click();
  };

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.dataTracking)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">📊</span>
        <BlockLabel type="DATA_TRACKING" />
      </div>
      
      <div className="space-y-2">
        <h3 className="font-bold text-[#2F4731]">{tracking?.metric_name || 'Data Tracking'}</h3>
        <p className="text-sm text-[#4B3424]">{tracking?.description || block.content}</p>
      </div>

      {/* Data Entry Form */}
      <div className="bg-[#FFF8EE] rounded-lg p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-[#2F4731] mb-1">
              {tracking?.unit || 'Value'}
            </label>
            <input
              type="number"
              step="0.01"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              placeholder="Enter value"
              className="w-full px-3 py-2 rounded-lg border border-[#E7DAC3] text-sm focus:outline-none focus:border-[#BD6809]"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-[#2F4731] mb-1">
              Label (optional)
            </label>
            <input
              type="text"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="e.g., Morning reading"
              className="w-full px-3 py-2 rounded-lg border border-[#E7DAC3] text-sm focus:outline-none focus:border-[#BD6809]"
            />
          </div>
        </div>
        <button
          onClick={handleAddData}
          disabled={!newValue}
          className="w-full py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold text-sm transition-colors"
        >
          Add Data Point
        </button>
      </div>

      {/* Historical Data Display */}
      {dataPoints.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-sm text-[#2F4731]">Historical Data ({dataPoints.length} points)</h4>
            <button
              onClick={handleExportCSV}
              className="text-xs text-[#BD6809] hover:text-[#a05a08] font-semibold"
            >
              Export CSV
            </button>
          </div>
          
          {/* Simple Chart Visualization */}
          <div className="bg-white rounded-lg p-4 border border-[#E7DAC3]">
            <div className="flex items-end gap-1 h-32">
              {dataPoints.slice(-10).map((dp, i) => {
                const maxValue = Math.max(...dataPoints.map(d => d.value));
                const height = maxValue > 0 ? (dp.value / maxValue) * 100 : 0;
                return (
                  <div
                    key={i}
                    className="flex-1 bg-[#BD6809] rounded-t hover:bg-[#a05a08] transition-colors relative group"
                    style={{ height: `${Math.max(height, 5)}%` }}
                  >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[#2F4731] text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                      {dp.value} {tracking?.unit}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Data Table */}
          <div className="max-h-40 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#E7DAC3] sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-[#2F4731]">Date</th>
                  <th className="px-3 py-2 text-left font-semibold text-[#2F4731]">Label</th>
                  <th className="px-3 py-2 text-right font-semibold text-[#2F4731]">Value</th>
                </tr>
              </thead>
              <tbody>
                {dataPoints.slice().reverse().map((dp, i) => (
                  <tr key={i} className="border-b border-[#E7DAC3]">
                    <td className="px-3 py-2 text-[#4B3424]">
                      {new Date(dp.timestamp).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2 text-[#4B3424]">{dp.label || '-'}</td>
                    <td className="px-3 py-2 text-right font-semibold text-[#2F4731]">
                      {dp.value} {tracking?.unit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── PROBLEM block ─────────────────────────────────────────────────────────────

function ProblemBlock({ block }: { block: LessonBlockResponse }) {
  const problem = (block as ExtendedBlockResponse).problem_data;
  const [showSolution, setShowSolution] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [userAnswer, setUserAnswer] = useState('');
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

  const handleCheckAnswer = () => {
    if (problem?.correct_answer && userAnswer.trim()) {
      // Simple comparison - could be enhanced for different problem types
      const normalizedUserAnswer = userAnswer.trim().toLowerCase();
      const normalizedCorrect = problem.correct_answer.toString().trim().toLowerCase();
      setIsCorrect(normalizedUserAnswer === normalizedCorrect);
    }
  };

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.problem)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">🧮</span>
        <BlockLabel type="PROBLEM" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{problem?.title || 'Math Problem'}</h3>
        <div className={clsx("text-[#374151] leading-relaxed", css.fontKalam)}>
          <LessonContent content={problem?.problem_text || block.content} color="#2F4731" />
        </div>
      </div>

      {/* Problem Type Badge */}
      {problem?.problem_type && (
        <span className="inline-block px-3 py-1 text-xs font-bold bg-[#E7DAC3] text-[#2F4731] rounded-full">
          {problem.problem_type}
        </span>
      )}

      {/* Work Area */}
      <div className="bg-[#FFF8EE] rounded-lg p-4 space-y-3">
        <div>
          <label className="block text-xs font-semibold text-[#2F4731] mb-2">
            Your Work Area
          </label>
          <textarea
            placeholder="Show your work here..."
            className="w-full h-24 px-3 py-2 rounded-lg border border-[#E7DAC3] text-sm focus:outline-none focus:border-[#BD6809] resize-none"
          />
        </div>
      </div>

      {/* Answer Input */}
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-[#2F4731] mb-2">
            Your Answer
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder="Enter your answer"
              className="flex-1 px-3 py-2 rounded-lg border border-[#E7DAC3] text-sm focus:outline-none focus:border-[#BD6809]"
            />
            <button
              onClick={handleCheckAnswer}
              disabled={!userAnswer.trim()}
              className="px-4 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold text-sm transition-colors"
            >
              Check
            </button>
          </div>
        </div>

        {/* Feedback */}
        {isCorrect !== null && (
          <div className={clsx(
            "p-3 rounded-lg text-sm font-semibold",
            isCorrect ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
          )}>
            {isCorrect ? "✓ Correct! Great work!" : "✗ Not quite. Try again or use a hint."}
          </div>
        )}
      </div>

      {/* Hint System */}
      <div className="space-y-2">
        <button
          onClick={() => setShowHint(!showHint)}
          className="text-sm text-[#BD6809] hover:text-[#a05a08] font-semibold"
        >
          {showHint ? "Hide Hint" : "Show Hint"}
        </button>
        {showHint && problem?.hint && (
          <div className="bg-[#FFF8EE] rounded-lg p-3 text-sm text-[#4B3424]">
            💡 {problem.hint}
          </div>
        )}
      </div>

      {/* Step-by-Step Solution */}
      <div className="space-y-2">
        <button
          onClick={() => setShowSolution(!showSolution)}
          className="text-sm text-[#BD6809] hover:text-[#a05a08] font-semibold"
        >
          {showSolution ? "Hide Solution" : "Show Solution"}
        </button>
        {showSolution && (
          <div className="bg-white rounded-lg p-4 border border-[#E7DAC3] space-y-3">
            {problem?.solution_steps && problem.solution_steps.length > 0 ? (
              <ol className="space-y-2 text-sm text-[#4B3424]">
                {problem.solution_steps.map((step, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="font-bold text-[#BD6809]">{i + 1}.</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-[#4B3424]">
                {problem?.solution_text || "Solution: " + (problem?.correct_answer || "See your teacher for the solution.")}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── WRITING block ─────────────────────────────────────────────────────────────

function WritingBlock({ block }: { block: LessonBlockResponse }) {
  const writing = (block as ExtendedBlockResponse).writing_data;
  const [content, setContent] = useState('');
  const [wordCount, setWordCount] = useState(0);
  const [readabilityScore, setReadabilityScore] = useState<string>('');

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    
    // Calculate word count
    const words = newContent.trim().split(/\s+/).filter(word => word.length > 0);
    setWordCount(words.length);
    
    // Simple readability score (Flesch-Kincaid approximation)
    if (words.length > 0) {
      const sentences = newContent.split(/[.!?]+/).filter(s => s.trim().length > 0);
      const syllables = words.reduce((acc, word) => acc + countSyllables(word), 0);
      const avgSentenceLength = words.length / Math.max(sentences.length, 1);
      const avgSyllablesPerWord = syllables / words.length;
      const score = 206.835 - (1.015 * avgSentenceLength) - (84.6 * avgSyllablesPerWord);
      
      if (score >= 90) setReadabilityScore('Very Easy (5th grade)');
      else if (score >= 80) setReadabilityScore('Easy (6th grade)');
      else if (score >= 70) setReadabilityScore('Fairly Easy (7th grade)');
      else if (score >= 60) setReadabilityScore('Standard (8th-9th grade)');
      else if (score >= 50) setReadabilityScore('Fairly Difficult (10th-12th grade)');
      else if (score >= 30) setReadabilityScore('Difficult (College)');
      else setReadabilityScore('Very Difficult (Graduate)');
    } else {
      setReadabilityScore('');
    }
  };

  const countSyllables = (word: string): number => {
    word = word.toLowerCase().replace(/[^a-z]/g, '');
    if (word.length <= 3) return 1;
    word = word.replace(/(?:[^laeiouy]es|ed|[^laeiouy]e)$/, '');
    word = word.replace(/^y/, '');
    const matches = word.match(/[aeiouy]{1,2}/g);
    return matches ? matches.length : 1;
  };

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.writing)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">✍️</span>
        <BlockLabel type="WRITING" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{writing?.title || 'Writing Assignment'}</h3>
        <p className="text-sm text-[#4B3424]">{writing?.prompt || block.content}</p>
      </div>

      {/* Writing Requirements */}
      {writing?.requirements && (
        <div className="bg-[#FFF8EE] rounded-lg p-3 space-y-2">
          <h4 className="font-semibold text-sm text-[#2F4731]">Requirements:</h4>
          <ul className="text-sm text-[#4B3424] space-y-1">
            {writing.requirements.map((req, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-[#BD6809]">•</span>
                <span>{req}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Rubric */}
      {writing?.rubric && (
        <div className="bg-white rounded-lg p-3 border border-[#E7DAC3]">
          <h4 className="font-semibold text-sm text-[#2F4731] mb-2">Rubric:</h4>
          <div className="text-sm text-[#4B3424] space-y-1">
            {Object.entries(writing.rubric).map(([criteria, description]) => (
              <div key={criteria} className="flex gap-2">
                <span className="font-semibold text-[#BD6809]">{criteria}:</span>
                <span>{description as string}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rich Text Editor */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-[#2F4731]">
          Your Response
        </label>
        <textarea
          value={content}
          onChange={handleContentChange}
          placeholder="Start writing here..."
          className="w-full h-64 px-4 py-3 rounded-lg border border-[#E7DAC3] text-sm focus:outline-none focus:border-[#BD6809] resize-none"
        />
      </div>

      {/* Writing Metrics */}
      <div className="flex gap-4 text-sm">
        <div className="flex-1 bg-[#FFF8EE] rounded-lg p-3">
          <div className="text-xs text-[#4B3424] mb-1">Word Count</div>
          <div className="font-bold text-[#2F4731]">{wordCount}</div>
        </div>
        <div className="flex-1 bg-[#FFF8EE] rounded-lg p-3">
          <div className="text-xs text-[#4B3424] mb-1">Readability</div>
          <div className="font-bold text-[#2F4731] text-xs">{readabilityScore || 'N/A'}</div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => setContent('')}
          className="flex-1 py-2 border border-[#E7DAC3] text-[#2F4731] rounded-lg hover:bg-[#FFF8EE] font-semibold text-sm transition-colors"
        >
          Clear
        </button>
        <button
          onClick={() => {/* Save draft functionality */}}
          className="flex-1 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] font-semibold text-sm transition-colors"
        >
          Save Draft
        </button>
        <button
          onClick={() => {/* Submit functionality */}}
          disabled={wordCount === 0}
          className="flex-1 py-2 bg-[#2F4731] text-white rounded-lg hover:bg-[#243828] disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold text-sm transition-colors"
        >
          Submit
        </button>
      </div>
    </div>
  );
}

// ── HIGHLIGHT_ASK block ───────────────────────────────────────────────────────

function HighlightAskBlock({ block }: { block: LessonBlockResponse }) {
  const highlightData = (block as ExtendedBlockResponse).highlight_ask_data;
  const [selectedText, setSelectedText] = useState('');
  const [explanation, setExplanation] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleTextSelection = () => {
    const selection = window.getSelection();
    const text = selection?.toString() || '';
    if (text.length > 0) {
      setSelectedText(text);
      // In production, this would call an AI API to get contextual explanation
      setExplanation(`AI explanation for: "${text}" - This feature would connect to the brain API for contextual explanations.`);
    }
  };

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.highlightAsk)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">💡</span>
        <BlockLabel type="HIGHLIGHT_ASK" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{highlightData?.title || 'Highlight & Ask'}</h3>
        <p className="text-sm text-[#4B3424]">{highlightData?.instructions || 'Highlight any text in the passage below to get a contextual explanation.'}</p>
      </div>

      {/* Text Content with Highlighting */}
      <div 
        className="bg-white rounded-lg p-4 border border-[#E7DAC3] leading-relaxed"
        onMouseUp={handleTextSelection}
      >
        <LessonContent content={block.content} color="#2F4731" />
      </div>

      {/* Selected Text Display */}
      {selectedText && (
        <div className="bg-[#FFF8EE] rounded-lg p-3 space-y-2">
          <div className="text-xs font-semibold text-[#2F4731]">Selected Text:</div>
          <div className="text-sm text-[#4B3424] italic">"{selectedText}"</div>
        </div>
      )}

      {/* AI Explanation */}
      {explanation && (
        <div className="bg-[#E7DAC3] rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">🤖</span>
            <div className="text-xs font-semibold text-[#2F4731]">AI Explanation</div>
          </div>
          <p className="text-sm text-[#4B3424]">{explanation}</p>
        </div>
      )}

      {/* Color Legend */}
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-yellow-300 rounded"></div>
          <span className="text-[#4B3424]">Vocabulary</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-blue-300 rounded"></div>
          <span className="text-[#4B3424]">Key Concepts</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-300 rounded"></div>
          <span className="text-[#4B3424]">Evidence</span>
        </div>
      </div>
    </div>
  );
}

// ── PEER_TUTOR block ───────────────────────────────────────────────────────────

function PeerTutorBlock({ block }: { block: LessonBlockResponse }) {
  const peerData = (block as ExtendedBlockResponse).peer_tutor_data;
  const [isMatched, setIsMatched] = useState(false);
  const [matchedPeer, setMatchedPeer] = useState<{ name: string; grade: string } | null>(null);

  const handleFindPeer = () => {
    // Simulate peer matching - in production this would call the matching API
    setIsMatched(true);
    setMatchedPeer({
      name: 'Sarah',
      grade: '8th Grade'
    });
  };

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.peerTutor)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">👥</span>
        <BlockLabel type="PEER_TUTOR" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{peerData?.title || 'Peer Tutoring'}</h3>
        <p className="text-sm text-[#4B3424]">{peerData?.description || 'Connect with a peer for collaborative learning.'}</p>
      </div>

      {!isMatched ? (
        <div className="space-y-3">
          <div className="bg-[#FFF8EE] rounded-lg p-4 text-center">
            <p className="text-sm text-[#4B3424] mb-3">
              Find a peer who's working on similar topics or can help you with this concept.
            </p>
            <button
              onClick={handleFindPeer}
              className="px-6 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] font-semibold text-sm transition-colors"
            >
              Find a Peer
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="bg-green-50 rounded-lg p-4 border border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">✅</span>
              <div className="font-semibold text-sm text-green-800">Peer Matched!</div>
            </div>
            <div className="text-sm text-green-700">
              You've been matched with <strong>{matchedPeer?.name}</strong> ({matchedPeer?.grade})
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button className="py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] font-semibold text-sm transition-colors">
              Start Video Call
            </button>
            <button className="py-2 border border-[#E7DAC3] text-[#2F4731] rounded-lg hover:bg-[#FFF8EE] font-semibold text-sm transition-colors">
              Send Message
            </button>
          </div>

          <div className="bg-white rounded-lg p-3 border border-[#E7DAC3]">
            <div className="text-xs font-semibold text-[#2F4731] mb-2">Shared Whiteboard</div>
            <div className="h-32 bg-[#FFF8EE] rounded-lg flex items-center justify-center text-sm text-[#4B3424]">
              Collaborative whiteboard would load here
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── DISCUSSION_FORUM block ─────────────────────────────────────────────────────

function DiscussionForumBlock({ block }: { block: LessonBlockResponse }) {
  const forumData = (block as ExtendedBlockResponse).discussion_forum_data;
  const [newPost, setNewPost] = useState('');

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.discussionForum)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">💬</span>
        <BlockLabel type="DISCUSSION_FORUM" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{forumData?.title || 'Discussion Forum'}</h3>
        <p className="text-sm text-[#4B3424]">{forumData?.topic || block.content}</p>
      </div>

      {/* New Post Input */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-[#2F4731]">
          Share your thoughts
        </label>
        <textarea
          value={newPost}
          onChange={(e) => setNewPost(e.target.value)}
          placeholder="What do you think about this topic?"
          className="w-full h-24 px-3 py-2 rounded-lg border border-[#E7DAC3] text-sm focus:outline-none focus:border-[#BD6809] resize-none"
        />
        <button
          onClick={() => setNewPost('')}
          disabled={!newPost.trim()}
          className="px-4 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold text-sm transition-colors"
        >
          Post
        </button>
      </div>

      {/* Sample Discussion Posts */}
      <div className="space-y-3">
        <div className="text-xs font-semibold text-[#2F4731]">Recent Discussion</div>
        
        <div className="bg-white rounded-lg p-3 border border-[#E7DAC3] space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#BD6809] rounded-full flex items-center justify-center text-white text-xs font-bold">
              JD
            </div>
            <div>
              <div className="text-sm font-semibold text-[#2F4731]">John D.</div>
              <div className="text-xs text-[#4B3424]">2 hours ago</div>
            </div>
          </div>
          <p className="text-sm text-[#4B3424]">
            I think this concept connects well to what we learned about soil composition last week.
          </p>
          <div className="flex gap-3 text-xs">
            <button className="text-[#BD6809] hover:text-[#a05a08] font-semibold">👍 3</button>
            <button className="text-[#BD6809] hover:text-[#a05a08] font-semibold">Reply</button>
          </div>
        </div>

        <div className="bg-white rounded-lg p-3 border border-[#E7DAC3] space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#2F4731] rounded-full flex items-center justify-center text-white text-xs font-bold">
              SM
            </div>
            <div>
              <div className="text-sm font-semibold text-[#2F4731]">Sarah M.</div>
              <div className="text-xs text-[#4B3424]">5 hours ago</div>
            </div>
          </div>
          <p className="text-sm text-[#4B3424]">
            Great point! I also noticed the connection to the farming methods we studied.
          </p>
          <div className="flex gap-3 text-xs">
            <button className="text-[#BD6809] hover:text-[#a05a08] font-semibold">👍 5</button>
            <button className="text-[#BD6809] hover:text-[#a05a08] font-semibold">Reply</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── AUDIO_DIALOGUE block ───────────────────────────────────────────────────────

function AudioDialogueBlock({ block }: { block: LessonBlockResponse }) {
  const audioData = (block as ExtendedBlockResponse).audio_dialogue_data;
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentChoice, setCurrentChoice] = useState<number | null>(null);

  return (
    <div className={clsx("rounded-xl p-5 space-y-4", css.audioDialogue)}>
      <div className="flex items-center gap-2">
        <span className="text-lg">🎧</span>
        <BlockLabel type="AUDIO_DIALOGUE" />
      </div>

      <div className="space-y-3">
        <h3 className="font-bold text-[#2F4731]">{audioData?.title || 'Audio Dialogue'}</h3>
        <p className="text-sm text-[#4B3424]">{audioData?.description || block.content}</p>
      </div>

      {/* Audio Player */}
      <div className="bg-white rounded-lg p-4 border border-[#E7DAC3] space-y-3">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-12 h-12 bg-[#BD6809] text-white rounded-full flex items-center justify-center hover:bg-[#a05a08] transition-colors"
          >
            {isPlaying ? '⏸' : '▶️'}
          </button>
          <div className="flex-1">
            <div className="h-2 bg-[#E7DAC3] rounded-full overflow-hidden">
              <div className="h-full bg-[#BD6809] w-1/3"></div>
            </div>
            <div className="flex justify-between text-xs text-[#4B3424] mt-1">
              <span>1:23</span>
              <span>4:56</span>
            </div>
          </div>
        </div>

        {/* Playback Speed Controls */}
        <div className="flex gap-2 text-xs">
          <button className="px-2 py-1 bg-[#FFF8EE] rounded hover:bg-[#E7DAC3]">0.5x</button>
          <button className="px-2 py-1 bg-[#BD6809] text-white rounded">1x</button>
          <button className="px-2 py-1 bg-[#FFF8EE] rounded hover:bg-[#E7DAC3]">1.5x</button>
          <button className="px-2 py-1 bg-[#FFF8EE] rounded hover:bg-[#E7DAC3]">2x</button>
        </div>
      </div>

      {/* Transcript */}
      <div className="bg-[#FFF8EE] rounded-lg p-4 space-y-2">
        <div className="text-xs font-semibold text-[#2F4731]">Transcript</div>
        <div className="text-sm text-[#4B3424] space-y-2">
          <p><strong>Speaker 1:</strong> {audioData?.transcript || "This is where the audio transcript would appear..."}</p>
        </div>
      </div>

      {/* Interactive Choices */}
      {audioData?.choices && audioData.choices.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-[#2F4731]">What should they do next?</div>
          <div className="space-y-2">
            {audioData.choices.map((choice, i) => (
              <button
                key={i}
                onClick={() => setCurrentChoice(i)}
                className={clsx(
                  "w-full text-left px-4 py-3 rounded-lg text-sm transition-colors",
                  currentChoice === i
                    ? "bg-[#BD6809] text-white"
                    : "bg-white border border-[#E7DAC3] hover:bg-[#FFF8EE]"
                )}
              >
                {choice}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Comprehension Questions */}
      {audioData?.comprehension_questions && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-[#2F4731]">Comprehension Check</div>
          <div className="bg-white rounded-lg p-3 border border-[#E7DAC3]">
            <p className="text-sm text-[#4B3424] mb-2">{audioData.comprehension_questions[0]}</p>
            <div className="flex gap-2">
              <button className="flex-1 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] text-xs font-semibold transition-colors">
                True
              </button>
              <button className="flex-1 py-2 border border-[#E7DAC3] text-[#2F4731] rounded-lg hover:bg-[#FFF8EE] text-xs font-semibold transition-colors">
                False
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── EMBEDDED_INTERRUPT_INLINE block ───────────────────────────────────────────

function EmbeddedInterruptInlineBlock({ block }: { block: LessonBlockResponse }) {
  const interruptData = (block as ExtendedBlockResponse).embedded_interrupt_data;
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className={clsx("rounded-xl p-4 space-y-3 border-2 border-[#BD6809] bg-[#FFF8EE]", css.embeddedInterrupt)}>
      <div className="flex items-start gap-3">
        <span className="text-2xl">⏸️</span>
        <div className="flex-1 space-y-2">
          <div className="font-bold text-[#2F4731]">{interruptData?.title || 'Pause & Reflect'}</div>
          <p className="text-sm text-[#4B3424]">{interruptData?.prompt || block.content}</p>
          
          {interruptData?.reflection_prompt && (
            <div className="bg-white rounded-lg p-3 border border-[#E7DAC3]">
              <div className="text-xs font-semibold text-[#2F4731] mb-1">Reflection:</div>
              <p className="text-sm text-[#4B3424]">{interruptData.reflection_prompt}</p>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => setDismissed(true)}
              className="flex-1 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#a05a08] font-semibold text-sm transition-colors"
            >
              Continue
            </button>
            <button
              onClick={() => {/* Save reflection functionality */}}
              className="flex-1 py-2 border border-[#E7DAC3] text-[#2F4731] rounded-lg hover:bg-[#FFF8EE] font-semibold text-sm transition-colors"
            >
              Save Reflection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
    </div>
  );
}

// ── Cross-track standards section ─────────────────────────────────────────────

function OASStandardsSection({ standards }: { standards: OASStandard[] }) {
  const primary    = standards.filter((s) => s.source_type !== "cross_track");
  const crossTrack = standards.filter((s) => s.source_type === "cross_track");

  if (!standards.length) return null;

  return (
    <div className={clsx("rounded-xl p-4 space-y-3 mt-2", css.oasStandards)}>
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
  const [extraBlocks, setExtraBlocks] = useState<Array<{ componentType: string; props: Record<string, any> }>>([]);

  const handleScaffoldResponse = (data: { scaffold_component?: string; scaffold_props?: Record<string, any> }) => {
    if (data.scaffold_component && data.scaffold_props) {
      setExtraBlocks((prev) => [
        ...prev,
        { componentType: data.scaffold_component!, props: data.scaffold_props! },
      ]);
    }
  };

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
                  props={{ ...(assemblyData?.props || {}), studentId: studentId ?? "", lessonId: _lessonId, blockId: block.block_id, track: block.track }}
                  initialState={assemblyData?.initial_state || {}}
                  callbacks={assemblyData?.callbacks || []}
                  onStateChange={async (newState) => {
                    if ((newState as any)._scaffold) {
                      handleScaffoldResponse((newState as any)._scaffold);
                      return;
                    }
                    // Send to backend to update BKT/ZPD and check for scaffold triggers
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
                        if (data.should_re_render) {
                          handleScaffoldResponse(data);
                        }
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
                ? <AnimatedSketchnoteRenderer lesson={block.animated_sketchnote_data} />
                : <TextBlock block={block} />;
              break;
            case "BOOK_SUGGESTION":
              blockContent = <BookSuggestionBlock block={block} />;
              break;
            case "DATA_TRACKING":
              blockContent = <DataTrackingBlock block={block} />;
              break;
            case "PROBLEM":
              blockContent = <ProblemBlock block={block} />;
              break;
            case "WRITING":
              blockContent = <WritingBlock block={block} />;
              break;
            case "HIGHLIGHT_ASK":
              blockContent = <HighlightAskBlock block={block} />;
              break;
            case "PEER_TUTOR":
              blockContent = <PeerTutorBlock block={block} />;
              break;
            case "DISCUSSION_FORUM":
              blockContent = <DiscussionForumBlock block={block} />;
              break;
            case "AUDIO_DIALOGUE": {
              const dialogueData = (block as any).audio_dialogue_data;
              blockContent = dialogueData ? (
                <AudioDialogue
                  data={dialogueData}
                  track={(block as any).track}
                />
              ) : (
                <TextBlock block={block} />
              );
              break;
            }
            case "EMBEDDED_INTERRUPT_INLINE": {
              const interruptData = (block as any).inline_interrupt_data;
              blockContent = interruptData ? (
                <DynamicComponent
                  componentType="EmbeddedInterrupt"
                  props={{
                    question: interruptData.question,
                    options: interruptData.options,
                    hint: interruptData.hint,
                    checkpointLabel: interruptData.checkpoint_label ?? "Quick Check",
                    blockId: block.block_id,
                    studentId: studentId ?? "",
                    lessonId: _lessonId,
                  }}
                  initialState={{}}
                  callbacks={["onAnswer", "onComplete"]}
                />
              ) : (
                <TextBlock block={block} />
              );
              break;
            }
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

      {extraBlocks.map((eb, i) => (
        <motion.div
          key={`scaffold-${i}`}
          variants={blockVariants}
          initial="hidden"
          animate="visible"
        >
          <DynamicComponent
            componentType={eb.componentType}
            props={eb.props}
            initialState={{}}
          />
        </motion.div>
      ))}

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
