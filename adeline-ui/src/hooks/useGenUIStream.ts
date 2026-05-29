"use client";

/**
 * useGenUIStream — React hook for progressive GenUI rendering via SSE.
 *
 * Manages a map of GenUI component states as they stream in from the
 * Data Stream Protocol.  Components progress through:
 *
 *   skeleton → partial → complete
 *
 * The hook also handles:
 *   - Bidirectional remediation: when a student struggles, it POSTs to
 *     /genui/remediate and injects the remedial component into the stream.
 *   - Tool call interception: student interactions are piped back to the
 *     orchestrator via onToolCall.
 *   - Delta patching: partial props are merged into existing component state.
 *
 * Usage:
 *   const { components, remediations, isStreaming, streamLesson, triggerRemediation }
 *     = useGenUIStream({ studentId, lessonId });
 */

import { useState, useCallback, useRef } from "react";
import type { LessonBlockResponse } from "@/lib/brain-client";
import {
  parseDataStream,
  type DataStreamEvent,
  type GenUISkeletonAnnotation,
  type GenUIPropsAnnotation,
  type GenUICompleteAnnotation,
  type RemediationAnnotation,
} from "@/lib/stream-protocol";

// ── Types ──────────────────────────────────────────────────────────────────

export type GenUIComponentState = "skeleton" | "partial" | "complete";

export interface GenUIComponent {
  componentId: string;
  componentType: string;
  state: GenUIComponentState;
  props: Record<string, unknown> | null;
  callbacks: string[];
  initialState: Record<string, unknown>;
  hints: Record<string, unknown>;
  lessonId?: string;
  track?: string;
}

export interface RemediationEntry {
  remedialId: string;
  sourceComponentId: string;
  componentType: string;
  props: Record<string, unknown>;
  reason: string;
  timestamp: number;
}

export interface UseGenUIStreamOptions {
  studentId: string;
  lessonId?: string;
  brainUrl?: string;
}

