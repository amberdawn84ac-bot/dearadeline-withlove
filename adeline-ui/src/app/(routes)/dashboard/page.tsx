'use client';

import { Suspense, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, ArrowLeft } from 'lucide-react';
import { StudentStatusBar } from '@/components/StudentStatusBar';
import { AdelineChatPanel } from '@/components/AdelineChatPanel';
import { SpacedRepWidget } from '@/components/dashboard/SpacedRepWidget';
import { useStudent } from '@/lib/useStudent';
import LessonRenderer from '@/components/lessons/LessonRenderer';
import type { LessonResponse } from '@/lib/brain-client';

interface LessonSuggestion {
  id: string;
  title: string;
  track: string;
  description: string;
  emoji: string;
}

const LESSON_SUGGESTIONS: LessonSuggestion[] = [
  { id: '1', title: 'Butterflies of North America', track: 'Science', description: 'Investigate butterfly life cycles and adaptations', emoji: '🦋' },
  { id: '2', title: 'The American Revolution', track: 'History', description: 'Primary sources from the founding era', emoji: '🏛️' },
  { id: '3', title: 'Water Cycle Investigation', track: 'Science', description: 'Hands-on experiments with evaporation and condensation', emoji: '💧' },
  { id: '4', title: 'Scripture Study: Psalms', track: 'Discipleship', description: 'Hebrew poetry and original meanings', emoji: '📖' },
];

function DashboardContent() {
  const { student, loading: profileLoading } = useStudent();
  const searchParams = useSearchParams();
  const studyPrompt = searchParams.get('study');
  const studentId = student?.id ?? '';
  const gradeLevel = student?.gradeLevel ?? '8';
  const [activeLesson, setActiveLesson] = useState<LessonResponse | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const handleLessonGenerated = useCallback((lesson: LessonResponse) => {
    console.log('[Dashboard] Lesson generated:', lesson.title);
    setActiveLesson(lesson);
  }, []);

  const handleBackToSuggestions = () => {
    setActiveLesson(null);
  };

  return (
    <div className="flex h-screen -m-6 md:-m-8 overflow-hidden bg-[#FFFEF7]">
      {/* ── Left column: lesson content ── */}
      <div className="flex-1 overflow-y-auto min-w-0">
        {/* Page header */}
        <header className="bg-white border-b-2 border-[#E7DAC3] px-6 py-5 sticky top-0 z-10">
          <h1
            className="text-2xl font-bold text-[#2F4731]"
            style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}
          >
            My Learning Plan
          </h1>
          <p className="text-[#2F4731]/60 mt-0.5 text-sm">
            {activeLesson
              ? 'Lesson in progress — ask Adeline questions in the panel →'
              : 'Choose a topic below or ask Adeline in the panel →'}
          </p>
        </header>

        {/* Status bar */}
        <div className="px-6 pt-5">
          <StudentStatusBar />
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

            {!isStreaming && (
              <div className="grid sm:grid-cols-2 gap-4">
                {LESSON_SUGGESTIONS.map(suggestion => (
                  <button
                    key={suggestion.id}
                    onClick={() => handleLessonGenerated(suggestion as any)}
                    disabled={isStreaming}
                    className="text-left p-6 rounded-2xl border-2 border-[#E7DAC3] hover:border-[#BD6809] hover:shadow-lg transition-all bg-white group disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-start gap-4">
                      <span className="text-4xl">{suggestion.emoji}</span>
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-[#2F4731] mb-1 group-hover:text-[#BD6809] transition-colors">
                          {suggestion.title}
                        </h3>
                        <p className="text-sm text-[#2F4731]/60 mb-2">{suggestion.description}</p>
                        <span className="inline-block px-3 py-1 bg-[#2F4731]/10 text-[#2F4731] text-xs font-bold rounded-full">
                          {suggestion.track}
                        </span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
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

      {/* ── Right column: Spaced Rep + Adeline chat panel ── */}
      <div className="w-[380px] shrink-0 hidden md:flex flex-col border-l-2 border-[#E7DAC3] overflow-y-auto">
        {/* Spaced Repetition Review */}
        <div className="flex-shrink-0 px-6 pt-6 pb-4">
          <SpacedRepWidget />
        </div>

        {/* Adeline Chat Panel */}
        <div className="flex-1 min-h-0">
          <AdelineChatPanel studentId={studentId} gradeLevel={gradeLevel} onLessonGenerated={handleLessonGenerated} initialPrompt={studyPrompt} />
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
