'use client';

import { useState, useEffect } from 'react';
import { BookOpen, Loader2, RotateCcw, ArrowRight, ChevronUp } from 'lucide-react';

interface DailyBread {
  verse: string;
  reference: string;
  original: string;
  originalMeaning: string;
  translationNote: string;
  context: string;
}

interface DeepDiveSection {
  heading: string;
  content: string;
}

interface DeepDiveResponse {
  reference: string;
  fox_text?: string;
  hebrew_text?: string;
  is_fox: boolean;
  sefaria_url?: string;
  sections: DeepDiveSection[];
}

interface DailyBreadWidgetProps {
  onStudy?: (prompt: string) => void;
  gradeLevel?: string;
}

export function DailyBreadWidget({ onStudy, gradeLevel = '8' }: DailyBreadWidgetProps) {
  const [data, setData] = useState<DailyBread | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [deepDive, setDeepDive] = useState<DeepDiveResponse | null>(null);
  const [deepDiveStatus, setDeepDiveStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');

  const fetchDailyBread = async () => {
    setStatus('loading');
    setError(null);
    setDeepDive(null);
    setDeepDiveStatus('idle');

    try {
      const response = await fetch('/brain/daily-bread');

      if (!response.ok) {
        throw new Error('Failed to load daily verse');
      }

      const dailyBread: DailyBread = await response.json();

      if (!dailyBread.verse || !dailyBread.reference) {
        throw new Error('Invalid verse data');
      }

      setData(dailyBread);
      setStatus('ready');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load today\'s verse';
      setError(message);
      setStatus('error');
    }
  };

  useEffect(() => {
    fetchDailyBread();
  }, []);

  const handleStudy = async () => {
    if (!data) return;

    // If deep dive already loaded, toggle it closed
    if (deepDiveStatus === 'ready') {
      setDeepDiveStatus('idle');
      setDeepDive(null);
      return;
    }

    setDeepDiveStatus('loading');

    try {
      const response = await fetch('/brain/daily-bread/deep-dive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference: data.reference,
          original: data.original || null,
          original_meaning: data.originalMeaning || null,
          context: data.context || null,
          grade_level: gradeLevel,
        }),
      });

      if (!response.ok) throw new Error('Deep dive request failed');

      const result: DeepDiveResponse = await response.json();
      setDeepDive(result);
      setDeepDiveStatus('ready');
    } catch (err) {
      setDeepDiveStatus('error');
      // Fallback: route to chat panel as before
      const prompt = `I want my Daily Bread deep-dive study on ${data.reference} today. Translate it directly from the original ${data.original || 'language'} text, keeping the original meaning and context.`;
      onStudy?.(prompt);
    }
  };

  // Loading state
  if (status === 'loading') {
    return (
      <div className="bg-[#FFFDF5] rounded-2xl border-2 border-[#E7DAC3] p-6 flex flex-col items-center justify-center min-h-64">
        <Loader2 className="w-6 h-6 animate-spin text-[#BD6809] mb-3" />
        <p className="text-[#2F4731]/60 text-sm">Loading today's verse…</p>
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="bg-[#FFFDF5] rounded-2xl border-2 border-[#E7DAC3] p-6">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[#BD6809]/10 flex items-center justify-center flex-shrink-0">
            <BookOpen className="w-5 h-5 text-[#BD6809]" />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-[#2F4731] text-sm mb-1">Daily Bread</h3>
            <p className="text-[#2F4731]/60 text-xs">{error}</p>
          </div>
        </div>
        <button
          onClick={fetchDailyBread}
          className="w-full px-3 py-2 bg-[#BD6809] text-white rounded-lg text-sm font-medium hover:bg-[#A55708] transition-colors flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  // Ready state
  if (status === 'ready' && data) {
    return (
      <div className="bg-[#FFFDF5] rounded-2xl border-2 border-[#E7DAC3] p-6">
        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[#BD6809]/10 flex items-center justify-center flex-shrink-0">
            <BookOpen className="w-5 h-5 text-[#BD6809]" />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-[#2F4731] text-sm">Daily Bread</h3>
            <p className="text-[#2F4731]/50 text-xs">Daily scripture study</p>
          </div>
        </div>

        {/* Verse */}
        <p className="text-[#2F4731] text-sm italic mb-2 leading-relaxed">"{data.verse}"</p>

        {/* Reference */}
        <p className="text-[#BD6809] font-semibold text-xs mb-4">{data.reference}</p>

        {/* Original language section */}
        {data.original && (
          <div className="mb-4 p-3 bg-white rounded-lg border border-[#E7DAC3]">
            <p className="text-xs text-[#2F4731]/60 mb-1">Original Language</p>
            <p className="text-[#2F4731] font-medium text-sm mb-2">{data.original}</p>
            <p className="text-xs text-[#2F4731]/70 italic">
              {data.originalMeaning || 'See how the original language enriches the meaning'}
            </p>
          </div>
        )}

        {/* Translation note */}
        {data.translationNote && (
          <div className="mb-4 p-3 bg-[#F5E6D3] rounded-lg border border-[#E7DAC3]">
            <p className="text-xs text-[#2F4731]/60 mb-1">Translation Note</p>
            <p className="text-xs text-[#2F4731] leading-relaxed">{data.translationNote}</p>
          </div>
        )}

        {/* CTA Button */}
        <button
          onClick={handleStudy}
          disabled={deepDiveStatus === 'loading'}
          className="w-full px-4 py-2 bg-[#2F4731] text-white rounded-lg text-sm font-semibold hover:bg-[#1F3321] transition-colors flex items-center justify-center gap-2 group disabled:opacity-60"
        >
          {deepDiveStatus === 'loading' ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Studying the text…</>
          ) : deepDiveStatus === 'ready' ? (
            <><ChevronUp className="w-4 h-4" /> Close Deep Dive</>
          ) : (
            <>Start Deep Dive Study <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>
          )}
        </button>

        {/* Deep Dive — inline result */}
        {deepDiveStatus === 'ready' && deepDive && (
          <div className="mt-4 space-y-3">
            {/* Fox translation banner */}
            {deepDive.fox_text && (
              <div className="p-3 bg-[#F5E6D3] rounded-lg border border-[#E7DAC3]">
                <p className="text-[10px] text-[#2F4731]/60 mb-1 font-semibold uppercase tracking-wider">
                  {deepDive.is_fox ? 'Everett Fox Translation' : 'English Text'}
                </p>
                <p className="text-sm text-[#2F4731] italic leading-relaxed">"{deepDive.fox_text}"</p>
                {deepDive.hebrew_text && (
                  <p className="text-xs text-[#2F4731]/60 mt-2 font-mono">{deepDive.hebrew_text}</p>
                )}
                {deepDive.sefaria_url && (
                  <a
                    href={deepDive.sefaria_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-[#BD6809] mt-1 inline-block hover:underline"
                  >
                    View on Sefaria →
                  </a>
                )}
              </div>
            )}

            {/* Study sections */}
            {deepDive.sections.map((section, i) => (
              <div key={i} className="p-3 bg-white rounded-lg border border-[#E7DAC3]">
                <p className="text-xs font-bold text-[#2F4731] mb-1.5">{section.heading}</p>
                <p className="text-xs text-[#2F4731]/80 leading-relaxed">{section.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return null;
}