export interface UseGenUIStreamReturn {
  /** Map of componentId → GenUI component state (skeleton/partial/complete) */
  components: Map<string, GenUIComponent>;
  /** Ordered list of component IDs for rendering */
  componentOrder: string[];
  /** Remediation components injected by the backend */
  remediations: RemediationEntry[];
  /** Lesson blocks received via the stream */
  blocks: LessonBlockResponse[];
  /** Status messages from the stream */
  statusMessage: string;
  /** Whether the stream is currently active */
  isStreaming: boolean;
  /** Lesson metadata from the done event */
  lessonMeta: { lessonId: string; title: string } | null;
  /** Trigger remediation for a struggling student */
  triggerRemediation: (params: {
    sourceComponentId: string;
    componentType: string;
    event: string;
    studentState: Record<string, unknown>;
    track?: string;
  }) => Promise<void>;
  /** Process Data Stream Protocol events from any source */
  processEvent: (event: DataStreamEvent) => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────

export function useGenUIStream(
  options: UseGenUIStreamOptions,
): UseGenUIStreamReturn {
  const { studentId, lessonId, brainUrl = "/brain" } = options;

  const [components, setComponents] = useState<Map<string, GenUIComponent>>(
    () => new Map(),
  );
  const [componentOrder, setComponentOrder] = useState<string[]>([]);
  const [remediations, setRemediations] = useState<RemediationEntry[]>([]);
  const [blocks, setBlocks] = useState<LessonBlockResponse[]>([]);
  const [statusMessage, setStatusMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [lessonMeta, setLessonMeta] = useState<{
    lessonId: string;
    title: string;
  } | null>(null);

  const componentsRef = useRef(components);
  componentsRef.current = components;

  // ── Annotation processors ──────────────────────────────────────────────

  const handleSkeleton = useCallback(
    (annotation: GenUISkeletonAnnotation) => {
      const { componentId, componentType, hints } = annotation;

      setComponents((prev) => {
        const next = new Map(prev);
        next.set(componentId, {
          componentId,
          componentType,
          state: "skeleton",
          props: null,
          callbacks: [],
          initialState: {},
          hints: hints ?? {},
          lessonId: annotation.lessonId,
          track: annotation.track,
        });
        return next;
      });

      setComponentOrder((prev) =>
        prev.includes(componentId) ? prev : [...prev, componentId],
      );
    },
    [],
  );

  const handleProps = useCallback(
    (annotation: GenUIPropsAnnotation) => {
      const { componentId, props, state } = annotation;

      setComponents((prev) => {
        const next = new Map(prev);
        const existing = next.get(componentId);
        if (!existing) return prev;

        const mergedProps =
          state === "partial"
            ? { ...(existing.props ?? {}), ...props }
            : props;

        next.set(componentId, {
          ...existing,
          props: mergedProps,
          state: state === "complete" ? "complete" : "partial",
        });
        return next;
      });
    },
    [],
  );

  const handleComplete = useCallback(
    (annotation: GenUICompleteAnnotation) => {
      const {
        componentId,
        componentType,
        props,
        callbacks,
        initialState,
      } = annotation;

      setComponents((prev) => {
        const next = new Map(prev);
        next.set(componentId, {
          componentId,
          componentType,
          state: "complete",
          props,
          callbacks: callbacks ?? [],
          initialState: initialState ?? {},
          hints: {},
          lessonId: annotation.lessonId,
          track: annotation.track,
        });
        return next;
      });

      setComponentOrder((prev) =>
        prev.includes(componentId) ? prev : [...prev, componentId],
      );
    },
    [],
  );

  const handleRemediation = useCallback(
    (annotation: RemediationAnnotation) => {
      setRemediations((prev) => [
        ...prev,
        {
          remedialId: annotation.remedialId,
          sourceComponentId: annotation.sourceComponentId,
          componentType: annotation.componentType,
          props: annotation.props,
          reason: annotation.reason,
          timestamp: Date.now(),
        },
      ]);

      // Also add the remediation component to the component map
      setComponents((prev) => {
        const next = new Map(prev);
        next.set(annotation.remedialId, {
          componentId: annotation.remedialId,
          componentType: annotation.componentType,
          state: "complete",
          props: annotation.props,
          callbacks: ["onAnswer", "onComplete"],
          initialState: {},
          hints: {},
        });
        return next;
      });

      setComponentOrder((prev) =>
        prev.includes(annotation.remedialId)
          ? prev
          : [...prev, annotation.remedialId],
      );
    },
    [],
  );

  // ── Process a single Data Stream Protocol event ────────────────────────

  const processEvent = useCallback(
    (event: DataStreamEvent) => {
      if (event.prefix === "2") {
        for (const annotation of event.annotations) {
          switch (annotation.type) {
            case "genui_skeleton":
              handleSkeleton(annotation as GenUISkeletonAnnotation);
              break;
            case "genui_props":
              handleProps(annotation as GenUIPropsAnnotation);
              break;
            case "genui_complete":
              handleComplete(annotation as GenUICompleteAnnotation);
              break;
            case "remediation":
              handleRemediation(annotation as RemediationAnnotation);
              break;
            case "status":
              setStatusMessage(
                (annotation as { type: "status"; message: string }).message,
              );
              break;
          }
        }
      } else if (event.prefix === "d") {
        setIsStreaming(false);
      }
    },
    [handleSkeleton, handleProps, handleComplete, handleRemediation],
  );

  // ── Bidirectional remediation trigger ───────────────────────────────────

  const triggerRemediation = useCallback(
    async (params: {
      sourceComponentId: string;
      componentType: string;
      event: string;
      studentState: Record<string, unknown>;
      track?: string;
    }) => {
      try {
        const resp = await fetch(`${brainUrl}/genui/remediate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            student_id: studentId,
            lesson_id: lessonId ?? "",
            source_component_id: params.sourceComponentId,
            component_type: params.componentType,
            event: params.event,
            student_state: params.studentState,
            track: params.track ?? null,
          }),
        });

        if (!resp.ok || !resp.body) return;

        // Parse the remediation response stream
        for await (const event of parseDataStream(resp.body)) {
          processEvent(event);
        }
      } catch (err) {
        console.warn("[useGenUIStream] Remediation request failed:", err);
      }
    },
    [studentId, lessonId, brainUrl, processEvent],
  );

  return {
    components,
    componentOrder,
    remediations,
    blocks,
    statusMessage,
    isStreaming,
    lessonMeta,
    triggerRemediation,
    processEvent,
  };
}
