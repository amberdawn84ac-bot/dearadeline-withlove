'use client';

import { useState, useCallback } from 'react';
import { Loader2, BookOpen, MessageCircle } from 'lucide-react';
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
  const [mobileTab, setMobileTab] = useState<'learn' | 'chat'>('learn');

  const handleLessonGenerated = useCallback((lesson: any) => {
    console.log('[Dashboard] Lesson generated:', lesson.title);
    setActiveLessonId('active');
  }, []);

  const handleBackToSuggestions = () => {
    setActiveLessonId(null);
  };

  return (
    <div className="flex flex-col md:flex-row h-screen -m-6 md:-m-8 overflow-hidden bg-[#FFFEF7]">

      {/* ── Left column: lesson content ── */}
      <div className={[
        "flex-1 overflow-y-auto min-w-0 flex flex-col",
        "pb-14 md:pb-0",           // space for mobile tab bar
        mobileTab === 'chat' ? "hidden md:flex" : "flex",
      ].join(" ")}>
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
              ? 'Lesson in progress — tap Chat below to ask Adeline'
              : 'Choose a topic, or tap Chat below to ask Adeline'}
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
                  onClick={() => { handleLessonGenerated(suggestion); setMobileTab('chat'); }}
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
      <div className={[
        "md:w-[380px] md:shrink-0 md:flex flex-col border-l-2 border-[#E7DAC3]",
        mobileTab === 'chat' ? "flex flex-1" : "hidden md:flex",
      ].join(" ")}>
        {/* Extra bottom padding on mobile so chat input clears the tab bar */}
        <div className="flex flex-col flex-1 md:pb-0 pb-14 min-h-0">
          <AdelineChatPanel studentId={STUDENT_ID} onLessonGenerated={handleLessonGenerated} />
        </div>
      </div>

      {/* ── Mobile bottom tab bar ── */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-14 flex border-t-2 border-[#E7DAC3] bg-white z-50">
        <button
          onClick={() => setMobileTab('learn')}
          className={[
            "flex-1 flex flex-col items-center justify-center gap-0.5 text-xs font-bold transition-colors",
            mobileTab === 'learn'
              ? "text-[#2F4731] border-t-2 border-[#2F4731] -mt-px bg-[#FFFEF7]"
              : "text-[#2F4731]/40",
          ].join(" ")}
        >
          <BookOpen size={20} />
          Learn
        </button>
        <button
          onClick={() => setMobileTab('chat')}
          className={[
            "flex-1 flex flex-col items-center justify-center gap-0.5 text-xs font-bold transition-colors",
            mobileTab === 'chat'
              ? "text-[#BD6809] border-t-2 border-[#BD6809] -mt-px bg-[#FFFEF7]"
              : "text-[#2F4731]/40",
          ].join(" ")}
        >
          <MessageCircle size={20} />
          Chat
        </button>
      </nav>

    </div>
  );
}

