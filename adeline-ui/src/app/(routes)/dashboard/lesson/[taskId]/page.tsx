'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import ClassroomPlayer from '@/components/classroom/ClassroomPlayer';
import { getSavedTodayPlan, getLearningPlan } from '@/lib/brain-client';
import { getClassroom, prepareClassroom, TRACKS, ClassroomRequest, ClassroomState, ClassroomTrack } from '@/lib/classroom-client';
import { useStudent } from '@/lib/useStudent';
import { selectPlannedTask } from './select-planned-task';

export function CanonicalExperiencePage({ view: _view = 'lesson' }: { view?: 'lesson' | 'space' }) {
  const params = useParams<{ taskId: string }>();
  const itemId = params.taskId;
  const { student, loading } = useStudent();
  const [state, setState] = useState<ClassroomState | null>(null);
  const [request, setRequest] = useState<ClassroomRequest>({ topic: '', track: 'CREATION_SCIENCE', level: 'Family ages 11–16', targets: [], materials: '', action: 'plan' });
  const [busy, setBusy] = useState(false);
  const [opening, setOpening] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!student?.id || !itemId) return;
    let active = true;
    setOpening(true); setError(''); setState(null);
    void (async () => {
      try {
        const saved = await getClassroom(student.id, itemId);
        if (!active) return;
        if (saved) { setState(saved); if (saved.request) setRequest(saved.request); return; }
        if (itemId.startsWith('new-')) return;
        const plan = await getSavedTodayPlan(student.id) ?? await getLearningPlan(student.id, 12);
        const { selected, requiredStandardCodes } = selectPlannedTask(plan, decodeURIComponent(itemId));
        if (active && selected) setRequest({ topic: selected.title, track: selected.track as ClassroomTrack, level: 'Family ages 11–16', targets: requiredStandardCodes, materials: '', action: 'plan' });
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : 'Could not open the classroom.'); }
      finally { if (active) setOpening(false); }
    })();
    return () => { active = false; };
  }, [student?.id, itemId]);
  useEffect(() => {
    if (state?.phase !== 'building' || !student?.id) return;
    let active = true;
    const timer = setInterval(() => {
      void getClassroom(student.id, itemId).then(result => { if (active && result) setState(result); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Could not check progress.'); });
    }, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [state?.phase, student?.id, itemId]);
  async function act(action: 'plan' | 'build') {
    if (!student || busy) return;
    setBusy(true); setError('');
    try { setState(await prepareClassroom(student.id, itemId, { ...request, action })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not prepare the classroom.'); }
    finally { setBusy(false); }
  }
  if (loading || opening) return <p role="status" className="p-10">Opening your classroom…</p>;
  if (!student) return <p className="p-10">Please sign in to open your classroom.</p>;
  return <div className="pb-12 text-[#183d32]">
    <Link href="/dashboard" className="mb-6 inline-block font-semibold">← Today</Link>
    {error && <p role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
    {state?.phase === 'ready' && state.classroom ? <ClassroomPlayer state={state} studentId={student.id} itemId={itemId} grade={student.gradeLevel ?? '8'} /> : <section className="mx-auto max-w-3xl rounded-3xl border border-[#d9cfbc] bg-[#fffdf7] p-7 md:p-10">
      <p className="text-xs uppercase tracking-[.2em]">Dear Adeline</p><h1 className="mt-3 text-4xl">A classroom worth walking into.</h1>
      {!state && <form onSubmit={e => { e.preventDefault(); void act('plan'); }} className="mt-7 grid gap-5">
        <label className="grid gap-2 font-semibold">What are we exploring?<input required minLength={3} maxLength={500} value={request.topic} onChange={e => setRequest(r => ({ ...r, topic: e.target.value }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal" placeholder="A question, a phenomenon, a skill, a career…" /></label>
        <label className="grid gap-2 font-semibold">Starting track<select value={request.track} onChange={e => setRequest(r => ({ ...r, track: e.target.value as ClassroomTrack }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal">{Object.entries(TRACKS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label className="grid gap-2 font-semibold">Learners<input value={request.level} maxLength={100} onChange={e => setRequest(r => ({ ...r, level: e.target.value }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal" /></label>
        <label className="grid gap-2 font-semibold">Materials we have<textarea rows={3} maxLength={2000} value={request.materials} onChange={e => setRequest(r => ({ ...r, materials: e.target.value }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal" placeholder="Optional: kitchen supplies, microscope, outdoor space…" /></label>
        <button disabled={busy} className="min-h-12 rounded-xl bg-[#183d32] p-4 font-semibold text-white disabled:opacity-50">{busy ? 'Adeline is planning…' : 'Plan our classroom'}</button>
      </form>}
      {state?.plan && <div className="mt-7 space-y-5"><h2 className="text-2xl">{state.plan.title}</h2><p className="text-lg">{state.plan.essential_question}</p><p>{state.plan.understanding}</p><ol className="list-decimal space-y-3 pl-5">{state.plan.scenes?.map(scene => <li key={scene.id}><b>{scene.title}</b><p className="mt-1 text-sm leading-6">{scene.objective}</p></li>)}</ol><p><b>What they’ll show:</b> {state.plan.demonstration}</p></div>}
      {state?.phase === 'planned' && <button onClick={() => void act('build')} disabled={busy} className="mt-7 min-h-12 rounded-xl bg-[#183d32] px-6 py-3 text-white disabled:opacity-50">{busy ? 'Starting…' : 'Build this classroom'}</button>}
      {state?.phase === 'building' && <p role="status" className="mt-7 rounded-xl bg-[#f2ead7] p-5">Building the classroom, one scene at a time. {state.built_scenes ?? 0} scenes saved. You can return to this page.</p>}
      {state?.phase === 'failed' && <div className="mt-7"><p role="alert">{state.error}</p><button onClick={() => void act('build')} disabled={busy} className="mt-4 rounded-xl bg-[#183d32] px-6 py-3 text-white">Resume classroom</button></div>}
    </section>}
  </div>;
}
export default CanonicalExperiencePage;
