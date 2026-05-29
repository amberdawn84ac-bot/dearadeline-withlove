"use client";

/**
 * StreamingGenUIRenderer — Progressive rendering of GenUI components from SSE.
 *
 * Renders GenUI components as they stream in via the Data Stream Protocol.
 * Components progress through three visual states:
 *
 *   skeleton  → Shows a typed placeholder (pulsing card matching component type)
 *   partial   → Shows the component with available props, loading indicators for missing
 *   complete  → Full interactive component with all props and callbacks
 *
 * Remediation components are injected inline when the backend detects struggle,
 * appearing smoothly without layout shifts via framer-motion animations.
 */

import { motion, AnimatePresence } from "framer-motion";
import type {
  GenUIComponent,
  RemediationEntry,
} from "@/hooks/useGenUIStream";

// ── Component Registry (mirrors GenUIRenderer.tsx) ───────────────────────
// Import the same whitelisted components used by the main renderer.

import { QuizCard } from "@/components/gen-ui/patterns/QuizCard";
import { Flashcard } from "@/components/gen-ui/patterns/Flashcard";
import { MindMap } from "@/components/gen-ui/patterns/MindMap";
import { DragDropTimeline } from "@/components/gen-ui/patterns/DragDropTimeline";
import { MnemonicCard } from "@/components/gen-ui/patterns/MnemonicCard";
import { ExperimentCard } from "@/components/gen-ui/patterns/ExperimentCard";
import { LabGuide } from "@/components/gen-ui/patterns/LabGuide";
import { NarratedSlides } from "@/components/gen-ui/patterns/NarratedSlides";
import { ScaffoldedProblem } from "@/components/gen-ui/patterns/ScaffoldedProblem";
import { HardThingChallenge } from "@/components/gen-ui/patterns/HardThingChallenge";
import { SocraticDebate } from "@/components/gen-ui/patterns/SocraticDebate";
import { ProjectBuilder } from "@/components/gen-ui/patterns/ProjectBuilder";
import { GlowGrow } from "@/components/gen-ui/patterns/GlowGrow";
import { FocusReset } from "@/components/gen-ui/patterns/FocusReset";
import { TaskScaffold } from "@/components/gen-ui/patterns/TaskScaffold";
import { InsightReport } from "@/components/gen-ui/patterns/InsightReport";
import { InteractiveConceptMap } from "@/components/gen-ui/patterns/InteractiveConceptMap";
import { CorrectiveOverlay } from "@/components/gen-ui/patterns/CorrectiveOverlay";
import { AdaptiveQuiz } from "@/components/gen-ui/patterns/AdaptiveQuiz";
import { StealthAssessment } from "@/components/gen-ui/patterns/StealthAssessment";
import { LiveChart } from "@/components/gen-ui/patterns/LiveChart";
import { CodePlayground } from "@/components/gen-ui/patterns/CodePlayground";
import { LessonRatingCard } from "@/components/gen-ui/patterns/LessonRatingCard";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const STREAMING_REGISTRY: Record<string, React.ComponentType<any>> = {
  InteractiveQuiz: QuizCard,
  GlowGrow,
  ScaffoldedProblem,
  SocraticDebate,
  HardThingChallenge,
  ProjectBuilder,
  DragDropTimeline,
  LiveChart,
  InsightReport,
  MnemonicCard,
  Flashcard,
  MindMap,
  FocusReset,
  TaskScaffold,
  ExperimentCard,
  LabGuide,
  CodePlayground,
  InteractiveConceptMap,
  NarratedSlides,
  CorrectiveOverlay,
  AdaptiveQuiz,
  StealthAssessment,
  LessonRatingCard,
};

// ── Skeleton styles per component category ───────────────────────────────

interface SkeletonStyle {
  bg: string;
  border: string;
  accentColor: string;
  icon: string;
  label: string;
}

