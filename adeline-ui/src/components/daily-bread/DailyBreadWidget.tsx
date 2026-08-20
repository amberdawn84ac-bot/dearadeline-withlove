'use client';

import { useState, useEffect } from 'react';
import { BookOpen, Loader2, RotateCcw, ArrowRight } from 'lucide-react';

interface DailyBread {
  verse: string;
  reference: string;
  original: string;
  originalMeaning: string;
  translationNote: string;
  context: string;
  lessonTitle: string;
  bigIdea: string;
  readTogether: string[];
  familyDiscussion: string[];
  practice: string;
  prayer: string;
  creditConnections: string[];
  portfolioEvidence: string[];
  originalText?: string;
  sourceVersion?: string;
  sourceUrl?: string;
  isFoxTranslation?: boolean;
}

interface DailyBreadWidgetProps {
  onStudy?: (prompt: string) => void;
  gradeLevel?: string;
}

export function DailyBreadWidget({ onStudy, gradeLevel = '8' }: DailyBreadWidgetProps) {
  const [data, setData] = useState<DailyBread | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  const fetchDailyBread = async () => {
    setStatus('loading');
    setError(null);

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

  const handleStudy = () => {
    if (!data) return;
    const prompt = `Daily Bread deep-dive study on ${data.reference}. The key word is "${data.original}" — ${data.originalMeaning}. Teach me what this passage actually says in the original language, the historical context, and what it means for how I live today.`;
    onStudy?.(prompt);
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
            <p className="text-[#2F4731]/50 text-xs">A new family Bible lesson every day</p>
          </div>
        </div>

        {/* Verse */}
        <p className="text-[#2F4731] text-sm italic mb-2 leading-relaxed">"{data.verse}"</p>

        {/* Reference */}
        <p className="text-[#BD6809] font-semibold text-xs mb-4">{data.reference}</p>
        {data.sourceUrl && <a href={data.sourceUrl} target="_blank" rel="noreferrer" className="mb-4 inline-flex text-[11px] font-semibold text-[#2F4731]/60 underline">Source text: {data.isFoxTranslation ? 'Everett Fox via Sefaria' : (data.sourceVersion || 'Sefaria')} ↗</a>}

        <div className="mb-4">
          <h4 className="font-bold text-[#2F4731]">{data.lessonTitle || 'Today’s Bible lesson'}</h4>
          <p className="mt-1 text-xs leading-relaxed text-[#2F4731]/70">{data.bigIdea}</p>
        </div>

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

        {data.readTogether?.length > 0 && <div className="mb-4"><p className="text-xs font-bold uppercase tracking-wide text-[#BD6809]">Read together</p><ul className="mt-1 list-disc pl-4 text-xs leading-5 text-[#2F4731]/75">{data.readTogether.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        {data.familyDiscussion?.length > 0 && <div className="mb-4"><p className="text-xs font-bold uppercase tracking-wide text-[#BD6809]">Talk about it</p><ol className="mt-1 list-decimal pl-4 text-xs leading-5 text-[#2F4731]/75">{data.familyDiscussion.map((item) => <li key={item}>{item}</li>)}</ol></div>}
        {data.practice && <div className="mb-4 rounded-lg bg-[#EEF4E9] p-3"><p className="text-xs font-bold text-[#2F4731]">Live it today</p><p className="mt-1 text-xs leading-5 text-[#2F4731]/75">{data.practice}</p></div>}
        {data.prayer && <p className="mb-4 text-xs italic leading-5 text-[#2F4731]/70">{data.prayer}</p>}
        {data.creditConnections?.length > 0 && <div className="mb-4 border-t border-[#E7DAC3] pt-3"><p className="text-[11px] font-bold uppercase text-[#2F4731]/50">Evidence can support</p><p className="mt-1 text-xs text-[#2F4731]/70">{data.creditConnections.map((track) => track.replace(/_/g, ' ')).join(' · ')}</p>{data.portfolioEvidence?.[0] && <p className="mt-2 text-[11px] italic text-[#2F4731]/55">Portfolio evidence: {data.portfolioEvidence[0]}</p>}</div>}

        {/* CTA Button */}
        {onStudy && <button
          onClick={handleStudy}
          className="w-full px-4 py-2 bg-[#2F4731] text-white rounded-lg text-sm font-semibold hover:bg-[#1F3321] transition-colors flex items-center justify-center gap-2 group"
        >
          Start Deep Dive Study
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>}
      </div>
    );
  }

  return null;
}
