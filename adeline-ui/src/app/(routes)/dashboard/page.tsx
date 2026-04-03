'use client';

import { useState, useEffect, useCallback } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { StudentStatusBar } from '@/components/StudentStatusBar';
import { AdelineChatPanel } from '@/components/AdelineChatPanel';

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

const STUDENT_ID = 'demo-student-001';

export default function DashboardPage() {
  const [activeLessonId, setActiveLessonId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const handleLessonGenerated = useCallback((lesson: any) => {
    console.log('[Dashboard] Lesson generated:', lesson.title);
    setActiveLessonId('active');
  }, []);

  const handleBackToSuggestions = () => {
    setActiveLessonId(null);
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
            {activeLessonId
              ? 'Lesson in progress — ask Adeline questions in the panel →'
              : 'Choose a topic below or ask Adeline in the panel →'}
          </p>
        </header>

        {/* Status bar */}
        <div className="px-6 pt-5">
          <StudentStatusBar />
        </div>

        {/* ── Idle: suggestion cards ── */}
        {!activeLessonId && (
          <main className="px-6 pb-8 pt-5">
            {isStreaming && (
              <div className="flex items-center gap-3 py-10 justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-[#BD6809]" />
                <p className="text-[#2F4731]/60 italic">Adeline is preparing your lesson…</p>
              </div>
            )}

            <div className="grid sm:grid-cols-2 gap-4">
              {LESSON_SUGGESTIONS.map(suggestion => (
                <button
                  key={suggestion.id}
                  onClick={() => handleLessonGenerated(suggestion)}
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
          </main>
        )}

        {/* Active lesson placeholder */}
        {activeLessonId && (
          <div className="px-6 pb-8 pt-4">
            <button
              onClick={handleBackToSuggestions}
              className="text-[#BD6809] hover:text-[#2F4731] mb-4 text-sm font-medium transition-colors"
            >
              ← Back to lesson list
            </button>
            <div className="flex items-center justify-center py-16">
              <p className="text-[#2F4731]/60 text-center">Lesson content will render here as you chat with Adeline</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right column: Adeline chat panel ── */}
      <div className="w-[380px] shrink-0 hidden md:flex flex-col border-l-2 border-[#E7DAC3]">
        <AdelineChatPanel studentId={STUDENT_ID} onLessonGenerated={handleLessonGenerated} />
      </div>
    </div>
  );
}
