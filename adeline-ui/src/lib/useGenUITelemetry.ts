"use client";

import { useCallback, useRef } from "react";
import { supabase } from "@/lib/supabase";

/**
 * Fire-and-forget telemetry hook for GenUI component interactions.
 * Sends events to /brain/genui/telemetry without blocking the UI.
 *
 * Usage:
 *   const { reportSuccess, reportStruggle } = useGenUITelemetry({ studentId, lessonId });
 *   // On successful completion:
 *   reportSuccess("SocraticDebate", { responses: [...], timeMs: 12000 });
 *   // On struggle detection:
 *   reportStruggle("QuizCard", { wrongAttempts: 3, hintsUsed: 2 });
 */

const BRAIN_URL = "/brain";

export interface TelemetryEvent {
  student_id: string;
  lesson_id: string;
  component_type: string;
  event: "completion" | "struggle" | "interaction" | "hint" | "timeout";
  state: Record<string, unknown>;
  duration_ms?: number;
  block_id?: string;
  track?: string;
}

interface UseGenUITelemetryOptions {
  studentId: string;
  lessonId: string;
  track?: string;
}

export function useGenUITelemetry({ studentId, lessonId, track }: UseGenUITelemetryOptions) {
  const mountedAt = useRef(Date.now());

  const send = useCallback(
    async (event: Omit<TelemetryEvent, "student_id" | "lesson_id">) => {
      try {
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        // Fire-and-forget — don't await response
        fetch(`${BRAIN_URL}/genui/telemetry`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            student_id: studentId,
            lesson_id: lessonId,
            track,
            ...event,
          }),
        }).catch(() => {
          // Silently ignore telemetry failures — never interrupt flow state
        });
      } catch {
        // Silently ignore
      }
    },
    [studentId, lessonId, track]
  );

  const reportSuccess = useCallback(
    (componentType: string, state: Record<string, unknown> = {}, blockId?: string) => {
      send({
        component_type: componentType,
        event: "completion",
        state,
        duration_ms: Date.now() - mountedAt.current,
        block_id: blockId,
      });
    },
    [send]
  );

  const reportStruggle = useCallback(
    (componentType: string, state: Record<string, unknown> = {}, blockId?: string) => {
      send({
        component_type: componentType,
        event: "struggle",
        state,
        duration_ms: Date.now() - mountedAt.current,
        block_id: blockId,
      });
    },
    [send]
  );

  const reportInteraction = useCallback(
    (componentType: string, state: Record<string, unknown> = {}, blockId?: string) => {
      send({
        component_type: componentType,
        event: "interaction",
        state,
        duration_ms: Date.now() - mountedAt.current,
        block_id: blockId,
      });
    },
    [send]
  );

  return { reportSuccess, reportStruggle, reportInteraction, send };
}
