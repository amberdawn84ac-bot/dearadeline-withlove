"use client";

/**
 * useALUStream — Atomic Learning Unit playlist state manager.
 *
 * Sits on top of useGenUIStream and adds:
 *   1. ALU playlist parsing from alu_start / alu_end SSE events
 *   2. Per-ALU temporal friction timer — fires /brain/genui/telemetry with
 *      event: "temporal_friction" when a student stalls mid-block
 *   3. Client-side scaffold injection — zero-latency pivot using the
 *      scaffold config returned in the 202 telemetry response body
 *
 * Usage:
 *   const {
 *     aluPlaylist, currentALUIndex, currentALU,
 *     scaffolds, advanceALU, injectScaffold,
 *     ...genUIStreamProps
 *   } = useALUStream({ studentId, lessonId, track });
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useGenUIStream, type UseGenUIStreamOptions, type UseGenUIStreamReturn } from "@/hooks/useGenUIStream";
import { supabase } from "@/lib/supabase";

// ── ALU Metadata types (mirrors AtomicUnitMetadata in api_models.py) ─────────

export interface ALUScaffoldConfig {
  component: string;
  props: Record<string, unknown>;
}

export interface ALUMetadata {
  unit_slug: string;
  title: string;
  track: string;
  difficulty: "EMERGING" | "DEVELOPING" | "EXPANDING" | "MASTERING";
  order: number;
  estimated_cognitive_load: number;
  target_modalities: string[];
  prerequisite_unit_slugs: string[];
  temporal_friction_threshold_secs: number;
  max_incorrect_before_scaffold: number;
  scaffold: ALUScaffoldConfig;
}

export interface InjectedScaffold {
  id: string;
  aluSlug: string;
  component: string;
  props: Record<string, unknown>;
  reason: "temporal_friction" | "incorrect_answer" | "manual";
  injectedAt: number;
}

export interface UseALUStreamOptions extends UseGenUIStreamOptions {
  track?: string;
}

export interface UseALUStreamReturn extends UseGenUIStreamReturn {
  /** Ordered list of ALU metadata objects received from alu_start events */
  aluPlaylist: ALUMetadata[];
  /** Index of the ALU the student is currently viewing */
  currentALUIndex: number;
  /** The ALU the student is currently viewing, or null if playlist is empty */
  currentALU: ALUMetadata | null;
  /** Scaffolds injected by temporal friction or incorrect answer pivots */
  scaffolds: InjectedScaffold[];
  /** Advance the student to the next ALU in the playlist */
  advanceALU: () => void;
  /** Jump to a specific ALU by index */
  goToALU: (index: number) => void;
  /** Manually inject a scaffold (e.g. from parent component) */
  injectScaffold: (scaffold: Omit<InjectedScaffold, "id" | "injectedAt">) => void;
  /** Process an SSE event from the lesson stream (extends base processEvent) */
  processALUEvent: (event: Record<string, unknown>) => void;
}

