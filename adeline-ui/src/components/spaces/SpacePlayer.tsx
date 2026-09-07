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
  const [error, setError] = useState('');
  const [creditedConcepts, setCreditedConcepts] = useState<string[]>([]);
  const encodedPath = useMemo(() => `${encodeURIComponent(studentId)}/${encodeURIComponent(planItemId)}`, [studentId, planItemId]);

  useEffect(() => {
    let cancelled = false;
    const openSpace = async () => {
      for (let attempt = 0; attempt < 20 && !cancelled; attempt += 1) {
        const response = await fetch(`/brain/spaces/${encodedPath}`, { cache: 'no-store' });
        if (response.ok) return response.json() as Promise<SpaceState>;
        // A newly authored experience can be saved a moment before its Space
        // session is created. Treat that conflict as a brief loading state.
        if (response.status !== 409) throw new Error('Adeline could not open this Space yet.');
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      throw new Error('Adeline could not open this Space yet.');
    };
    void openSpace()
      .then((state) => { if (!cancelled) setSpace(state); })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Could not open Space.'); });
    return () => { cancelled = true; };
  }, [encodedPath]);

  useEffect(() => {
    function receiveSpaceUpdate(event: Event) {
      const detail = (event as CustomEvent<{ planItemId: string; state: SpaceState }>).detail;
      if (detail?.planItemId === planItemId) {
        setSpace(detail.state);
        if (detail.state.credited_this_session?.length) {
          setCreditedConcepts((previous) => [
            ...new Set([...previous, ...detail.state.credited_this_session!]),
          ]);
        }
        setError('');
      }
    }
    window.addEventListener('adeline:space-updated', receiveSpaceUpdate);
    return () => window.removeEventListener('adeline:space-updated', receiveSpaceUpdate);
  }, [planItemId]);

  if (error && !space) return <p className="rounded-2xl bg-red-50 p-5 text-red-700" role="alert">{error}</p>;
  if (!space) return <p className="rounded-2xl border border-[#E7DAC3] bg-[#FDF6E9] p-5 italic text-[#2F4731]/70">Opening your saved Space…</p>;
  const progress = space.total_blocks ? Math.round((space.completed_block_ids.length / space.total_blocks) * 100) : 0;

  return <div className="space-y-6">
    {space.current_block && <section className="rounded-[28px] border border-[#E7DAC3] bg-white p-4 sm:p-6"><GenUIRenderer lessonId={lesson.lesson_id} blocks={[space.current_block]} isHomestead={lesson.track === 'HOMESTEADING'} oasStandards={lesson.oas_standards} agentName={lesson.agent_name} studentId={studentId} /></section>}

    <div className="px-1" aria-label={`${progress}% of this unit explored`}>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#E9E1D2]"><div className="h-full bg-[#2F5A3A] transition-all" style={{ width: `${progress}%` }} /></div>
    </div>

    {space.breakout_data && <BreakoutTracks data={space.breakout_data} />}
    {space.status === 'completed' && <div className="rounded-2xl border border-[#D8C9AB] bg-[#FDF6E9] p-5">
        <p className="font-bold text-[#2F5A3A]">You reached the end of this unit Space.</p>
        {creditedConcepts.length > 0 ? <p className="mt-2 text-sm text-[#2F4731]">Adeline recorded mastery as you went, for: <strong>{creditedConcepts.join(', ')}</strong>. Check the Learning Map to see it reflected on the transcript.</p>
          : <p className="mt-2 text-sm text-[#2F4731]/70">No mastery was recorded this time through — Adeline only credits concepts once your answers are judged correct along the way. Feel free to revisit this Space to try again.</p>}
        <p className="mt-2 text-xs italic text-[#2F4731]/60">This Space stays open. Use the Adeline chat above if you have more questions or want to explore further.</p>
      </div>}
  </div>;
}

function BreakoutTracks({ data }: { data: Record<string, Standard[]> }) {
  return <section className="rounded-[28px] border border-[#E7DAC3] bg-[#FDF6E9] p-5"><h2 className="text-2xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Ten-track breakout</h2><p className="mt-1 text-sm text-[#2F4731]/65">The shared investigation stays intact while each track shows only genuine Oklahoma standards connections.</p><div className="mt-4 grid gap-3 md:grid-cols-2">{Object.entries(data).map(([subject, standards]) => <article key={subject} className="rounded-2xl bg-white p-4"><h3 className="font-black text-[#2F4731]">{subject}</h3><div className="mt-2 space-y-2">{standards.length ? standards.map((standard) => <p key={standard.code} className="text-xs leading-5 text-[#2F4731]/75"><strong className="rounded bg-[#DCE8D8] px-2 py-1 text-[#2F4731]">{standard.code}</strong> {standard.description}</p>) : <p className="text-xs text-[#2F4731]/55">No strong standards match for this activity; this track is not forced.</p>}</div></article>)}</div></section>;
}
