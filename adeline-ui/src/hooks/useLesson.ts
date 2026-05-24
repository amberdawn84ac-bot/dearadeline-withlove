"use client";

import { useState, useCallback } from "react";
import { streamLesson } from "@/lib/brain-client";
import type { LessonResponse, LessonRequest, LessonBlockResponse } from "@/lib/brain-client";

interface UseLessonState {
  blocks: LessonBlockResponse[];
  lesson: LessonResponse | null;
  loading: boolean;
  streamStatus: string | null;
  error: string | null;
}

interface UseLessonReturn extends UseLessonState {
  generate: (request: LessonRequest) => Promise<void>;
  reset: () => void;
}

export function useLesson(): UseLessonReturn {
  const [state, setState] = useState<UseLessonState>({
    blocks: [],
    lesson: null,
    loading: false,
    streamStatus: null,
    error: null,
  });

  const generate = useCallback(async (request: LessonRequest) => {
    setState({ blocks: [], lesson: null, loading: true, streamStatus: "Starting…", error: null });

    try {
      for await (const event of streamLesson(request)) {
        if (event.type === "status") {
          setState((prev) => ({ ...prev, streamStatus: event.message }));
        } else if (event.type === "block") {
          setState((prev) => ({ ...prev, blocks: [...prev.blocks, event.block] }));
        } else if (event.type === "done") {
          setState((prev) => ({
            ...prev,
            loading: false,
            streamStatus: null,
            lesson: {
              lesson_id: event.lesson_id,
              title: event.title,
              track: request.track,
              blocks: prev.blocks,
              has_research_missions: prev.blocks.some(
                (b) => b.block_type === "RESEARCH_MISSION",
              ),
              researcher_activated: false,
              oas_standards: (event.oas_standards as LessonResponse["oas_standards"]) ?? [],
              agent_name: "",
              xapi_statements: [],
              credits_awarded: [],
            },
          }));
        } else if (event.type === "error") {
          setState((prev) => ({
            ...prev,
            loading: false,
            streamStatus: null,
            error: event.message,
          }));
          return;
        }
      }
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        streamStatus: null,
        error: err instanceof Error ? err.message : "Failed to generate lesson.",
      }));
    }
  }, []);

  const reset = useCallback(() => {
    setState({ blocks: [], lesson: null, loading: false, streamStatus: null, error: null });
  }, []);

  return { ...state, generate, reset };
}
