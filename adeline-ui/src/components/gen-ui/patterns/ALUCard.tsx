"use client";

/**
 * ALUCard — Atomic Learning Unit card with multimodal tab switcher.
 *
 * A single ALU wraps all the multimodal views (text, slides, audio dialogue,
 * mind map, quiz, etc.) for one concept into a tabbed card. The student
 * picks their preferred representation; completing any tab marks the ALU
 * as seen and fires an onComplete callback.
 *
 * When a temporal friction scaffold has been injected (via useALUStream),
 * the card renders the scaffold overlay instead of the normal tabs.
 *
 * Props:
 *   aluMeta      — AtomicUnitMetadata from the alu_start SSE event
 *   blocks       — The lesson blocks belonging to this ALU
 *   scaffold     — Optional injected scaffold (temporal friction pivot)
 *   track        — Learning track for theming
 *   isActive     — Whether this is the currently active ALU in the playlist
 *   onComplete   — Called when the student marks this ALU done
 *   onAdvance    — Called to move to the next ALU in the playlist
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Presentation,
  Headphones,
  Brain,
  ListOrdered,
  HelpCircle,
  CheckCircle2,
  ChevronRight,
  AlertTriangle,
  Layers,
} from "lucide-react";
import { FocusReset } from "@/components/gen-ui/patterns/FocusReset";
import { TaskScaffold } from "@/components/gen-ui/patterns/TaskScaffold";
import type { InjectedScaffold, ALUMetadata } from "@/hooks/useALUStream";

// ── Block type → tab metadata mapping ────────────────────────────────────────

interface TabConfig {
  icon: React.ReactNode;
  label: string;
  modality: string;
}

const BLOCK_TAB_CONFIG: Record<string, TabConfig> = {
  NARRATIVE:          { icon: <BookOpen size={13} />,      label: "Read",      modality: "reading" },
  TEXT:               { icon: <BookOpen size={13} />,      label: "Read",      modality: "reading" },
  PRIMARY_SOURCE:     { icon: <BookOpen size={13} />,      label: "Source",    modality: "reading" },
  RESEARCH_MISSION:   { icon: <BookOpen size={13} />,      label: "Research",  modality: "reading" },
  NARRATED_SLIDE:     { icon: <Presentation size={13} />,  label: "Slides",    modality: "visual" },
  AUDIO_DIALOGUE:     { icon: <Headphones size={13} />,    label: "Listen",    modality: "auditory" },
  MIND_MAP:           { icon: <Brain size={13} />,         label: "Map",       modality: "visual" },
  TIMELINE:           { icon: <ListOrdered size={13} />,   label: "Timeline",  modality: "visual" },
  MNEMONIC:           { icon: <Brain size={13} />,         label: "Memory",    modality: "visual" },
  QUIZ:               { icon: <HelpCircle size={13} />,    label: "Quiz",      modality: "assessment" },
  FLASHCARD:          { icon: <Layers size={13} />,        label: "Cards",     modality: "reading" },
  EXPERIMENT:         { icon: <Layers size={13} />,        label: "Lab",       modality: "kinesthetic" },
  LAB_MISSION:        { icon: <Layers size={13} />,        label: "Lab",       modality: "kinesthetic" },
  GENUI_ASSEMBLY:     { icon: <Layers size={13} />,        label: "Activity",  modality: "kinesthetic" },
  SIMULATION:         { icon: <Layers size={13} />,        label: "Simulate",  modality: "kinesthetic" },
  REAL_WORLD_APP:     { icon: <Layers size={13} />,        label: "Apply",     modality: "kinesthetic" },
  BOOK_SUGGESTION:    { icon: <BookOpen size={13} />,      label: "Books",     modality: "reading" },
  VIDEO:              { icon: <Presentation size={13} />,  label: "Video",     modality: "visual" },
};

function getTabConfig(blockType: string): TabConfig {
  return (
    BLOCK_TAB_CONFIG[blockType] ?? {
      icon: <BookOpen size={13} />,
      label: "Learn",
      modality: "reading",
    }
  );
}

// ── Track accent colors ───────────────────────────────────────────────────────

const TRACK_ACCENT: Record<string, string> = {
  TRUTH_HISTORY:        "#1E3A5F",
  JUSTICE_CHANGEMAKING: "#7C2D12",
  GOVERNMENT_ECONOMICS: "#78350F",
  CREATION_SCIENCE:     "#14532D",
  HOMESTEADING:         "#365314",
  DISCIPLESHIP:         "#581C87",
  HEALTH_NATUROPATHY:   "#164E63",
  ENGLISH_LITERATURE:   "#7C3AED",
  APPLIED_MATHEMATICS:  "#1D4ED8",
  CREATIVE_ECONOMY:     "#9D174D",
};

// ── Difficulty badge ──────────────────────────────────────────────────────────

const DIFFICULTY_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  EMERGING:   { bg: "#F0FDF4", text: "#166534", label: "Emerging" },
  DEVELOPING: { bg: "#EFF6FF", text: "#1D4ED8", label: "Developing" },
  EXPANDING:  { bg: "#FFF7ED", text: "#C2410C", label: "Expanding" },
  MASTERING:  { bg: "#FDF4FF", text: "#7E22CE", label: "Mastering" },
};

// ── Scaffold component map ────────────────────────────────────────────────────
// Components that can be rendered by scaffold.component

type ScaffoldComponentName = "FocusReset" | "TaskScaffold";

const SCAFFOLD_COMPONENT_MAP: Record<
  ScaffoldComponentName,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  React.ComponentType<any>
> = {
  FocusReset,
  TaskScaffold,
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ALUCardBlock {
  block_id: string;
  block_type: string;
  title?: string;
  content?: string;
  /** Opaque structured data passed directly to the block's renderer */
  data?: Record<string, unknown>;
  /** Already-rendered React node (from GenUIRenderer) */
  renderedNode?: React.ReactNode;
}

