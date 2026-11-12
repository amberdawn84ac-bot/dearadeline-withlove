'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import ClassroomPlayer from '@/components/classroom/ClassroomPlayer';
import LearnerPreferences from '@/components/classroom/LearnerPreferences';
import { getSavedTodayPlan, getLearningPlan } from '@/lib/brain-client';
import { ClassroomRequestError, ESTUARY_ITEM, ESTUARY_TITLE, getClassroom, prepareClassroom, TRACKS, ClassroomRequest, ClassroomState, ClassroomTrack } from '@/lib/classroom-client';
import { useStudent } from '@/lib/useStudent';
import { selectPlannedTask } from './select-planned-task';

export function CanonicalExperiencePage({ view: _view = 'lesson' }: { view?: 'lesson' | 'space' }) {
  const { taskId } = useParams<{ taskId: string }>();
  const { student, loading } = useStudent();
  if (loading) return <p role="status" className="p-10">Opening your exploration…</p>;
  if (!student) return <p className="p-10">Please sign in to continue exploring.</p>;
  return <StudentExperience key={`${student.id}:${taskId}`} student={student} itemId={taskId} />;
}

function StudentExperience({ student, itemId }: { student: NonNullable<ReturnType<typeof useStudent>['student']>; itemId: string }) {
  const [state, setState] = useState<ClassroomState | null>(null);
  const [request, setRequest] = useState<ClassroomRequest>({ topic: '', track: 'CREATION_SCIENCE', level: '', targets: [], materials: '', action: 'plan' });
  const [busy, setBusy] = useState(false);
  const [opening, setOpening] = useState(true);
  const [error, setError] = useState('');
  const [retryAt, setRetryAt] = useState(0);
  const retryTime = Math.max(retryAt, (state?.retry_at ?? 0) * 1000);
  const [clock, setClock] = useState(() => Date.now());
  const waitingToRetry = retryTime > clock;
  const isEstuary = itemId === ESTUARY_ITEM;
  useEffect(() => {
    if (!waitingToRetry) return;
    const timer = setTimeout(() => setClock(Date.now()), Math.max(0, retryTime - Date.now()) + 50);
    return () => clearTimeout(timer);
  }, [waitingToRetry, retryTime, clock]);
  useEffect(() => {
    if (!itemId) return;
    let active = true;
    setOpening(true); setError(''); setState(null); setRetryAt(0); setClock(Date.now());
    void (async () => {
      try {
        const saved = await getClassroom(student.id, itemId);
        if (!active) return;
        if (saved) { setState(saved); if (saved.request) setRequest(saved.request); return; }
        if (isEstuary) {
          setRequest({ topic: ESTUARY_TITLE, track: 'CREATION_SCIENCE', level: 'family', targets: [], materials: '', action: 'plan' });
          return;
        }
        setRequest(current => ({ ...current, level: student.gradeLevel ?? '' }));
        if (itemId.startsWith('new-')) {
          const query = new URLSearchParams(window.location.search);
          const topic = query.get('topic'); const target = query.get('target'); const track = query.get('track');
          if (topic && track && track in TRACKS) setRequest({ topic: topic.slice(0, 500), track: track as ClassroomTrack, level: student.gradeLevel ?? '', targets: target ? [target] : [], materials: '', action: 'plan' });
          return;
        }
        const plan = await getSavedTodayPlan(student.id) ?? await getLearningPlan(student.id, 12);
        const { selected, requiredStandardCodes } = selectPlannedTask(plan, decodeURIComponent(itemId));
        if (active && selected) setRequest({ topic: selected.title, track: selected.track as ClassroomTrack, level: selected.grade_band || student.gradeLevel || '', targets: requiredStandardCodes, materials: '', learning_need: selected.description?.slice(0, 2000), action: 'plan' });
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : 'Could not open your exploration.'); }
      finally { if (active) setOpening(false); }
    })();
    return () => { active = false; };
  }, [student?.id, student?.gradeLevel, itemId, isEstuary]);
  useEffect(() => {
    if (state?.phase !== 'building' || !student?.id) return;
    let active = true;
    const timer = setInterval(() => {
      void getClassroom(student.id, itemId).then(result => { if (active && result) setState(result); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Could not check progress.'); });
    }, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [state?.phase, student?.id, itemId]);
  async function act(action: 'plan' | 'build') {
    if (!student || busy || waitingToRetry) return;
    setBusy(true); setError(''); setRetryAt(0); setClock(Date.now());
    try { setState(await prepareClassroom(student.id, itemId, { ...request, action })); }
    catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not prepare your exploration.');
      if (reason instanceof ClassroomRequestError && reason.retryAt) setRetryAt(reason.retryAt);
    }
    finally { setBusy(false); }
  }
  if (opening) return <p role="status" className="p-10">Opening your exploration…</p>;
  return <div className="pb-12 text-[#183d32]">
    <Link href="/dashboard" className="mb-6 inline-block font-semibold">← Today</Link>
    {error && <p role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
    {waitingToRetry && <p role="status" className="mb-5">You can try again after {new Date(retryTime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}.</p>}
    {state?.phase === 'ready' && state.classroom ? <ClassroomPlayer state={state} studentId={student.id} itemId={itemId} grade={student.gradeLevel ?? '8'} /> : <section className="mx-auto max-w-3xl rounded-3xl border border-[#d9cfbc] bg-[#fffdf7] p-7 md:p-10">
      <p className="text-xs uppercase tracking-[.2em]">Dear Adeline</p><h1 className="mt-3 text-4xl">{isEstuary ? ESTUARY_TITLE : 'What do you want to explore or learn about?'}</h1>
      {!state && isEstuary && <div className="mt-7 space-y-4">
        <p>Investigate why water can settle into layers, then use what you find to plan an estuary field measurement.</p>
        <button disabled={busy || waitingToRetry} onClick={() => void act('plan')} className="min-h-12 rounded-xl bg-[#183d32] px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? 'Opening…' : 'Open the family lab'}</button>
      </div>}
      {!state && !isEstuary && <form onSubmit={e => { e.preventDefault(); void act('plan'); }} className="mt-7 grid gap-5">
        <label className="grid gap-2 font-semibold">What are we exploring?<input required minLength={3} maxLength={500} value={request.topic} onChange={e => setRequest(r => ({ ...r, topic: e.target.value }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal" placeholder="A question, a phenomenon, a skill, a career…" /></label>
        <label className="grid gap-2 font-semibold">Starting track<select value={request.track} onChange={e => setRequest(r => ({ ...r, track: e.target.value as ClassroomTrack }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal">{Object.entries(TRACKS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label className="grid gap-2 font-semibold">Learners<input value={request.level} maxLength={100} onChange={e => setRequest(r => ({ ...r, level: e.target.value, learner_context: undefined }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal" /></label>
        <LearnerPreferences value={request.learner_context ?? undefined} onChange={context => setRequest(current => ({ ...current, learner_context: context }))} />
        <label className="grid gap-2 font-semibold">Materials we have<textarea rows={3} maxLength={2000} value={request.materials} onChange={e => setRequest(r => ({ ...r, materials: e.target.value }))} className="rounded-xl border border-[#c9bfa9] bg-white p-4 font-normal" placeholder="Optional: kitchen supplies, microscope, outdoor space…" /></label>
        <button disabled={busy || waitingToRetry} className="min-h-12 rounded-xl bg-[#183d32] p-4 font-semibold text-white disabled:opacity-50">{busy ? 'Adeline is planning…' : 'Plan our exploration'}</button>
      </form>}
      {state?.plan && <div className="mt-7 space-y-5"><h2 className="text-2xl">{state.plan.title}</h2><p className="text-lg">{state.plan.essential_question}</p><p>{state.plan.understanding}</p><ol className="list-decimal space-y-3 pl-5">{state.plan.scenes?.map(scene => <li key={scene.id}><b>{scene.title}</b><p className="mt-1 text-sm leading-6">{scene.objective}</p></li>)}</ol><p><b>What they’ll show:</b> {state.plan.demonstration}</p></div>}
      {state?.phase === 'planned' && <button onClick={() => void act('build')} disabled={busy || waitingToRetry} className="mt-7 min-h-12 rounded-xl bg-[#183d32] px-6 py-3 text-white disabled:opacity-50">{busy ? 'Starting…' : 'Let’s explore'}</button>}
      {state?.phase === 'building' && <p role="status" className="mt-7 rounded-xl bg-[#f2ead7] p-5">Adeline is preparing your exploration. {state.built_scenes ?? 0} scenes saved. You can return to this page.</p>}
      {state?.phase === 'failed' && <div className="mt-7"><p role="alert">{state.error}</p><button onClick={() => void act('build')} disabled={busy || waitingToRetry} className="mt-4 rounded-xl bg-[#183d32] px-6 py-3 text-white disabled:opacity-50">Resume preparing</button></div>}
    </section>}
  </div>;
}
export default CanonicalExperiencePage;
