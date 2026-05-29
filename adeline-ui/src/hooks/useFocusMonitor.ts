"use client";

import { useEffect, useRef, useState } from "react";

export type FocusGapType = "COGNITIVE_OVERLOAD" | "EXTERNAL_DISTRACTION";

const BRAIN_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? "";

/**
 * Tracks how long a student spends on a given block and reports
 * rapid exits / low-engagement signals to the focus API.
 *
 * Fires POST /brain/focus/block-enter on mount.
 * Fires POST /brain/focus/block-exit  on unmount (keepalive: true for navigation-safe delivery).
 *
 * Returns focusGap — non-null when the backend detects overload or distraction.
 */
export function useFocusMonitor(
  studentId: string,
  blockId: string,
  blockType: string,
): { focusGap: FocusGapType | null } {
  const mountTimeRef = useRef<number>(Date.now());
  const interactionCountRef = useRef<number>(0);
  const [focusGap, setFocusGap] = useState<FocusGapType | null>(null);

  useEffect(() => {
    if (!studentId || !blockId) return;

    mountTimeRef.current = Date.now();
    interactionCountRef.current = 0;

    // Signal block entry (fire-and-forget)
    fetch(`${BRAIN_URL}/brain/focus/block-enter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: studentId,
        block_id: blockId,
        block_type: blockType,
        timestamp_ms: Date.now(),
      }),
    }).catch(() => {});

    // Count user interactions inside this block
    const countInteraction = () => { interactionCountRef.current += 1; };
    window.addEventListener("click", countInteraction);
    window.addEventListener("keydown", countInteraction);

    return () => {
      window.removeEventListener("click", countInteraction);
      window.removeEventListener("keydown", countInteraction);

      const duration = Date.now() - mountTimeRef.current;

      // keepalive ensures the request fires even during page navigation
      fetch(`${BRAIN_URL}/brain/focus/block-exit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: studentId,
          block_id: blockId,
          duration_ms: duration,
          interaction_count: interactionCountRef.current,
        }),
        keepalive: true,
      })
        .then((res) => res.json())
        .then((data: { focus_gap?: FocusGapType | null }) => {
          if (data.focus_gap) setFocusGap(data.focus_gap);
        })
        .catch(() => {});
    };
  }, [studentId, blockId, blockType]);

  return { focusGap };
}
