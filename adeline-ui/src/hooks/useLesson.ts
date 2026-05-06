"use client";

import { useState, useCallback } from "react";
import { generateLesson, pollLessonResult } from "@/lib/brain-client";
import type { LessonResponse, LessonRequest } from "@/lib/brain-client";

interface UseLessonState {
  lesson: LessonResponse | null;
  loading: boolean;
  generatingStatus: string | null;
  error: string | null;
}

interface UseLessonReturn extends UseLessonState {
  generate: (request: LessonRequest) => Promise<void>;
  reset: () => void;
}

export function useLesson(): UseLessonReturn {
  const [state, setState] = useState<UseLessonState>({
    lesson: null,
    loading: false,
    generatingStatus: null,
    error: null,
  });

  const generate = useCallback(async (request: LessonRequest) => {
    setState({ lesson: null, loading: true, generatingStatus: "queued", error: null });
    try {
      const job = await generateLesson(request);
      const lesson = await pollLessonResult(job.job_id, {
        intervalMs: 2000,
        timeoutMs: 90000,
        onProgress: (status) =>
          setState((prev) => ({ ...prev, generatingStatus: status })),
      });
      setState({ lesson, loading: false, generatingStatus: null, error: null });
    } catch (err) {
      setState({
        lesson: null,
        loading: false,
        generatingStatus: null,
        error: err instanceof Error ? err.message : "Failed to generate lesson.",
      });
    }
  }, []);

  const reset = useCallback(() => {
    setState({ lesson: null, loading: false, generatingStatus: null, error: null });
  }, []);

  return { ...state, generate, reset };
}
