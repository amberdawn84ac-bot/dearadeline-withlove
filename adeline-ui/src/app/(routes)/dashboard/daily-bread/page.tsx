'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { BookOpen, Loader2 } from 'lucide-react';
import { useStudent } from '@/lib/useStudent';

interface DailyBread {
  forDate: string;
  verse: string;
  reference: string;
  original: string;
  originalMeaning: string;
  translationNote?: string;
  context: string;
  lessonTitle: string;
  bigIdea: string;
  readTogether: string[];
  familyDiscussion: string[];
  prayer: string;
  creditConnections: string[];
  portfolioEvidence: string[];
  originalText?: string;
  sourceVersion?: string;
  sourceUrl?: string;
  isFoxTranslation?: boolean;
  sourceTranslation?: string;
  translationLabel?: string;
}

interface DeepDive {
  fox_text?: string;
  hebrew_text?: string;
  is_fox: boolean;
  direct_translation?: string;
  source_version?: string;
  sefaria_url?: string;
  sections: Array<{ heading: string; content: string }>;
}

export default function DailyBreadLessonPage() {
  const { student } = useStudent();
  const [bread, setBread] = useState<DailyBread | null>(null);
  const [study, setStudy] = useState<DeepDive | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!student) return;
    let cancelled = false;
    void (async () => {
      try {
        const dailyResponse = await fetch('/brain/daily-bread', { cache: 'no-store' });
        if (!dailyResponse.ok) throw new Error('Today’s Daily Bread could not load.');
        const daily: DailyBread = await dailyResponse.json();
        if (cancelled) return;
        setBread(daily);
        const deepResponse = await fetch('/brain/daily-bread/deep-dive', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            reference: daily.reference,
            original: daily.original,
            original_meaning: daily.originalMeaning,
            context: daily.context,
            grade_level: student.gradeLevel,
          }),
        });
        if (!deepResponse.ok) throw new Error('The deep-dive study could not load.');
        const deep: DeepDive = await deepResponse.json();
        if (!cancelled) setStudy(deep);
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Daily Bread could not load.');
      }
    })();
    return () => { cancelled = true; };
  }, [student]);

  if (!bread && !error) return <div className="flex min-h-80 items-center justify-center gap-3 text-[#2F4731]/60"><Loader2 className="h-5 w-5 animate-spin" /> Opening today&apos;s Bible lesson…</div>;
  if (error && !bread) return <div className="rounded-2xl bg-red-50 p-6 text-red-700">{error}</div>;

  return bread && <div className="mx-auto max-w-4xl space-y-6 pb-16">
    <Link href="/dashboard" className="inline-flex text-sm font-bold text-[#2F4731]">← Back to today</Link>
    <header className="rounded-[28px] border border-[#E7DAC3] bg-[#FFFDF5] p-7 md:p-10">
      <div className="flex items-center gap-3 text-[#BD6809]"><BookOpen className="h-5 w-5" /><span className="text-xs font-black uppercase tracking-[.18em]">Daily Bread · Family Bible Lesson</span></div>
      <h1 className="mt-4 text-4xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{bread.lessonTitle}</h1>
      <p className="mt-3 text-lg font-semibold leading-7 text-[#2F4731]/75">{bread.bigIdea}</p>
      <p className="mt-2 font-bold text-[#BD6809]">{bread.reference}</p>
      {(study?.sefaria_url || bread.sourceUrl) && <a href={study?.sefaria_url || bread.sourceUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-xs font-semibold text-[#2F4731]/60 underline">Source record via Sefaria ↗</a>}
    </header>

    {(study?.hebrew_text || bread.originalText) && <section className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><p className="text-xs font-black uppercase tracking-wide text-[#BD6809]">Source text · Masoretic Hebrew</p><p dir="rtl" className="mt-3 text-2xl leading-10 text-[#2F4731]">{study?.hebrew_text || bread.originalText}</p><p className="mt-3 text-xs text-[#2F4731]/55">This is the surviving Hebrew source tradition used for the close rendering; it is shown separately from translation and interpretation.</p></section>}

    <section className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><p className="text-xs font-black uppercase tracking-wide text-[#BD6809]">{bread.translationLabel || 'Close rendering from the source text'}</p><blockquote className="mt-3 border-l-4 border-[#BD6809] pl-5 text-lg leading-8 text-[#2F4731]">“{study?.direct_translation || bread.verse}”</blockquote><p className="mt-3 text-xs text-[#2F4731]/55">This close rendering is labeled separately from the surviving source text and from any published translation.</p></section>

    {(study?.is_fox && study.fox_text) || (bread.isFoxTranslation && bread.sourceTranslation) ? <section className="rounded-2xl border border-[#E7DAC3] bg-[#FFFDF5] p-6"><p className="text-xs font-black uppercase tracking-wide text-[#BD6809]">Everett Fox comparison</p><p className="mt-3 text-base leading-7 text-[#2F4731]">{study?.fox_text || bread.sourceTranslation}</p><p className="mt-3 text-xs text-[#2F4731]/55">Published translation: {study?.source_version || bread.sourceVersion || 'Everett Fox edition'}.</p></section> : null}

    <section className="grid gap-4 md:grid-cols-2">
      <article className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><p className="text-xs font-black uppercase text-[#BD6809]">Key word</p><h2 className="mt-2 text-xl font-bold text-[#2F4731]">{bread.original}</h2><p className="mt-3 text-sm leading-6 text-[#2F4731]/70">{bread.originalMeaning}</p></article>
      <article className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><p className="text-xs font-black uppercase text-[#BD6809]">Context</p><p className="mt-3 text-sm leading-6 text-[#2F4731]/70">{bread.context}</p>{bread.translationNote && <p className="mt-3 text-sm italic leading-6 text-[#2F4731]/60">{bread.translationNote}</p>}</article>
    </section>

    {study ? <section className="space-y-4">{study.sections.map((section) => <article key={section.heading} className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><h2 className="text-2xl font-bold text-[#2F4731]">{section.heading}</h2><p className="mt-3 whitespace-pre-line text-sm leading-7 text-[#2F4731]/75">{section.content}</p></article>)}</section> : error ? <div className="rounded-2xl bg-amber-50 p-5 text-sm text-amber-800">{error} The sourced passage and family lesson are still available below.</div> : <div className="flex items-center gap-3 rounded-2xl bg-[#FFF8EC] p-5 text-sm text-[#2F4731]/65"><Loader2 className="h-4 w-4 animate-spin" /> Building the deeper study from the source text…</div>}

    <section className="rounded-2xl border border-[#E7DAC3] bg-[#FFFDF5] p-6"><h2 className="text-2xl font-bold text-[#2F4731]">Read and discuss together</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[#2F4731]/75">{bread.readTogether.map((item) => <li key={item}>{item}</li>)}</ul><ol className="mt-5 list-decimal space-y-3 pl-5 text-sm text-[#2F4731]/75">{bread.familyDiscussion.map((item) => <li key={item}>{item}</li>)}</ol></section>
    <section className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><p className="text-xs font-black uppercase text-[#BD6809]">Portfolio and credit</p><p className="mt-2 text-sm font-bold text-[#2F4731]">{bread.creditConnections.map((track) => track.replace(/_/g, ' ')).join(' · ')}</p><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[#2F4731]/70">{bread.portfolioEvidence.map((item) => <li key={item}>{item}</li>)}</ul></section>
  </div>;
}
