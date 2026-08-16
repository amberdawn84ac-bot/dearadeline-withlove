'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan } from '@/lib/brain-client';
import type { LearningPlanResponse } from '@/lib/brain-client';

export default function LearningPlanPage() {
  const { student } = useStudent();
  const [plan, setPlan] = useState<LearningPlanResponse | null>(null);
  const [error, setError] = useState('');

  const loadPlan = useCallback(async () => {
    if (!student?.id) return;
    try { setPlan(await getLearningPlan(student.id, 12)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The learning plan could not load.'); }
  }, [student?.id]);

  useEffect(() => { void loadPlan(); }, [loadPlan]);
  if (!student || (!plan && !error)) return <div className="p-10 text-center text-[#2F4731]/60">Building the larger roadmap…</div>;

  return (
    <div className="space-y-7 pb-12">
      <header className="rounded-[28px] border border-[#D9CFBC] bg-white/80 p-7">
        <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">The wider view</p>
        <h1 className="mt-1 text-4xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>My Learning Plan</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#2F4731]/65">Your longer path across interests, unfinished skills, projects, and graduation needs. Today is the zoomed-in itinerary.</p>
        <Link href="/dashboard" className="mt-5 inline-flex rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white">Open everything for today →</Link>
      </header>
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {plan && <>
        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><small className="font-bold uppercase text-[#BD6809]">Earned</small><p className="mt-2 text-3xl font-black text-[#2F4731]">{plan.total_credits_earned}</p><span className="text-xs text-[#2F4731]/55">credits recorded</span></div>
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><small className="font-bold uppercase text-[#BD6809]">This week</small><p className="mt-2 text-3xl font-black text-[#2F4731]">{plan.credits_this_week}</p><span className="text-xs text-[#2F4731]/55">credits added</span></div>
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><small className="font-bold uppercase text-[#BD6809]">Path ahead</small><p className="mt-2 text-3xl font-black text-[#2F4731]">{plan.suggestions.length}</p><span className="text-xs text-[#2F4731]/55">next opportunities</span></div>
        </section>
        <section><h2 className="mb-3 text-2xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Roadmap</h2><div className="grid gap-4 md:grid-cols-2">
          {plan.suggestions.map((item, index) => <article key={item.id} className="rounded-2xl border border-[#E7DAC3] bg-white p-5">
            <div className="flex items-center justify-between gap-3"><small className="font-black uppercase tracking-wider text-[#BD6809]">{index < 4 ? 'Today' : index < 8 ? 'Next' : 'Later'} · {item.track.replace(/_/g, ' ')}</small><span>{item.emoji}</span></div>
            <h3 className="mt-2 font-bold text-[#2F4731]">{item.title}</h3><p className="mt-1 text-sm leading-5 text-[#2F4731]/60">{item.description}</p>
            {item.personalization_reason && <p className="mt-3 border-t border-[#E7DAC3] pt-3 text-xs italic text-[#2F4731]/55">Why Adeline chose it: {item.personalization_reason}</p>}
            <Link href={`/dashboard/lesson/${encodeURIComponent(item.id)}`} className="mt-4 inline-flex rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white">Open assignment →</Link>
          </article>)}
        </div></section>
      </>}
    </div>
  );
}
