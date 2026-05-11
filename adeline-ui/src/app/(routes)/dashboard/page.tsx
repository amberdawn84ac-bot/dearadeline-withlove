'use client';

import { Suspense, useState, useCallback, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, ArrowLeft, RefreshCw, Award, Hammer, Clock } from 'lucide-react';
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport, isDataUIPart, isToolUIPart, getToolName } from 'ai';
import { StudentStatusBar } from '@/components/StudentStatusBar';
import { AdelineChatPanel } from '@/components/AdelineChatPanel';
import { SpacedRepWidget } from '@/components/dashboard/SpacedRepWidget';
import { useStudent } from '@/lib/useStudent';
import LessonRenderer from '@/components/lessons/LessonRenderer';
import { MasteryCheckWidget } from '@/components/gen-ui/widgets/MasteryCheckWidget';
import { LabMissionWidget } from '@/components/gen-ui/widgets/LabMissionWidget';
import { getLearningPlan } from '@/lib/brain-client';
import { supabase } from '@/lib/supabase';
import type { LessonResponse, LessonBlockResponse, Track, LessonSuggestion, ProjectSuggestion, BookRecommendation } from '@/lib/brain-client';
import { RecommendedBooks } from '@/components/dashboard/RecommendedBooks';
import GenUIRendererWithHighlightAsk from '@/components/GenUIRenderer';

// ── Types ──────────────────────────────────────────────────────────────────────

// Discriminated union matching what /api/lesson sends as 2: data stream annotations
type LessonAnnotation =
  | { type: 'block'; block: LessonBlockResponse }
  | { type: 'done'; title?: string }
  | { type: 'status'; message: string }
  | { type: 'error'; message: string };

