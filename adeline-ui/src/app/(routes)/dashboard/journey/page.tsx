"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { ArrowLeft, AlertCircle } from "lucide-react";
import { generateLesson } from "@/lib/brain-client";
import type { LessonResponse, Track } from "@/lib/brain-client";
import LessonRenderer from "@/components/lessons/LessonRenderer";
import { AdelineChatPanel } from "@/components/AdelineChatPanel";
import { StudentStatusBar } from "@/components/StudentStatusBar";
import { useStudent } from "@/lib/useStudent";
import { AgentThinkingState } from "@/components/gen-ui/AgentThinkingState";
import { TextSelectionMenu } from "@/components/gen-ui/TextSelectionMenu";

// ── Lesson suggestion cards ───────────────────────────────────────────────────

interface LessonSuggestion {
  id: string;
  title: string;
  /** Richer query sent to the brain — scores higher against corpus embeddings */
  topic: string;
  track: Track;
  description: string;
  emoji: string;
}

const LESSON_SUGGESTIONS: LessonSuggestion[] = [
  {
    id: "1",
    title: "Frederick Douglass Learning to Read",
    topic: "How did Frederick Douglass learn to read through the help of white boys in the street, despite laws forbidding slaves from learning to read?",
    track: "TRUTH_HISTORY",
    description: "Primary sources from Douglass's own narrative",
    emoji: "📜",
  },
  {
    id: "2",
    title: "The Constitutional Convention of 1787",
    topic: "How did the Founders debate the structure of the republic at the Constitutional Convention of 1787, including the Great Compromise and the Bill of Rights?",
    track: "GOVERNMENT_ECONOMICS",
    description: "Founders debate the structure of the republic",
    emoji: "🏛️",
  },
  {
    id: "3",
    title: "Medicinal Herbs of the American Frontier",
    topic: "What medicinal herbs did American frontier homesteaders and Indigenous healers use for traditional plant medicine, and what is their historical use?",
    track: "HEALTH_NATUROPATHY",
    description: "Traditional plant medicine and its historical use",
    emoji: "🌿",
  },
  {
    id: "4",
    title: "Harriet Tubman and the Underground Railroad",
    topic: "How did Harriet Tubman escape slavery and lead freedom-seekers north on the Underground Railroad, and what courage did she show returning south again and again?",
    track: "JUSTICE_CHANGEMAKING",
    description: "First-person accounts of courage and liberation",
    emoji: "⭐",
  },
];

// ── JourneyPage ───────────────────────────────────────────────────────────────

export default function JourneyPage() {
  const { student } = useStudent();
  const STUDENT_ID = student?.id ?? '';
  const GRADE_LEVEL_VAL = student?.gradeLevel ?? '8';
  const [activeLesson, setActiveLesson] = useState<LessonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedText, setHighlightedText] = useState<string | null>(null);
  const lessonContainerRef = useRef<HTMLDivElement>(null);

  // Listen for highlight-ask events dispatched by GenUIRenderer's TextSelectionMenu
  useEffect(() => {
    const handler = (e: Event) => {
      const { text } = (e as CustomEvent).detail ?? {};
      if (text) setHighlightedText(text);
    };
    window.addEventListener("adeline:highlight-ask", handler);
    return () => window.removeEventListener("adeline:highlight-ask", handler);
  }, []);

  const handleLessonRequest = useCallback(async (topic: string, track: Track = "TRUTH_HISTORY") => {
    setIsLoading(true);
    setError(null);
    try {
      const lesson = await generateLesson({
        student_id: STUDENT_ID,
        track,
        topic,
        is_homestead: false,
        grade_level: GRADE_LEVEL_VAL,
      });
      setActiveLesson(lesson);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate lesson");
    } finally {
      setIsLoading(false);
    }
  }, [STUDENT_ID, GRADE_LEVEL_VAL]);

  const handleSuggestionClick = (suggestion: LessonSuggestion) => {
    handleLessonRequest(suggestion.topic, suggestion.track);
  };

  const handleBackToSuggestions = () => {
    setActiveLesson(null);
    setError(null);
  };

  return (
    /*
     * Full-viewport two-column layout.
     * -m-6 / -m-8 cancels the padding from (routes)/layout.tsx
     * so the columns stretch edge-to-edge.
     */
    <div className="flex h-screen overflow-hidden bg-[#FFFEF7]" style={{ margin: "-0px" }}>

      {/* ── Left column: lesson content ────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto min-w-0">

        {/* Header */}
        <header className="bg-white border-b-2 border-[#E7DAC3] px-6 py-5 sticky top-0 z-10">
          <h1
            className="text-2xl font-bold text-[#2F4731]"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            My Learning Plan
          </h1>
          <p className="text-[#2F4731]/60 mt-0.5 text-sm">
            {activeLesson
              ? "Lesson in progress — ask Adeline questions in the panel →"
              : "Choose a topic below or ask Adeline in the panel →"}
          </p>
        </header>

        {/* Status bar */}
        <div className="px-6 pt-4">
          <StudentStatusBar />
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-6 mt-4 flex items-center gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p className="text-sm">{error}</p>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-xs underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* ── Idle: suggestion cards ── */}
        {!activeLesson && !isLoading && (
          <main className="px-6 pb-8 pt-5">
            <div className="grid sm:grid-cols-2 gap-4">
              {LESSON_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion.id}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="text-left p-6 rounded-2xl border-2 border-[#E7DAC3] hover:border-[#BD6809] hover:shadow-lg transition-all bg-white group"
                >
                  <div className="flex items-start gap-4">
                    <span className="text-4xl">{suggestion.emoji}</span>
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-[#2F4731] mb-1 group-hover:text-[#BD6809] transition-colors">
                        {suggestion.title}
                      </h3>
                      <p className="text-sm text-[#2F4731]/60 mb-2">
                        {suggestion.description}
                      </p>
                      <span className="inline-block px-3 py-1 bg-[#2F4731]/10 text-[#2F4731] text-xs font-bold rounded-full">
                        {suggestion.track.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </main>
        )}

        {/* Loading state — Transparent AI thinking visualization */}
        <AgentThinkingState isActive={isLoading} />

        {/* ── Active lesson ── */}
        {activeLesson && !isLoading && (
          <div ref={lessonContainerRef} className="px-6 pb-8 pt-5">
            <button
              onClick={handleBackToSuggestions}
              className="flex items-center gap-2 text-[#BD6809] hover:text-[#2F4731] mb-6 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Back to lesson list</span>
            </button>

            <LessonRenderer
              lesson={activeLesson}
              studentId={STUDENT_ID}
            />

            {/* Ambient "Highlight & Ask" feature */}
            <TextSelectionMenu
              containerRef={lessonContainerRef}
              onAskAboutSelection={(text) => setHighlightedText(text)}
              enabled={!!activeLesson}
            />
          </div>
        )}
      </div>

      {/* ── Right column: Adeline chat panel (380px) ───────────────────────── */}
      <div className="w-[380px] shrink-0 hidden md:flex flex-col border-l-2 border-[#E7DAC3]">
        <AdelineChatPanel
          studentId={STUDENT_ID}
          gradeLevel={GRADE_LEVEL_VAL}
          activeLessonContext={
            activeLesson
              ? {
                  topic: activeLesson.title,
                  track: activeLesson.track,
                  lessonId: activeLesson.lesson_id,
                }
              : null
          }
          onLessonRequest={(topic) => handleLessonRequest(topic)}
          onLessonGenerated={setActiveLesson}
          highlightedContext={highlightedText}
          onHighlightedContextUsed={() => setHighlightedText(null)}
        />
      </div>
    </div>
  );
}
