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
          className="w-full px-4 py-2 bg-[#2F4731] text-white rounded-lg text-sm font-semibold hover:bg-[#1F3321] transition-colors flex items-center justify-center gap-2 group"
        >
          Start Deep Dive Study
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    );
  }

  return null;
}