// Structural type for a resolved tool call — matches ai@6 ToolUIPart output-available state.
interface ResultInvocation {
  state: 'output-available';
  toolCallId: string;
  toolName: string;
  input: unknown;
  result: Record<string, unknown>;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const SOURCE_BADGES: Record<string, { bg: string; text: string; label: string }> = {
  zpd:        { bg: '#F0FDF4', text: '#166534', label: 'Ready to Learn' },
  cross_track: { bg: '#EFF6FF', text: '#1D4ED8', label: 'Cross-Track' },
  continue:   { bg: '#FDF6E9', text: '#BD6809', label: 'Continue' },
  explore:    { bg: '#F3F4F6', text: '#374151', label: 'Explore' },
  interest:   { bg: '#FDF2F8', text: '#BE185D', label: 'Your Interest' },
};

const DIFFICULTY_BADGES: Record<string, { bg: string; text: string }> = {
  SEEDLING: { bg: '#F0FDF4', text: '#166534' },
  GROWING:  { bg: '#FEF3C7', text: '#92400E' },
  HARVEST:  { bg: '#FEE2E2', text: '#991B1B' },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

// ── DashboardContent ───────────────────────────────────────────────────────────

function DashboardContent() {
  const { student, loading: profileLoading } = useStudent();
  const searchParams = useSearchParams();
  const studyPrompt = searchParams.get('study');
  const studentId = student?.id ?? '';
  const gradeLevel = student?.gradeLevel ?? '8';
  const [activeLesson, setActiveLesson] = useState<LessonResponse | null>(null);
  const [suggestions, setSuggestions] = useState<LessonSuggestion[]>([]);
  const [projects, setProjects] = useState<ProjectSuggestion[]>([]);
  const [totalCredits, setTotalCredits] = useState(0);
  const [weeklyCredits, setWeeklyCredits] = useState(0);
  const [recommendedBooks, setRecommendedBooks] = useState<BookRecommendation[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const [currentLessonMeta, setCurrentLessonMeta] = useState<{ topic: string; track: Track } | null>(null);
  const router = useRouter();

  // Stable transport reference — must not be recreated on every render or useChat
  // will re-initialize its internal reducer and cause an infinite update loop.
  const chatTransport = useMemo(() => new DefaultChatTransport({
    api: '/api/lesson',
    fetch: async (url, options) => {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      return fetch(url, {
        ...options,
        headers: {
          ...(options?.headers as Record<string, string> | undefined),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), []);

  // useChat drives lesson streaming via /api/lesson translation bridge
  const { messages, setMessages, sendMessage: append, status: chatStatus } = useChat({
    transport: chatTransport,
    onError: (err: Error) => {
      console.error('[Dashboard] Lesson stream error:', err);
    },
  });

  const isStreaming = chatStatus === 'streaming' || chatStatus === 'submitted';

  // Derive everything from the last assistant message parts — ai@6 stores data as DataUIPart
  // and tool invocations as ToolUIPart in m.parts; there is no m.annotations or m.toolInvocations.
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const msgParts = lastAssistant?.parts ?? [];

  // Reconstruct LessonAnnotation union from data-* parts so downstream filtering is unchanged.
  const lessonAnnotations: LessonAnnotation[] = msgParts
    .filter(isDataUIPart)
    .map((p): LessonAnnotation | null => {
      if (p.type === 'data-block') return { type: 'block', ...(p.data as { block: LessonBlockResponse }) };
      if (p.type === 'data-done') return { type: 'done', ...(p.data as { title?: string }) };
      if (p.type === 'data-status') return { type: 'status', ...(p.data as { message: string }) };
      if (p.type === 'data-error') return { type: 'error', ...(p.data as { message: string }) };
      return null;
    })
    .filter((a): a is LessonAnnotation => a !== null);

  const lessonBlocks = lessonAnnotations
    .filter((a): a is Extract<LessonAnnotation, { type: 'block' }> => a.type === 'block')
    .map((a) => a.block);
  const doneEvent = lessonAnnotations.find(
    (a): a is Extract<LessonAnnotation, { type: 'done' }> => a.type === 'done',
  );
  const statusEvent = lessonAnnotations.find(
    (a): a is Extract<LessonAnnotation, { type: 'status' }> => a.type === 'status',
  );
  const lessonTitle = doneEvent?.title ?? '';
  const lessonStatus = isStreaming
    ? (statusEvent?.message ?? 'Adeline is preparing your lesson…')
    : '';

  // Tool invocations are ToolUIPart/DynamicToolUIPart in m.parts with state 'output-available'.
  const lessonToolInvocations: ResultInvocation[] = msgParts
    .filter(isToolUIPart)
    .filter((p) => p.state === 'output-available')
    .map((p) => ({
      state: 'output-available' as const,
      toolCallId: p.toolCallId,
      toolName: getToolName(p),
      input: p.input,
      result: p.output as Record<string, unknown>,
    }));

  // Fetch dynamic learning plan suggestions
  const fetchSuggestions = useCallback(async () => {
    if (!studentId) return;
    setLoadingSuggestions(true);
    setSuggestionsError(null);
    try {
      const plan = await getLearningPlan(studentId, 6);
      setSuggestions(plan.suggestions);
      setProjects(plan.projects || []);
      setTotalCredits(plan.total_credits_earned || 0);
      setWeeklyCredits(plan.credits_this_week || 0);
      setRecommendedBooks(plan.recommended_books || []);
    } catch (error) {
      console.error('[Dashboard] Failed to fetch learning plan:', error);
      setSuggestionsError('Unable to load your learning plan. Please try again.');
    } finally {
      setLoadingSuggestions(false);
    }
  }, [studentId]);

  useEffect(() => {
    if (studentId) fetchSuggestions();
  }, [studentId, fetchSuggestions]);

  const handleLessonGenerated = useCallback((lesson: LessonResponse) => {
    setActiveLesson(lesson);
  }, []);

  const handleBackToSuggestions = useCallback(() => {
    setActiveLesson(null);
    setMessages([]);
  }, [setMessages]);

  const handleSuggestionClick = useCallback(
    (suggestion: LessonSuggestion) => {
      const hasContent = messages.some((m) => m.role === 'assistant');
      if (isStreaming || hasContent || !studentId) return;
      setActiveLesson(null);
      setCurrentLessonMeta({ topic: suggestion.title, track: suggestion.track as Track });
      append(
        { text: suggestion.title },
        {
          body: {
            lesson_request: {
              student_id: studentId,
              track: suggestion.track as Track,
              topic: suggestion.title,
              is_homestead: false,
              grade_level: gradeLevel,
            },
          },
        },
      );
    },
    [studentId, gradeLevel, isStreaming, messages, append],
  );

  const handleRegenerateLesson = useCallback(() => {
    if (!currentLessonMeta || !studentId || isStreaming) return;
    setMessages([]);
    append(
      { text: currentLessonMeta.topic },
      {
        body: {
          lesson_request: {
            student_id: studentId,
            track: currentLessonMeta.track,
            topic: currentLessonMeta.topic,
            is_homestead: false,
            grade_level: gradeLevel,
            force_regenerate: true,
          },
        },
      },
    );
  }, [currentLessonMeta, studentId, gradeLevel, isStreaming, setMessages, append]);

  return (
    <div className="flex flex-col h-screen -m-6 md:-m-8 overflow-hidden bg-[#FFFEF7]">

      {/* ── Adeline chat — pinned to top, full width ── */}
      <div className="shrink-0 border-b-2 border-[#E7DAC3]" style={{ height: '340px' }}>
        <AdelineChatPanel
          studentId={studentId}
          gradeLevel={gradeLevel}
          onLessonGenerated={handleLessonGenerated}
          initialPrompt={studyPrompt}
        />
      </div>

      {/* ── Scrollable content below chat ── */}
      <div className="flex-1 overflow-y-auto min-w-0">
        <div className="px-6 pt-5">
          <StudentStatusBar />
        </div>

        <div className="px-6 pt-3">
          <SpacedRepWidget />
        </div>

        {/* ── Streaming lesson view ── */}
        {!activeLesson && (isStreaming || lessonBlocks.length > 0) && (
          <div className="px-6 pb-8 pt-5">
            {!isStreaming && lessonBlocks.length > 0 && (
              <div className="flex items-center gap-3 mb-4">
                <button
                  onClick={handleBackToSuggestions}
                  className="flex items-center gap-2 text-[#BD6809] hover:text-[#2F4731] transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span className="text-sm font-medium">Back to lesson list</span>
                </button>
                {currentLessonMeta && (
                  <button
                    onClick={handleRegenerateLesson}
                    className="flex items-center gap-2 text-[#2F4731]/50 hover:text-[#2F4731] transition-colors ml-auto"
                    title="Regenerate this lesson with fresh content"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span className="text-sm font-medium">Regenerate lesson</span>
                  </button>
                )}
              </div>
            )}

            {isStreaming && (
              <div className="flex items-center gap-3 pb-4">
                <Loader2 className="w-5 h-5 animate-spin text-[#BD6809]" />
                <p className="text-sm text-[#2F4731]/60 italic">{lessonStatus}</p>
              </div>
            )}

            {lessonTitle && (
              <h2 className="text-xl font-bold text-[#2F4731] mb-4">{lessonTitle}</h2>
            )}

            {/* Standard toolInvocations render — no manual state, no data-part parsing */}
            {lessonBlocks.length > 0 ? (
              <GenUIRendererWithHighlightAsk
                lessonId={doneEvent?.title ?? `lesson-${Date.now()}`}
                blocks={lessonBlocks}
                isHomestead={false}
                oasStandards={[]}
                agentName=""
                studentId={studentId}
              />
            ) : (
              // While streaming and no blocks yet, show the raw text content
              messages
                .filter((m) => m.role === 'assistant')
                .slice(-1)
                .map((m) => {
                  const text = (m.parts ?? [])
                    .filter((p): p is { type: 'text'; text: string } => p.type === 'text')
                    .map((p) => p.text)
                    .join('');
                  return text ? (
                    <div
                      key={m.id}
                      className="prose prose-stone max-w-none whitespace-pre-wrap text-[#2F4731] text-sm leading-relaxed"
                    >
                      {text}
                    </div>
                  ) : null;
                })
            )}
          </div>
        )}

        {/* ── Idle: suggestion cards ── */}
        {!activeLesson && !isStreaming && lessonBlocks.length === 0 && (
          <main className="px-6 pb-8 pt-5">
            {loadingSuggestions && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-[#BD6809]" />
                <p className="ml-3 text-[#2F4731]/60">Loading your learning plan…</p>
              </div>
            )}

            {suggestionsError && (
              <div className="text-center py-12">
                <p className="text-[#991B1B] mb-4">{suggestionsError}</p>
                <button
                  onClick={fetchSuggestions}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#2F4731] text-white rounded-lg hover:bg-[#2F4731]/90 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </button>
              </div>
            )}

            {!loadingSuggestions && !suggestionsError && (
              <>
                {/* Credits Summary */}
                <div className="flex items-center gap-6 mb-6 p-4 bg-white rounded-xl border border-[#E7DAC3]">
                  <div className="flex items-center gap-2">
                    <Award className="w-5 h-5 text-[#BD6809]" />
                    <div>
                      <p className="text-xs text-[#2F4731]/60">Total Credits</p>
                      <p className="text-lg font-bold text-[#2F4731]">{totalCredits.toFixed(1)}</p>
                    </div>
                  </div>
                  <div className="h-8 w-px bg-[#E7DAC3]" />
                  <div className="flex items-center gap-2">
                    <Clock className="w-5 h-5 text-[#2F4731]/60" />
                    <div>
                      <p className="text-xs text-[#2F4731]/60">This Week</p>
                      <p className="text-lg font-bold text-[#2F4731]">{weeklyCredits.toFixed(1)}</p>
                    </div>
                  </div>
                </div>

                {/* Lessons Section */}
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-[#2F4731]/60">
                    {suggestions.length > 0
                      ? `${suggestions.length} lessons recommended for you`
                      : 'Getting your first lessons ready...'}
                  </p>
                  <button
                    onClick={fetchSuggestions}
                    className="text-sm text-[#BD6809] hover:text-[#2F4731] flex items-center gap-1 transition-colors"
                  >
                    <RefreshCw className="w-3 h-3" />
                    Refresh
                  </button>
                </div>

                {suggestions.length === 0 && !loadingSuggestions && (
                  <div className="text-center py-10 px-6 bg-white rounded-2xl border-2 border-dashed border-[#E7DAC3] mb-6">
                    <p className="text-lg font-bold text-[#2F4731] mb-2">
                      Welcome to Dear Adeline!
                    </p>
                    <p className="text-sm text-[#2F4731]/60 max-w-md mx-auto">
                      Ask Adeline a question in the chat panel to get started, or hit Refresh above.
                      Your personalized learning plan will build itself as you explore.
                    </p>
                  </div>
                )}

                <div className="grid sm:grid-cols-2 gap-4">
                  {suggestions.map((suggestion) => {
                    const sourceBadge = SOURCE_BADGES[suggestion.source] || SOURCE_BADGES.explore;
                    return (
                      <button
                        key={suggestion.id}
                        onClick={() => handleSuggestionClick(suggestion)}
                        disabled={isStreaming}
                        className="text-left p-6 rounded-2xl border-2 border-[#E7DAC3] hover:border-[#BD6809] hover:shadow-lg transition-all bg-white group disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <div className="flex items-start gap-4">
                          <span className="text-4xl">{suggestion.emoji}</span>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-lg font-bold text-[#2F4731] group-hover:text-[#BD6809] transition-colors">
                                {suggestion.title}
                              </h3>
                            </div>
                            <p className="text-sm text-[#2F4731]/60 mb-2">{suggestion.description}</p>
                            <div className="flex flex-wrap gap-2">
                              <span className="inline-block px-3 py-1 bg-[#2F4731]/10 text-[#2F4731] text-xs font-bold rounded-full">
                                {suggestion.track.replace(/_/g, ' ')}
                              </span>
                              <span
                                className="inline-block px-2 py-0.5 text-[10px] font-bold rounded-full"
                                style={{ backgroundColor: sourceBadge.bg, color: sourceBadge.text }}
                              >
                                {sourceBadge.label}
                              </span>
                              {suggestion.grade_band && (
                                <span className="inline-block px-2 py-0.5 text-[10px] text-[#2F4731]/50 rounded-full border border-[#E7DAC3]">
                                  {suggestion.grade_band}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <RecommendedBooks books={recommendedBooks} />

                {/* Projects Section */}
                {projects.length > 0 && (
                  <>
                    <div className="flex items-center gap-2 mt-8 mb-4">
                      <Hammer className="w-4 h-4 text-[#BD6809]" />
                      <p className="text-sm font-bold text-[#2F4731]">Portfolio Projects</p>
                      <span className="text-xs text-[#2F4731]/50">
                        — Real accomplishments, not assignments
                      </span>
                    </div>
                    <div className="grid sm:grid-cols-3 gap-4">
                      {projects.map((project) => {
                        const diffBadge = DIFFICULTY_BADGES[project.difficulty] || DIFFICULTY_BADGES.SEEDLING;
                        return (
                          <button
                            key={project.id}
                            onClick={() => router.push(`/dashboard/projects?id=${project.id}`)}
                            className="text-left p-4 rounded-xl border-2 border-[#E7DAC3] hover:border-[#BD6809] hover:shadow-lg transition-all bg-white group"
                          >
                            <div className="flex items-center gap-3 mb-2">
                              <span className="text-2xl">{project.emoji}</span>
                              <h4 className="text-sm font-bold text-[#2F4731] group-hover:text-[#BD6809] transition-colors">
                                {project.title}
                              </h4>
                            </div>
                            <p className="text-xs text-[#2F4731]/60 mb-3 line-clamp-2">{project.tagline}</p>
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block px-2 py-0.5 text-[10px] font-bold rounded-full"
                                style={{ backgroundColor: diffBadge.bg, color: diffBadge.text }}
                              >
                                {project.difficulty}
                              </span>
                              <span className="text-[10px] text-[#2F4731]/50">
                                ~{project.estimated_hours}h
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </>
            )}
          </main>
        )}

        {/* Active lesson (legacy poll-based path) */}
        {activeLesson && (
          <div className="px-6 pb-8 pt-5">
            <button
              onClick={handleBackToSuggestions}
              className="flex items-center gap-2 text-[#BD6809] hover:text-[#2F4731] mb-6 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Back to lesson list</span>
            </button>
            <LessonRenderer lesson={activeLesson} studentId={studentId} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
