'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan } from '@/lib/brain-client';
import type { LearningPlanResponse } from '@/lib/brain-client';

type View = 'month' | 'year' | 'graduation';
const pretty = (value: string) => value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function LearningPlanPage() {
  const { student } = useStudent();
  const [plan, setPlan] = useState<LearningPlanResponse | null>(null);
  const [view, setView] = useState<View>('month');
  const [error, setError] = useState('');
  const loadPlan = useCallback(async () => {
    if (!student?.id) return;
    try { setPlan(await getLearningPlan(student.id, 12)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The learning plan could not load.'); }
  }, [student?.id]);
  useEffect(() => { void loadPlan(); }, [loadPlan]);
  if (!student || (!plan && !error)) return <div className="p-10 text-center text-[#2F4731]/60">Building the larger roadmap…</div>;
  const firstMonth = plan?.roadmap.months[0];

  return <div className="space-y-7 pb-12">
    <header className="rounded-[28px] border border-[#D9CFBC] bg-white/80 p-7">
      <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">The wider view</p>
      <h1 className="mt-1 text-4xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>My Learning Plan</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[#2F4731]/65">A living 36-week, four-day forecast—not a locked syllabus. The near term is specific; later months shift as interests, mastery, pace, completed evidence, and graduation needs change.</p>
      <Link href="/dashboard" className="mt-5 inline-flex rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white">Open today →</Link>
    </header>
    {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {plan && <>
      {plan.placement.placement_required && <section className="rounded-2xl border border-[#D6A64B] bg-[#FFF8E8] p-5"><p className="text-xs font-black uppercase tracking-wide text-[#BD6809]">Grade discovery in progress</p><h2 className="mt-2 text-xl font-bold text-[#2F4731]">Working at grade {plan.placement.working_grade === 'K' ? 'K' : plan.placement.working_grade} for now</h2><p className="mt-2 text-sm leading-6 text-[#2F4731]/70">{plan.placement.reason} Adeline should adjust individual subjects as Jack demonstrates what he already knows; this working grade is not a permanent label.</p></section>}
      <section className="grid gap-4 sm:grid-cols-3">
        <Stat label="This month" value={`${firstMonth?.weeks.length ?? 0} weeks`} note="four school days each week" />
        <Stat label="This year" value={`${plan.roadmap.total_weeks} weeks`} note={`adaptive ${plan.roadmap.school_days_per_week}-day forecast`} />
        <Stat label="Credits earned" value={String(plan.total_credits_earned)} note={plan.graduation_progress.is_high_school ? `${plan.graduation_progress.credits_remaining} still required` : 'evidence recorded automatically'} />
      </section>
      <nav className="flex flex-wrap gap-2" aria-label="Roadmap view">{(['month', 'year', 'graduation'] as View[]).map((item) => <button key={item} onClick={() => setView(item)} className={`rounded-full px-5 py-2 text-sm font-bold ${view === item ? 'bg-[#BD6809] text-white' : 'border border-[#D9CFBC] bg-white text-[#2F4731]'}`}>{item === 'graduation' ? 'Graduation & credits' : `The ${item}`}</button>)}</nav>
      {view === 'month' && firstMonth && <section className="space-y-4"><h2 className="text-2xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{firstMonth.label}: {firstMonth.focus}</h2>{firstMonth.weeks.map((week) => <article key={week.week} className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><h3 className="font-bold text-[#2F4731]">Week {week.week} · {week.theme}</h3><div className="mt-3 grid gap-3 md:grid-cols-4">{week.days.map((day) => <Link key={day.date} href={`/dashboard/lesson/${encodeURIComponent(day.lesson_id)}`} className="rounded-xl bg-[#FFF8EC] p-3 hover:ring-2 hover:ring-[#BD6809]/30"><small className="font-black uppercase text-[#BD6809]">{day.day}</small><p className="mt-1 text-sm font-bold text-[#2F4731]">{day.emoji} {day.title}</p><span className="text-[11px] text-[#2F4731]/50">{pretty(day.track)}</span></Link>)}</div></article>)}</section>}
      {view === 'year' && <section><p className="mb-4 rounded-xl bg-[#FFF8EC] p-4 text-sm text-[#2F4731]/70">Later months are directional forecasts. Adeline recalculates them from real learning rather than forcing a child to keep pace with an obsolete plan.</p><div className="grid gap-4 md:grid-cols-3">{plan.roadmap.months.map((month) => <article key={month.month} className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><small className="font-black uppercase text-[#BD6809]">{month.label} · {month.month === 1 ? 'current plan' : 'forecast'}</small><h3 className="mt-2 font-bold text-[#2F4731]">{month.focus}</h3><p className="mt-2 text-sm text-[#2F4731]/60">Weeks {month.weeks[0].week}–{month.weeks.at(-1)?.week} · flexible sequence</p><ul className="mt-3 space-y-1 text-xs text-[#2F4731]/65">{month.weeks.map((week) => <li key={week.week}>Week {week.week}: {week.theme}</li>)}</ul></article>)}</div></section>}
      {view === 'graduation' && <section className="rounded-2xl border border-[#E7DAC3] bg-white p-6"><h2 className="text-2xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{plan.graduation_progress.is_high_school ? 'What remains for graduation' : 'Foundations now, graduation record later'}</h2>{plan.graduation_progress.is_high_school ? <div className="mt-5 space-y-4">{plan.credit_gaps.map((gap) => { const percent = gap.required ? Math.min(100, gap.earned / gap.required * 100) : 0; return <div key={gap.bucket}><div className="flex justify-between text-sm"><strong className="text-[#2F4731]">{pretty(gap.bucket)}</strong><span className="text-[#2F4731]/60">{gap.earned} / {gap.required} · {gap.remaining} remaining</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-[#E7DAC3]"><div className="h-full bg-[#BD6809]" style={{ width: `${percent}%` }} /></div></div>})}</div> : <p className="mt-3 text-sm leading-6 text-[#2F4731]/65">Adeline tracks mastered standards and portfolio evidence now. High-school requirements appear here automatically when credit-bearing work begins.</p>}</section>}
    </>}
  </div>;
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><small className="font-bold uppercase text-[#BD6809]">{label}</small><p className="mt-2 text-3xl font-black text-[#2F4731]">{value}</p><span className="text-xs text-[#2F4731]/55">{note}</span></div>;
}
