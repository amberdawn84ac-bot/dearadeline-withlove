'use client';

import { useEffect, useMemo, useState } from 'react';
import GenUIRenderer from '@/components/GenUIRenderer';
import type { LessonBlockResponse, LessonResponse } from '@/lib/brain-client';

type Message = { role: 'user' | 'assistant'; content: string };
type Standard = { code: string; description: string; grade_band: string; similarity: number };
type SpaceState = {
  title: string; status: 'active' | 'completed'; version: number;
  current_block_index: number; total_blocks: number; completed_block_ids: string[];
  current_block: LessonBlockResponse | null;
  current_lesson: { index: number; count: number; title: string; purpose?: string };
  learner_depth: { grade: number; band: string; tier: string; assignment: string };
  messages: Message[]; resource_triggers?: string[];
  breakout_data?: Record<string, Standard[]> | null;
  credited_this_session?: string[];
};

export default function SpacePlayer({ lesson, studentId, planItemId }: {
  lesson: LessonResponse; studentId: string; planItemId: string;
}) {
  const [space, setSpace] = useState<SpaceState | null>(null);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [creditedConcepts, setCreditedConcepts] = useState<string[]>([]);
  const encodedPath = useMemo(() => `${encodeURIComponent(studentId)}/${encodeURIComponent(planItemId)}`, [studentId, planItemId]);

  useEffect(() => {
    let cancelled = false;
    void fetch(`/brain/spaces/${encodedPath}`, { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error('Adeline could not open this Space yet.');
        return response.json() as Promise<SpaceState>;
      })
      .then((state) => { if (!cancelled) setSpace(state); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Could not open Space.'); });
    return () => { cancelled = true; };
  }, [encodedPath]);

  async function sendTurn() {
    if (!space || !message.trim() || sending) return;
    const submitted = message.trim();
    setMessage(''); setSending(true); setError('');
    try {
      const response = await fetch('/api/spaces/turn', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ studentId, planItemId, userMessage: submitted, expectedVersion: space.version }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Adeline could not hear that.');
      setSpace(result as SpaceState);
      if (result.credited_this_session?.length) {
        setCreditedConcepts((previous) => [...new Set([...previous, ...result.credited_this_session])]);
      }
    } catch (reason) {
      setMessage(submitted);
      setError(reason instanceof Error ? reason.message : 'Adeline could not hear that.');
    } finally { setSending(false); }
  }

  if (error && !space) return <p className="rounded-2xl bg-red-50 p-5 text-red-700" role="alert">{error}</p>;
  if (!space) return <p className="rounded-2xl border border-[#E7DAC3] bg-[#FDF6E9] p-5 italic text-[#2F4731]/70">Opening your saved Space…</p>;
  const progress = space.total_blocks ? Math.round((space.completed_block_ids.length / space.total_blocks) * 100) : 0;
  const lastAssistant = [...space.messages].reverse().find((item) => item.role === 'assistant');

  return <div className="space-y-6">
    <header className="rounded-[28px] border border-[#D8C9AB] bg-[#FFFDF8] p-6 shadow-sm">
      <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Unit Space · Lesson {space.current_lesson.index + 1} of {space.current_lesson.count}</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-3xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{space.title}</h1><p className="mt-1 text-[#2F4731]/70">{space.current_lesson.title}</p>{space.learner_depth.assignment && <p className="mt-2 max-w-3xl text-sm font-semibold text-[#2F4731]"><span className="uppercase tracking-wide text-[#BD6809]">Your {space.learner_depth.tier} work:</span> {space.learner_depth.assignment}</p>}</div><strong className="text-sm text-[#2F4731]">{progress}% explored</strong></div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#E9E1D2]"><div className="h-full bg-[#2F5A3A] transition-all" style={{ width: `${progress}%` }} /></div>
      <ol className="mt-4 flex flex-wrap gap-2" aria-label="Unit activities">{lesson.blocks.map((block, index) => <li key={block.block_id} className={`rounded-full px-3 py-1 text-xs font-bold ${index === space.current_block_index ? 'bg-[#2F5A3A] text-white' : space.completed_block_ids.includes(block.block_id) ? 'bg-[#DCE8D8] text-[#2F4731]' : 'bg-[#F2ECE1] text-[#2F4731]/55'}`}>{index + 1}. {block.title || block.experience_stage || 'Activity'}</li>)}</ol>
    </header>

    {space.current_block && <section className="rounded-[28px] border border-[#E7DAC3] bg-white p-4 sm:p-6"><GenUIRenderer lessonId={lesson.lesson_id} blocks={[space.current_block]} isHomestead={lesson.track === 'HOMESTEADING'} oasStandards={lesson.oas_standards} agentName={lesson.agent_name} studentId={studentId} /></section>}

    {space.breakout_data && <BreakoutTracks data={space.breakout_data} />}

    <section className="overflow-hidden rounded-[28px] border-2 border-[#2F5A3A] bg-[#FFF9ED]">
      <header className="bg-[#2F5A3A] px-5 py-4 text-white"><small className="uppercase tracking-[.18em] text-white/70">Learning companion</small><h2 className="text-xl">Adeline</h2></header>
      <div className="min-h-32 p-5"><p className="max-w-3xl rounded-2xl bg-white p-4 text-sm leading-6 text-[#2F4731] shadow-sm">{lastAssistant?.content || `We’ll work through “${space.current_lesson.title}” together. Tell me what you notice, tried, or need help with.`}</p></div>
      {space.status === 'completed' ? <div className="border-t border-[#E7DAC3] p-5">
        <p className="font-bold text-[#2F5A3A]">You reached the end of this unit Space.</p>
        {creditedConcepts.length > 0 ? <p className="mt-2 text-sm text-[#2F4731]">Adeline recorded mastery as you went, for: <strong>{creditedConcepts.join(', ')}</strong>. Check the Learning Map to see it reflected on the transcript.</p>
          : <p className="mt-2 text-sm text-[#2F4731]/70">No mastery was recorded this time through — Adeline only credits concepts once your answers are judged correct along the way. Feel free to revisit this Space to try again.</p>}
      </div> : <div className="flex gap-2 border-t border-[#E7DAC3] p-4"><label className="sr-only" htmlFor="space-message">Tell Adeline what you did or wondered</label><input id="space-message" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void sendTurn(); }} placeholder="Tell Adeline what you did, noticed, or want to learn…" className="min-w-0 flex-1 rounded-full border border-[#D8C9AB] bg-white px-4 py-3 text-sm text-[#2F4731]" disabled={sending} /><button type="button" onClick={() => void sendTurn()} disabled={sending || !message.trim()} className="rounded-full bg-[#2F5A3A] px-5 py-3 text-sm font-bold text-white disabled:opacity-40">{sending ? 'Thinking…' : 'Send'}</button></div>}
      {error && <p className="px-5 pb-4 text-sm text-red-700" role="alert">{error}</p>}
    </section>
  </div>;
}

function BreakoutTracks({ data }: { data: Record<string, Standard[]> }) {
  return <section className="rounded-[28px] border border-[#E7DAC3] bg-[#FDF6E9] p-5"><h2 className="text-2xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Ten-track breakout</h2><p className="mt-1 text-sm text-[#2F4731]/65">The shared investigation stays intact while each track shows only genuine Oklahoma standards connections.</p><div className="mt-4 grid gap-3 md:grid-cols-2">{Object.entries(data).map(([subject, standards]) => <article key={subject} className="rounded-2xl bg-white p-4"><h3 className="font-black text-[#2F4731]">{subject}</h3><div className="mt-2 space-y-2">{standards.length ? standards.map((standard) => <p key={standard.code} className="text-xs leading-5 text-[#2F4731]/75"><strong className="rounded bg-[#DCE8D8] px-2 py-1 text-[#2F4731]">{standard.code}</strong> {standard.description}</p>) : <p className="text-xs text-[#2F4731]/55">No strong standards match for this activity; this track is not forced.</p>}</div></article>)}</div></section>;
}