export interface ALUCardProps {
  aluMeta: ALUMetadata;
  blocks: ALUCardBlock[];
  scaffold?: InjectedScaffold | null;
  track?: string;
  isActive?: boolean;
  onComplete?: (unitSlug: string) => void;
  onAdvance?: () => void;
  onDismissScaffold?: () => void;
}

// ── ALUCard ───────────────────────────────────────────────────────────────────

export function ALUCard({
  aluMeta,
  blocks,
  scaffold,
  track,
  isActive = false,
  onComplete,
  onAdvance,
  onDismissScaffold,
}: ALUCardProps) {
  const accent = TRACK_ACCENT[track ?? aluMeta.track ?? ""] ?? "#1D4ED8";
  const diffBadge =
    DIFFICULTY_BADGE[aluMeta.difficulty ?? "DEVELOPING"] ??
    DIFFICULTY_BADGE.DEVELOPING;

  // Active tab index — default to first block
  const [activeTab, setActiveTab] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [seenTabs, setSeenTabs] = useState<Set<number>>(new Set([0]));
  const [showScaffoldOverlay, setShowScaffoldOverlay] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Show scaffold overlay whenever a new scaffold is injected
  useEffect(() => {
    if (scaffold) {
      setShowScaffoldOverlay(true);
    }
  }, [scaffold]);

  // Mark tab as seen when the student switches to it
  const handleTabChange = useCallback((idx: number) => {
    setActiveTab(idx);
    setSeenTabs((prev) => new Set([...prev, idx]));
  }, []);

  // Mark ALU complete when student explicitly clicks Complete
  const handleComplete = useCallback(() => {
    setCompleted(true);
    onComplete?.(aluMeta.unit_slug);
  }, [aluMeta.unit_slug, onComplete]);

  const handleDismissScaffold = useCallback(() => {
    setShowScaffoldOverlay(false);
    onDismissScaffold?.();
  }, [onDismissScaffold]);

  const handleAdvance = useCallback(() => {
    if (!completed) handleComplete();
    onAdvance?.();
  }, [completed, handleComplete, onAdvance]);

  // Resolve scaffold component
  const ScaffoldComponent = scaffold
    ? (SCAFFOLD_COMPONENT_MAP[scaffold.component as ScaffoldComponentName] ?? FocusReset)
    : null;

  const activeBlock = blocks[activeTab];

  return (
    <div
      ref={cardRef}
      className="rounded-2xl overflow-hidden transition-shadow"
      style={{
        border: `1.5px solid ${accent}${isActive ? "40" : "20"}`,
        boxShadow: isActive ? `0 0 0 2px ${accent}30` : undefined,
        background: "#FAFAFA",
      }}
    >
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: accent, color: "#fff" }}
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Difficulty badge */}
          <span
            className="flex-shrink-0 text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
            style={{ background: diffBadge.bg, color: diffBadge.text }}
          >
            {diffBadge.label}
          </span>
          <span className="text-sm font-bold truncate">{aluMeta.title}</span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Cognitive load indicator */}
          {aluMeta.estimated_cognitive_load != null && (
            <div
              className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: "rgba(255,255,255,0.18)", color: "#fff" }}
              title={`Estimated cognitive load: ${aluMeta.estimated_cognitive_load.toFixed(1)}/10`}
            >
              <Brain size={10} />
              {aluMeta.estimated_cognitive_load.toFixed(1)}
            </div>
          )}

          {/* Completed checkmark */}
          {completed && (
            <CheckCircle2 size={16} className="text-emerald-300" />
          )}
        </div>
      </div>

      {/* ── Prerequisite chips ────────────────────────────────────────────── */}
      {aluMeta.prerequisite_unit_slugs.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5 px-4 py-2"
          style={{ background: `${accent}08`, borderBottom: `1px solid ${accent}15` }}
        >
          <span className="text-[10px] font-semibold text-[#9CA3AF] mr-1">Needs:</span>
          {aluMeta.prerequisite_unit_slugs.map((slug) => (
            <span
              key={slug}
              className="text-[10px] px-2 py-0.5 rounded-full font-medium"
              style={{ background: `${accent}15`, color: accent }}
            >
              {slug.replace(/-/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* ── Modality tabs (only shown when > 1 block) ─────────────────────── */}
      {blocks.length > 1 && (
        <div
          className="flex gap-0 overflow-x-auto"
          style={{ borderBottom: `1px solid ${accent}15` }}
        >
          {blocks.map((block, idx) => {
            const tab = getTabConfig(block.block_type);
            const isActiveTab = idx === activeTab;
            const isSeen = seenTabs.has(idx);
            return (
              <button
                key={block.block_id}
                onClick={() => handleTabChange(idx)}
                className="flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-semibold whitespace-nowrap transition-colors relative"
                style={{
                  color: isActiveTab ? accent : "#9CA3AF",
                  background: isActiveTab ? `${accent}0D` : "transparent",
                  borderBottom: isActiveTab ? `2px solid ${accent}` : "2px solid transparent",
                }}
              >
                {tab.icon}
                {tab.label}
                {/* Seen dot */}
                {isSeen && !isActiveTab && (
                  <span
                    className="absolute top-1.5 right-1.5 w-1 h-1 rounded-full"
                    style={{ background: "#10B981" }}
                  />
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* ── Block content pane ────────────────────────────────────────────── */}
      <div className="relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.18 }}
            className="p-4"
          >
            {activeBlock ? (
              activeBlock.renderedNode ? (
                // Pre-rendered node from GenUIRenderer
                <>{activeBlock.renderedNode}</>
              ) : (
                // Fallback: render raw content as text
                <div className="space-y-2">
                  {activeBlock.title && (
                    <h3
                      className="text-sm font-bold"
                      style={{ color: accent }}
                    >
                      {activeBlock.title}
                    </h3>
                  )}
                  <p className="text-sm leading-relaxed text-[#374151]">
                    {activeBlock.content ?? ""}
                  </p>
                </div>
              )
            ) : (
              <p className="text-sm text-[#9CA3AF]">Loading…</p>
            )}
          </motion.div>
        </AnimatePresence>

        {/* ── Scaffold overlay ──────────────────────────────────────────── */}
        <AnimatePresence>
          {showScaffoldOverlay && scaffold && ScaffoldComponent && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="absolute inset-0 z-10 flex flex-col justify-end"
              style={{ background: "rgba(250,250,250,0.96)" }}
            >
              <div className="p-4 space-y-3">
                {/* Friction banner */}
                <div
                  className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold"
                  style={{ background: "#FEF9C3", border: "1px solid #CA8A04", color: "#78350F" }}
                >
                  <AlertTriangle size={13} />
                  Looks like you might need a moment — let's reset.
                </div>

                {/* Scaffold component */}
                <ScaffoldComponent
                  {...(scaffold.props as Record<string, unknown>)}
                  onComplete={handleDismissScaffold}
                />

                {/* Dismiss link */}
                <button
                  onClick={handleDismissScaffold}
                  className="text-xs text-[#9CA3AF] underline hover:text-[#374151]"
                >
                  Skip and continue
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Footer: progress + completion ─────────────────────────────────── */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ borderTop: `1px solid ${accent}15` }}
      >
        {/* Tab progress dots */}
        <div className="flex gap-1">
          {blocks.map((_, idx) => (
            <button
              key={idx}
              onClick={() => handleTabChange(idx)}
              className="w-2 h-2 rounded-full transition-colors"
              style={{
                background:
                  idx === activeTab
                    ? accent
                    : seenTabs.has(idx)
                    ? `${accent}60`
                    : "#E5E7EB",
              }}
              aria-label={`Go to block ${idx + 1}`}
            />
          ))}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {!completed ? (
            <button
              onClick={handleComplete}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: accent }}
            >
              <CheckCircle2 size={12} />
              Mark Done
            </button>
          ) : (
            <button
              onClick={handleAdvance}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: "#10B981" }}
            >
              Next Unit
              <ChevronRight size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ALUCard;
