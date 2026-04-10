'use client';

import { Suspense, useState, useCallback, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, ArrowLeft, RefreshCw, Award, Hammer, Clock } from 'lucide-react';
import { StudentStatusBar } from '@/components/StudentStatusBar';
import { AdelineChatPanel } from '@/components/AdelineChatPanel';
import { SpacedRepWidget } from '@/components/dashboard/SpacedRepWidget';
import { useStudent } from '@/lib/useStudent';
import LessonRenderer from '@/components/lessons/LessonRenderer';
import { generateLesson, getLearningPlan } from '@/lib/brain-client';
import type { LessonResponse, Track, LessonSuggestion, ProjectSuggestion, LearningPlanResponse, BookRecommendation } from '@/lib/brain-client';
import { RecommendedBooks } from '@/components/dashboard/RecommendedBooks';

// Source badge colors for learning plan suggestions
const SOURCE_BADGES: Record<string, { bg: string; text: string; label: string }> = {
  zpd: { bg: '#F0FDF4', text: '#166534', label: 'Ready to Learn' },
  cross_track: { bg: '#EFF6FF', text: '#1D4ED8', label: 'Cross-Track' },
  continue: { bg: '#FDF6E9', text: '#BD6809', label: 'Continue' },
  explore: { bg: '#F3F4F6', text: '#374151', label: 'Explore' },
  interest: { bg: '#FDF2F8', text: '#BE185D', label: 'Your Interest' },
};

// Difficulty badge colors for projects
const DIFFICULTY_BADGES: Record<string, { bg: string; text: string }> = {
  SEEDLING: { bg: '#F0FDF4', text: '#166534' },
  GROWING: { bg: '#FEF3C7', text: '#92400E' },
  HARVEST: { bg: '#FEE2E2', text: '#991B1B' },
};

function DashboardContent() {
  const { student, loading: profileLoading } = useStudent();
  const searchParams = useSearchParams();
  const studyPrompt = searchParams.get('study');
  const studentId = student?.id ?? '';
  const gradeLevel = student?.gradeLevel ?? '8';
  const [activeLesson, setActiveLesson] = useState<LessonResponse | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<LessonSuggestion[]>([]);
  const [projects, setProjects] = useState<ProjectSuggestion[]>([]);
  const [totalCredits, setTotalCredits] = useState(0);
  const [weeklyCredits, setWeeklyCredits] = useState(0);
  const [recommendedBooks, setRecommendedBooks] = useState<BookRecommendation[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const router = useRouter();

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
    if (studentId) {
      fetchSuggestions();
    }
  }, [studentId, fetchSuggestions]);

  const handleLessonGenerated = useCallback((lesson: LessonResponse) => {
    console.log('[Dashboard] Lesson generated:', lesson.title);
    setActiveLesson(lesson);
    setIsStreaming(false);
  }, []);

  const handleSuggestionClick = useCallback(async (suggestion: LessonSuggestion) => {
    if (isStreaming || !studentId) return;
    
    setIsStreaming(true);
    setActiveLesson(null);
    
    try {
      const lesson = await generateLesson({
        student_id: studentId,
        track: suggestion.track as Track,
        topic: suggestion.title,
        is_homestead: false,
        grade_level: gradeLevel,
      });
      handleLessonGenerated(lesson);
    } catch (error) {
      console.error('[Dashboard] Lesson generation failed:', error);
      setIsStreaming(false);
    }
  }, [studentId, gradeLevel, isStreaming, handleLessonGenerated]);

  const handleBackToSuggestions = () => {
    setActiveLesson(null);
  };

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
        {/* Status bar */}
        <div className="px-6 pt-5">
          <StudentStatusBar />
        </div>

        {/* Spaced rep widget — compact strip */}
        <div className="px-6 pt-3">
          <SpacedRepWidget />
        </div>

        {/* ── Idle: suggestion cards ── */}
        {!activeLesson && (
          <main className="px-6 pb-8 pt-5">
            {isStreaming && (
              <div className="flex items-center gap-3 py-10 justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-[#BD6809]" />
                <p className="text-[#2F4731]/60 italic">Adeline is preparing your lesson…</p>
              </div>
            )}

            {!isStreaming && loadingSuggestions && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-[#BD6809]" />
                <p className="ml-3 text-[#2F4731]/60">Loading your learning plan…</p>
              </div>
            )}

            {!isStreaming && suggestionsError && (
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

            {!isStreaming && !loadingSuggestions && !suggestionsError && (
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
                  {suggestions.map(suggestion => {
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

                {/* Recommended Reading */}
                <RecommendedBooks books={recommendedBooks} />

                {/* Projects Section */}
                {projects.length > 0 && (
                  <>
                    <div className="flex items-center gap-2 mt-8 mb-4">
                      <Hammer className="w-4 h-4 text-[#BD6809]" />
                      <p className="text-sm font-bold text-[#2F4731]">
                        Portfolio Projects
                      </p>
                      <span className="text-xs text-[#2F4731]/50">
                        — Real accomplishments, not assignments
                      </span>
                    </div>
                    <div className="grid sm:grid-cols-3 gap-4">
                      {projects.map(project => {
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

        {/* Active lesson */}
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
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