const SKELETON_STYLES: Record<string, SkeletonStyle> = {
  InteractiveQuiz: { bg: "#EFF6FF", border: "#1D4ED8", accentColor: "#1D4ED820", icon: "📝", label: "Quiz" },
  GlowGrow:        { bg: "#F0FDF4", border: "#166534", accentColor: "#16653420", icon: "🌱", label: "Glow & Grow" },
  Flashcard:       { bg: "#FAF5FF", border: "#7C3AED", accentColor: "#7C3AED20", icon: "🃏", label: "Flashcard" },
  MindMap:         { bg: "#ECFDF5", border: "#059669", accentColor: "#05966920", icon: "🕸️", label: "Mind Map" },
  DragDropTimeline:{ bg: "#F5F3FF", border: "#6D28D9", accentColor: "#6D28D920", icon: "📅", label: "Timeline" },
  MnemonicCard:    { bg: "#FAF5FF", border: "#7C3AED", accentColor: "#7C3AED20", icon: "🧠", label: "Mnemonic" },
  ExperimentCard:  { bg: "#FFF7ED", border: "#BD6809", accentColor: "#BD680920", icon: "⚗️", label: "Experiment" },
  LabGuide:        { bg: "#FFF7ED", border: "#BD6809", accentColor: "#BD680920", icon: "📋", label: "Lab Guide" },
  ScaffoldedProblem:{ bg: "#F5F3FF", border: "#7C3AED", accentColor: "#7C3AED20", icon: "📐", label: "Problem" },
  HardThingChallenge:{ bg: "#FEF2F2", border: "#DC2626", accentColor: "#DC262620", icon: "🏔️", label: "Challenge" },
  SocraticDebate:  { bg: "#FEF2F2", border: "#991B1B", accentColor: "#991B1B20", icon: "💬", label: "Debate" },
  TaskScaffold:    { bg: "#FEFCE8", border: "#CA8A04", accentColor: "#CA8A0420", icon: "📋", label: "Scaffold" },
  InteractiveConceptMap: { bg: "#ECFDF5", border: "#059669", accentColor: "#05966920", icon: "🗺️", label: "Concept Map" },
  CorrectiveOverlay: { bg: "#FEF2F2", border: "#DC2626", accentColor: "#DC262620", icon: "💡", label: "Correction" },
};

const DEFAULT_SKELETON: SkeletonStyle = {
  bg: "#FFFEF7", border: "#2F4731", accentColor: "#2F473120", icon: "✨", label: "Component",
};

// ── Skeleton component ───────────────────────────────────────────────────

function GenUISkeleton({ component }: { component: GenUIComponent }) {
  const style = SKELETON_STYLES[component.componentType] ?? DEFAULT_SKELETON;
  const hint = (component.hints?.title as string) ?? "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="rounded-2xl p-5 space-y-3 animate-pulse"
      style={{ background: style.bg, border: `2px solid ${style.border}30` }}
    >
      <div className="flex items-center gap-2">
        <span role="img" aria-hidden className="text-lg">{style.icon}</span>
        <span
          className="text-[10px] font-bold uppercase tracking-wider"
          style={{ color: style.border }}
        >
          {style.label}
        </span>
        <div className="ml-auto flex gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background: style.border,
                opacity: 0.4,
                animation: `pulse 1s ease-in-out ${i * 0.15}s infinite`,
              }}
            />
          ))}
        </div>
      </div>

      {hint && (
        <div className="h-4 rounded" style={{ background: style.accentColor, width: "60%" }} />
      )}

      <div className="space-y-2">
        <div className="h-3 rounded-full w-full" style={{ background: style.accentColor }} />
        <div className="h-3 rounded-full w-5/6" style={{ background: style.accentColor }} />
        <div className="h-3 rounded-full w-4/6" style={{ background: style.accentColor }} />
      </div>

      {/* Interactive element placeholders */}
      <div className="space-y-2 pt-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-10 rounded-xl"
            style={{ background: style.accentColor, border: `1.5px solid ${style.accentColor}` }}
          />
        ))}
      </div>

      <div className="text-xs font-mono pt-1" style={{ color: `${style.border}80` }}>
        Preparing {style.label.toLowerCase()}…
      </div>
    </motion.div>
  );
}