const BRAIN_URL = "/brain";

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useALUStream(options: UseALUStreamOptions): UseALUStreamReturn {
  const { studentId, lessonId, track, brainUrl } = options;

  const genUIStream = useGenUIStream({ studentId, lessonId, brainUrl });

  const [aluPlaylist, setALUPlaylist] = useState<ALUMetadata[]>([]);
  const [currentALUIndex, setCurrentALUIndex] = useState(0);
  const [scaffolds, setScaffolds] = useState<InjectedScaffold[]>([]);

  // ── Temporal friction timer ───────────────────────────────────────────────
  // Tracks how long the student has been on the current ALU.
  // Resets whenever currentALUIndex changes or the lesson stream starts.
  const frictionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const aluStartTimeRef = useRef<number>(Date.now());
  const frictionFiredRef = useRef<boolean>(false);

  const clearFrictionTimer = useCallback(() => {
    if (frictionTimerRef.current) {
      clearTimeout(frictionTimerRef.current);
      frictionTimerRef.current = null;
    }
    frictionFiredRef.current = false;
  }, []);

  const fireFrictionTelemetry = useCallback(
    async (alu: ALUMetadata) => {
      if (frictionFiredRef.current) return;
      frictionFiredRef.current = true;

      const durationMs = Date.now() - aluStartTimeRef.current;

      // 1. Fire telemetry — returns scaffold recommendation in 202 body
      try {
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${BRAIN_URL}/genui/telemetry`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            student_id: studentId,
            lesson_id: lessonId ?? "unknown",
            component_type: alu.unit_slug,
            event: "temporal_friction",
            state: {
              threshold_secs: alu.temporal_friction_threshold_secs,
              scaffold_component: alu.scaffold.component,
              scaffold_props: alu.scaffold.props,
            },
            duration_ms: durationMs,
            block_id: alu.unit_slug,
            track: track ?? alu.track,
          }),
        });

        // 2. Extract scaffold recommendation from response body (202 Accepted)
        if (res.ok) {
          const body = await res.json().catch(() => ({}));
          const scaffoldRec = body?.scaffold as { component: string; props: Record<string, unknown> } | undefined;
          const component = scaffoldRec?.component ?? alu.scaffold.component;
          const props = scaffoldRec?.props ?? alu.scaffold.props ?? { mode: "breathe" };

          // 3. Inject scaffold client-side — zero extra round-trip
          setScaffolds((prev) => [
            ...prev,
            {
              id: `friction-${alu.unit_slug}-${Date.now()}`,
              aluSlug: alu.unit_slug,
              component,
              props,
              reason: "temporal_friction",
              injectedAt: Date.now(),
            },
          ]);
        }
      } catch {
        // Temporal friction is non-blocking — silently ignore network errors
        // Still inject the pre-configured scaffold from the ALU metadata
        setScaffolds((prev) => [
          ...prev,
          {
            id: `friction-${alu.unit_slug}-${Date.now()}`,
            aluSlug: alu.unit_slug,
            component: alu.scaffold.component,
            props: alu.scaffold.props ?? { mode: "breathe" },
            reason: "temporal_friction",
            injectedAt: Date.now(),
          },
        ]);
      }
    },
    [studentId, lessonId, track],
  );

  // Restart the friction timer when the current ALU changes
  useEffect(() => {
    const currentALU = aluPlaylist[currentALUIndex];
    if (!currentALU) return;

    clearFrictionTimer();
    aluStartTimeRef.current = Date.now();

    const thresholdMs = currentALU.temporal_friction_threshold_secs * 1000;
    frictionTimerRef.current = setTimeout(() => {
      fireFrictionTelemetry(currentALU);
    }, thresholdMs);

    return () => clearFrictionTimer();
  }, [currentALUIndex, aluPlaylist, clearFrictionTimer, fireFrictionTelemetry]);

  // Clear timer on unmount
  useEffect(() => () => clearFrictionTimer(), [clearFrictionTimer]);

  // ── ALU playlist navigation ───────────────────────────────────────────────

  const advanceALU = useCallback(() => {
    setCurrentALUIndex((prev) => {
      const next = prev + 1;
      return next < aluPlaylist.length ? next : prev;
    });
  }, [aluPlaylist.length]);

  const goToALU = useCallback((index: number) => {
    if (index >= 0 && index < aluPlaylist.length) {
      setCurrentALUIndex(index);
    }
  }, [aluPlaylist.length]);

  const injectScaffold = useCallback(
    (scaffold: Omit<InjectedScaffold, "id" | "injectedAt">) => {
      setScaffolds((prev) => [
        ...prev,
        {
          ...scaffold,
          id: `manual-${scaffold.aluSlug}-${Date.now()}`,
          injectedAt: Date.now(),
        },
      ]);
    },
    [],
  );

  // ── SSE event processor — handles alu_start / alu_end plus passes through ─

  const processALUEvent = useCallback(
    (event: Record<string, unknown>) => {
      const type = event.type as string;

      if (type === "alu_start") {
        const metadata = event.metadata as ALUMetadata;
        if (metadata?.unit_slug) {
          setALUPlaylist((prev) => {
            // Avoid duplicates if the stream is replayed
            if (prev.some((u) => u.unit_slug === metadata.unit_slug)) return prev;
            return [...prev, metadata];
          });
        }
        return;
      }

      if (type === "alu_end") {
        // alu_end is informational — the timer advance happens via advanceALU
        return;
      }

      // Also handle the 'done' event which carries the full alu_playlist as a
      // single authoritative payload — use it to hydrate the playlist at once
      // (covers the case where alu_start events were missed or replayed).
      if (type === "done" && Array.isArray(event.alu_playlist)) {
        const playlist = event.alu_playlist as ALUMetadata[];
        setALUPlaylist(playlist);
      }

      // All other events are forwarded to the base genui stream processor
      // by the caller (AdelineChatPanel processes raw SSE events via processEvent).
    },
    [],
  );

  const currentALU = aluPlaylist[currentALUIndex] ?? null;

  return {
    ...genUIStream,
    aluPlaylist,
    currentALUIndex,
    currentALU,
    scaffolds,
    advanceALU,
    goToALU,
    injectScaffold,
    processALUEvent,
  };
}