// ── Remediation badge ────────────────────────────────────────────────────

function RemediationBadge({ reason }: { reason: string }) {
  const label =
    reason === "onWrongAnswer" ? "Let\u2019s try a different approach" :
    reason === "onStruggle"    ? "Here\u2019s some help" :
                                 "Adeline suggests";
  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg mb-2"
      style={{ background: "#FEF3C7", border: "1px solid #F59E0B40" }}
    >
      <span className="text-sm">🌿</span>
      <span className="text-xs font-semibold text-[#92400E]">{label}</span>
    </div>
  );
}

// ── Main renderer ────────────────────────────────────────────────────────

interface StreamingGenUIRendererProps {
  components: Map<string, GenUIComponent>;
  componentOrder: string[];
  remediations: RemediationEntry[];
  onComponentEvent?: (params: {
    componentId: string;
    componentType: string;
    event: string;
    state: Record<string, unknown>;
  }) => void;
}

export function StreamingGenUIRenderer({
  components,
  componentOrder,
  remediations,
  onComponentEvent,
}: StreamingGenUIRendererProps) {
  // Build remediation lookup: sourceComponentId → list of remediation entries
  const remediationMap = new Map<string, RemediationEntry[]>();
  for (const r of remediations) {
    const list = remediationMap.get(r.sourceComponentId) ?? [];
    list.push(r);
    remediationMap.set(r.sourceComponentId, list);
  }

  return (
    <motion.div
      className="space-y-4"
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: { staggerChildren: 0.12, delayChildren: 0.05 },
        },
      }}
    >
      <AnimatePresence mode="popLayout">
        {componentOrder.map((id) => {
          const component = components.get(id);
          if (!component) return null;

          const isRemedial = id.startsWith("remedial-");
          const componentRemediations = remediationMap.get(id) ?? [];

          return (
            <motion.div
              key={id}
              layout
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 260, damping: 25 }}
            >
              {/* Remediation badge for injected components */}
              {isRemedial && (
                <RemediationBadge
                  reason={
                    remediations.find((r) => r.remedialId === id)?.reason ??
                    "remediation"
                  }
                />
              )}

              {/* Render skeleton or full component */}
              {component.state === "skeleton" ? (
                <GenUISkeleton component={component} />
              ) : (
                <StreamingComponent
                  component={component}
                  onEvent={onComponentEvent}
                />
              )}

              {/* Render any remediation components injected for this component */}
              {componentRemediations.map((r) => {
                const remedialComp = components.get(r.remedialId);
                if (!remedialComp || remedialComp.state === "skeleton")
                  return null;
                return (
                  <motion.div
                    key={r.remedialId}
                    initial={{ opacity: 0, y: 12, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    className="mt-3"
                  >
                    <RemediationBadge reason={r.reason} />
                    <StreamingComponent
                      component={remedialComp}
                      onEvent={onComponentEvent}
                    />
                  </motion.div>
                );
              })}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Individual streaming component ───────────────────────────────────────

function StreamingComponent({
  component,
  onEvent,
}: {
  component: GenUIComponent;
  onEvent?: (params: {
    componentId: string;
    componentType: string;
    event: string;
    state: Record<string, unknown>;
  }) => void;
}) {
  const Component = STREAMING_REGISTRY[component.componentType];

  if (!Component) {
    return (
      <div
        className="rounded-xl p-4 text-sm text-[#991B1B]"
        style={{ background: "#FEF2F2", border: "1.5px solid #991B1B30" }}
      >
        Unknown component: {component.componentType}
      </div>
    );
  }

  const handleStateChange = (newState: Record<string, unknown>) => {
    onEvent?.({
      componentId: component.componentId,
      componentType: component.componentType,
      event: "onStateChange",
      state: newState,
    });
  };

  return (
    <Component
      {...(component.props ?? {})}
      state={component.initialState}
      onStateChange={handleStateChange}
      callbacks={component.callbacks}
    />
  );
}
