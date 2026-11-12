'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import ActivityLab from './ActivityLab';
import SceneVisual, { LessonImage } from './SceneVisual';
import LearningReviewPanel from './LearningReview';
import { ActivityWork, ClassroomScene, ClassroomState, Feedback, ClassroomTurn, SceneMaterial, getSceneMaterials, reviewClassroomResponse, talkToClassroom, submitClassroomResponse } from '@/lib/classroom-client';
import { matterMenu } from '@/lib/classroom-models';

function sortingChoices(response: string): Record<string, string> {
  try {
    const value: unknown = JSON.parse(response || '{}');
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return Object.fromEntries(Object.entries(value).filter(([, category]) => typeof category === 'string'));
    }
  } catch { /* A non-sorting response has no classifications. */ }
  return {};
}

function SortingActivity({ scene, response, onChange, disabled }: { scene: ClassroomScene; response: string; onChange: (value: string) => void; disabled: boolean }) {
  const choices = sortingChoices(response);
  const spec = scene.sorting!;
  return <section aria-label="Sorting activity" className="my-6 space-y-4 rounded-2xl bg-[#f2ead7] p-5">
    <p className="text-lg font-semibold">{spec.instruction}</p>
    <p className="text-sm">Choose a category for each item. You can change your choices before checking.</p>
    {spec.items.map(item => <label key={item.id} className="grid gap-2 rounded-xl bg-white p-4 sm:grid-cols-2 sm:items-center">
      <span>{item.label}</span>
      <select aria-label={`Category for ${item.label}`} disabled={disabled} value={choices[item.id] ?? ''} onChange={e => onChange(JSON.stringify({ ...choices, [item.id]: e.target.value }))} className="min-h-11 rounded-lg border border-[#c9bfa9] bg-white p-3">
        <option value="">Choose a category</option>{spec.categories.map(category => <option key={category.id} value={category.id}>{category.label}</option>)}
      </select>
    </label>)}
  </section>;
}

export default function ClassroomPlayer({ state, studentId, itemId, grade }: { state: ClassroomState; studentId: string; itemId: string; grade: string }) {
  const classroom = state.classroom!;
  const [index, setIndex] = useState(0);
  const [focus, setFocus] = useState<string | null>(null);
  const [narratedNode, setNarratedNode] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [annotation, setAnnotation] = useState<string | null>(null);
  const [narrationText, setNarrationText] = useState('');
  const [revealed, setRevealed] = useState<Record<string, string[]>>({});
  const [narrationIndex, setNarrationIndex] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [paused, setPaused] = useState(false);
  const [activityDirty, setActivityDirty] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const narrationToken = useRef(0);
  const restoredScene = useRef<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const scene = classroom.scenes[index];
  const hiddenVisualIds = scene.actions
    .filter(action => action.kind === 'reveal' && action.target_id && !revealed[scene.id]?.includes(action.target_id))
    .map(action => action.target_id!);
  // Teacher actions are the spoken narration, not a second written lesson.
  const discussionActions = scene.actions.filter(action =>
    classroom.blueprint.roster.some(role => role.id === action.role_id && role.role !== 'teacher'),
  );
  const [materialsByScene, setMaterialsByScene] = useState<Record<string, SceneMaterial[]>>({});
  const [materialErrors, setMaterialErrors] = useState<Record<string, string>>({});
  const materialRequests = useRef(new Set<string>());
  const [materialLoading, setMaterialLoading] = useState<Record<string, boolean>>({});
  const pageMaterials = materialsByScene[scene.id] ?? scene.resources ?? [];
  const promisesMaterial = discussionActions.some(action => /\b(?:prepared|displayed|i(?:'|’)ve got|i have|i(?:'|’)ve brought)\b/i.test(action.text));
  const loadMaterials = useCallback(async (sceneId: string) => {
    if (materialRequests.current.has(sceneId)) return;
    materialRequests.current.add(sceneId);
    setMaterialLoading(current => ({ ...current, [sceneId]: true }));
    setMaterialErrors(current => ({ ...current, [sceneId]: '' }));
    try {
      const resources = await getSceneMaterials(studentId, itemId, sceneId);
      setMaterialsByScene(current => ({ ...current, [sceneId]: resources }));
    } catch (reason) {
      setMaterialErrors(current => ({ ...current, [sceneId]: reason instanceof Error ? reason.message : 'These materials could not be loaded.' }));
      materialRequests.current.delete(sceneId);
    } finally {
      setMaterialLoading(current => ({ ...current, [sceneId]: false }));
    }
  }, [studentId, itemId]);
  useEffect(() => {
    if (promisesMaterial && !pageMaterials.length && !materialErrors[scene.id]) void loadMaterials(scene.id);
  }, [scene.id, promisesMaterial, pageMaterials.length, loadMaterials, materialErrors]);
  const [response, setResponse] = useState('');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef<{ text: string; key: string } | null>(null);
  const [saved, setSaved] = useState(state.responses ?? {});
  const [speechAvailable, setSpeechAvailable] = useState(false);
  const [dialogue, setDialogue] = useState<Record<string, ClassroomTurn[]>>(state.dialogue ?? {});
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const questionKey = useRef<{ text: string; key: string } | null>(null);
  async function ask(message = question) {
    if (!message.trim() || asking) return;
    setAsking(true); setError('');
    if (questionKey.current?.text !== message) questionKey.current = { text: message, key: crypto.randomUUID() };
    try {
      const turn = await talkToClassroom(studentId, itemId, scene.id, message, questionKey.current.key);
      setDialogue(current => ({ ...current, [scene.id]: [...(current[scene.id] ?? []).filter(t => t.key !== turn.key), turn] }));
      if (message === question) setQuestion('');
      questionKey.current = null;
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Adeline could not reply. Your message is still here.'); }
    finally { setAsking(false); }
  }
  let sortingComplete = true;
  if (scene.sorting) {
    const choices = sortingChoices(response);
    sortingComplete = scene.sorting.items.every(item => scene.sorting!.categories.some(c => c.id === choices[item.id]));
  }
  const hasLab = !!(scene.interaction || scene.simulation);
  const dirty = activityDirty || (!hasLab && response !== (saved[scene.id]?.text ?? ''));
  const attemptPending = scene.response_required && !saved[scene.id];
  const workingGrade = state.request?.learner_context?.working_grade || grade;
  const numericGrade = workingGrade.toUpperCase() === 'K' ? 0 : Number.parseInt(workingGrade, 10);
  const band = numericGrade <= 5 ? 'elementary' : numericGrade <= 8 ? 'middle' : 'high_school';
  useEffect(() => { setSpeechAvailable('speechSynthesis' in window); return () => window.speechSynthesis?.cancel(); }, []);
  useEffect(() => {
    if (restoredScene.current === scene.id) return;
    const moved = restoredScene.current !== null;
    restoredScene.current = scene.id;
    if (moved) {
      heading.current?.focus({ preventScroll: true });
      heading.current?.scrollIntoView?.({ block: 'start' });
    }
    narrationToken.current += 1; setShowTranscript(false);
    setFocus(null); setNarratedNode(null); setHighlightId(null); setAnnotation(null); setNarrationIndex(0); setSpeaking(false); setPaused(false); setActivityDirty(false);
    setNarrationText('');
    setQuestion(''); questionKey.current = null;
    setResponse(saved[scene.id]?.text ?? ''); setFeedback(saved[scene.id]?.feedback ?? null); setError(''); pending.current = null;
    window.speechSynthesis?.cancel();
  }, [scene.id, saved]);
  function stopNarration() {
    narrationToken.current += 1;
    window.speechSynthesis?.cancel(); setSpeaking(false); setPaused(false); setFocus(null); setNarratedNode(null);
    setHighlightId(null); setAnnotation(null); setNarrationText('');
  }
  function applyAction(action: ClassroomScene['actions'][number]) {
    if (action.kind === 'reveal' && action.target_id) {
      const id = action.target_id;
      setRevealed(current => ({ ...current, [scene.id]: [...new Set([...(current[scene.id] ?? []), id])] }));
    }
    setNarrationText(action.text);
    if (action.kind === 'clear') {
      setFocus(null); setNarratedNode(null); setHighlightId(null); setAnnotation(null);
      return;
    }
    setFocus(action.focus ?? (action.target_id ? 'visual' : null));
    setNarratedNode(action.node_id ?? null);
    setHighlightId(action.target_id ?? null);
    setAnnotation(action.kind === 'annotate' ? action.note || null : null);
  }
  function showPart(part = narrationIndex) {
    stopNarration();
    if (part >= scene.actions.length) return;
    applyAction(scene.actions[part]);
    setNarrationIndex(part + 1);
  }
  function listen(part = narrationIndex) {
    stopNarration();
    const token = narrationToken.current;
    const current = part >= scene.actions.length ? 0 : part;
    const action = scene.actions[current];
    if (!speechAvailable) { applyAction(action); setNarrationIndex(current + 1); return; }
    const utterance = new SpeechSynthesisUtterance(action.text);
    utterance.onstart = () => { if (token !== narrationToken.current) return; applyAction(action); setSpeaking(true); };
    utterance.onend = () => { if (token !== narrationToken.current) return; if (action.kind !== 'pause' && action.kind !== 'annotate') { setFocus(null); setHighlightId(null); } setSpeaking(false); setPaused(false); setNarrationIndex(current + 1); };
    utterance.onerror = () => { if (token !== narrationToken.current) return; showPart(current); };
    setSpeaking(true); window.speechSynthesis.speak(utterance);
  }
  function reviewSavedWork(sceneId: string, result: Feedback) {
    const key = result.submission_key;
    if (!key) return;
    function updateReview(assessment?: Feedback['assessment']) {
      setSaved(current => {
        const work = current[sceneId];
        if (work?.feedback.submission_key !== key) return current;
        return { ...current, [sceneId]: { ...work, feedback: { ...work.feedback, assessment, assessment_pending: false } } };
      });
    }
    void reviewClassroomResponse(studentId, itemId, key).then(updateReview, () => updateReview());
  }
  async function saveActivity(text: string, activity: ActivityWork) {
    if (saving) throw new Error('Please wait for the current save.');
    setSaving(true); setError('');
    const fingerprint = JSON.stringify({ text, activity });
    if (pending.current?.text !== fingerprint) pending.current = { text: fingerprint, key: crypto.randomUUID() };
    try {
      const receipt = await submitClassroomResponse(studentId, itemId, scene.id, text, pending.current.key, activity);
      const result = { ...receipt, assessment_pending: activity.stage === 'observation' && !!receipt.submission_key };
      setSaved(current => ({ ...current, [scene.id]: { text, feedback: result, activity } }));
      setFeedback(result); pending.current = null; setActivityDirty(false);
      if (activity.stage === 'observation') reviewSavedWork(scene.id, result);
    } catch (reason) { throw reason instanceof Error ? reason : new Error('Your work could not be saved.'); }
    finally { setSaving(false); }
  }
  async function save() {
    if (!response.trim() || saving || !sortingComplete) return;
    setSaving(true); setError('');
    if (pending.current?.text !== response) pending.current = { text: response, key: crypto.randomUUID() };
    try {
      const receipt = await submitClassroomResponse(studentId, itemId, scene.id, response, pending.current.key);
      const result = { ...receipt, assessment_pending: !!receipt.submission_key };
      setSaved(current => ({ ...current, [scene.id]: { text: response, feedback: result } })); setFeedback(result); pending.current = null;
      reviewSavedWork(scene.id, result);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your response could not be saved.'); }
    finally { setSaving(false); }
  }
  const teaching = <div className="space-y-4">
    <p className={`whitespace-pre-line leading-8 ${scene.type === 'slide' ? 'text-lg' : ''} ${focus === 'content' ? 'rounded-xl ring-2 ring-[#bba978] ring-offset-4' : ''}`}>{scene.content}</p>
    {scene.visual && <div className={focus === 'visual' ? 'rounded-2xl ring-2 ring-[#bba978] ring-offset-4' : ''}><SceneVisual visual={scene.visual} activeId={highlightId} hiddenIds={hiddenVisualIds} /></div>}
    {annotation && <p role="status" className="rounded-xl bg-[#f2ead7] p-4">{annotation}</p>}
    {scene.worked_example && <div className="rounded-xl border border-[#d9cfbc] bg-white p-4">
      <h3 className="font-semibold">Worked example</h3>
      <p className="mt-2 whitespace-pre-line leading-7">{scene.worked_example}</p>
    </div>}
    {scene.key_points.length > 0 && <ul className="list-disc space-y-2 pl-5">{scene.key_points.map(point => <li key={point}>{point}</li>)}</ul>}
  </div>;
  const task = <div className={`space-y-2 leading-7 ${focus === 'task' ? 'rounded-xl ring-2 ring-[#bba978] ring-offset-4' : ''}`}>
    <p>{scene.learner_task}</p><p className="text-sm">{scene.family_roles[band]}</p>
  </div>;
  const responseForm = !hasLab && <fieldset className="space-y-3" disabled={saving}><legend className="mb-3 font-semibold">{scene.question?.prompt ?? (scene.sorting ? 'Check your classifications' : scene.portfolio_title ?? 'Record your work')}</legend>
    {scene.question ? scene.question.choices.map(choice => <label key={choice.id} className="flex cursor-pointer gap-3 rounded-xl border border-[#c9bfa9] bg-white p-4 has-[:checked]:border-[#183d32] has-[:checked]:bg-[#e7efdf]"><input type="radio" name={`answer-${scene.id}`} value={choice.id} checked={response === choice.id} onChange={() => { setResponse(choice.id); setFeedback(null); }} />{choice.label}</label>) : !scene.sorting && <textarea aria-label="Your response" rows={5} value={response} onChange={e => { setResponse(e.target.value); setFeedback(null); }} className="w-full rounded-xl border border-[#c9bfa9] bg-white p-4" />}
    <button onClick={save} disabled={!response.trim() || saving || !sortingComplete} className="min-h-11 rounded-xl bg-[#183d32] px-5 py-3 text-white disabled:opacity-50">{saving ? 'Saving…' : scene.question || scene.sorting ? 'Check and save' : scene.portfolio_title ? 'Save to portfolio' : 'Save my work'}</button>
  </fieldset>;
  const activity = <div className={focus === 'activity' ? 'rounded-2xl ring-2 ring-[#bba978] ring-offset-4' : ''}>
    {scene.sorting && <SortingActivity scene={scene} response={response} disabled={saving} onChange={value => { setResponse(value); setFeedback(null); }} />}
    {hasLab && <ActivityLab key={`${studentId}:${itemId}:${scene.id}`} scene={scene} saved={saved[scene.id]} saving={saving} onSave={saveActivity} onDirty={setActivityDirty} narratedNode={narratedNode} />}
  </div>;
  const project = <div className="rounded-2xl border border-[#d9cfbc] bg-[#fff9ec] p-5">
    {scene.materials.length > 0 && <div className="mb-5"><h3 className="font-semibold">Gather</h3><ul className="mt-2 flex flex-wrap gap-2">{scene.materials.map(material => <li key={material} className="rounded-lg bg-[#f2ead7] px-3 py-1">{material}</li>)}</ul></div>}
    <h3 className="font-semibold">Do the investigation</h3>
    <ol className="mt-3 list-decimal space-y-3 pl-5 leading-7">{scene.steps.map(step => <li key={step}>{step}</li>)}</ol>
  </div>;
  const review = feedback && saved[scene.id]?.feedback.submission_key === feedback.submission_key ? saved[scene.id]?.feedback : feedback;
  const nextDisabled = index === classroom.scenes.length - 1 || saving || asking || dirty || attemptPending;
  const narrationFinished = narrationIndex >= scene.actions.length;
  return <main className="mx-auto max-w-6xl space-y-6 text-[#183d32]">
    <header className="rounded-3xl bg-[#183d32] p-7 text-[#fff9ec] md:p-10"><h1 className="text-3xl md:text-4xl">{classroom.blueprint.title}</h1><p className="mt-3 max-w-3xl text-lg">{classroom.blueprint.essential_question}</p></header>
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <article className="min-w-0 space-y-6 rounded-3xl border border-[#d9cfbc] bg-[#fffdf7] p-6 md:p-9">
        <div>
          <p className="text-sm">{index + 1} of {classroom.scenes.length} · {{ slide: 'Explore the idea', interactive: 'Try it', quiz: 'Check your thinking', pbl: 'Investigate' }[scene.type]}</p>
          <h2 ref={heading} tabIndex={-1} className="mt-2 scroll-mt-28 text-3xl focus:outline-none">{scene.title}</h2>
        </div>
        {scene.actions.length > 0 && <div className="flex flex-wrap gap-2">
          {speechAvailable && (!speaking ? <button onClick={() => listen()} className="min-h-11 rounded-lg border border-[#bba978] px-3 py-2 text-sm">{narrationIndex === 0 ? 'Listen' : narrationFinished ? 'Listen again' : 'Continue narration'}</button> : <>
            <button className="min-h-11 rounded-lg border border-[#bba978] px-3 py-2 text-sm" onClick={() => { if (paused) window.speechSynthesis.resume(); else window.speechSynthesis.pause(); setPaused(p => !p); }}>{paused ? 'Resume narration' : 'Pause narration'}</button>
            <button className="min-h-11 rounded-lg border px-3 py-2 text-sm" onClick={stopNarration}>Stop narration</button>
          </>)}
          {!narrationFinished && <button onClick={() => showPart()} className="min-h-11 rounded-lg border px-3 py-2 text-sm">{narrationIndex === 0 && !speechAvailable ? 'Show the teaching steps' : 'Next part'}</button>}
          {narrationFinished && <span role="status" className="self-center text-sm">Teaching steps complete</span>}
        </div>}
        {narrationText && narrationText.trim() !== scene.content.trim() && <p role="status" className="rounded-xl bg-[#e7efdf] p-4">{narrationText}</p>}
        {scene.type === 'quiz' ? <div className="space-y-5 rounded-2xl bg-[#f2ead7] p-5">{teaching}{responseForm}<details><summary className="cursor-pointer text-sm font-semibold">Discuss your reasoning</summary><div className="mt-2">{task}</div></details></div> : teaching}
        {scene.type === 'interactive' && <>{task}{activity}{responseForm}</>}
        {scene.type === 'pbl' && <>{scene.steps.length > 0 && project}{task}{responseForm}</>}
        {scene.type === 'slide' && (scene.response_required ? <>{task}{responseForm}</> : <details key={scene.id} open={dirty || !!saved[scene.id]}><summary className="cursor-pointer font-semibold">Try it or add a note</summary><div className="mt-4 space-y-4">{task}{responseForm}</div></details>)}
        {(pageMaterials.length > 0 || promisesMaterial) && <section id={`scene-materials-${scene.id}`} aria-label="Materials for this page" className="space-y-4">
          <h3 className="text-xl font-semibold">Materials for this page</h3>
          {materialLoading[scene.id] && <p role="status">Preparing the materials mentioned on this page…</p>}
          {materialErrors[scene.id] && <div role="alert"><p>{materialErrors[scene.id]}</p><button onClick={() => void loadMaterials(scene.id)} className="mt-2 rounded-lg border px-4 py-2">Try loading materials again</button></div>}
          {pageMaterials.map(material => <article key={material.id} className="space-y-3 rounded-2xl border border-[#d9cfbc] bg-white p-5">
            <h4 className="font-semibold">{material.title}</h4>
            {material.kind === 'image' && !scene.visual?.elements.some(element => element.type === 'image' && element.url === material.image_url) && <LessonImage key={material.image_url} src={material.image_url} alt={material.title} />}
            {material.content && <p className="whitespace-pre-line leading-7">{material.content}</p>}
            {material.supports && <p className="leading-7">{material.supports}</p>}
            {material.url && <a href={material.url} target="_blank" rel="noopener noreferrer" className="inline-block font-semibold underline">{material.kind === 'image' ? 'Open the image source' : 'Open the reading or source'} →</a>}
            {material.attribution && <p className="text-xs leading-5">{material.attribution}</p>}
            {material.license_url && <a href={material.license_url} target="_blank" rel="noopener noreferrer" className="text-xs underline">License</a>}
          </article>)}
        </section>}
        {feedback && <p role="status" className="rounded-xl bg-[#e7efdf] p-4">{feedback.correct === undefined ? '' : feedback.correct ? 'That matches the evidence. ' : 'Try another explanation. '}{feedback.review}</p>}
        {feedback?.items && <ul aria-label="Classification feedback" className="space-y-3">{feedback.items.map(item => { const label = scene.sorting?.items.find(i => i.id === item.item_id)?.label ?? scene.interaction?.steps?.find(step => step.id === item.item_id)?.label ?? scene.interaction?.pairs?.find(pair => pair.id === item.item_id)?.prompt ?? matterMenu.find(([id]) => id === item.item_id)?.[1] ?? item.item_id; return <li key={item.item_id} className="rounded-xl border border-[#d9cfbc] p-4"><b>{label}:</b> {item.correct ? 'Matches. ' : 'Reconsider. '}{item.explanation}</li>; })}</ul>}
        {error && <p role="alert" className="text-red-800">{error}</p>}
        {scene.type !== 'slide' && <details><summary className="cursor-pointer font-semibold">What to show</summary><ul className="mt-3 list-disc space-y-2 pl-5">{scene.success_criteria.map(c => <li key={c}>{c}</li>)}</ul></details>}
        {scene.actions.length > 0 && <details key={`transcript-${scene.id}`} onToggle={e => setShowTranscript(e.currentTarget.open)}><summary className="cursor-pointer font-semibold">Read or replay the narration</summary>{showTranscript && <ol className="mt-3 space-y-3">{scene.actions.map((action, i) => <li key={i} className="rounded-xl border border-[#d9cfbc] p-3"><p>{action.text}</p>{speechAvailable && <button className="mt-2 min-h-11 rounded-lg border px-3 text-sm" onClick={() => listen(i)}>Replay part {i + 1}</button>}</li>)}</ol>}</details>}
        {review?.submission_key && <details open={scene.type === 'pbl'}><summary className="cursor-pointer font-semibold">Learning review</summary><LearningReviewPanel key={review.submission_key} feedback={review} studentId={studentId} itemId={itemId} track={state.request?.track ?? classroom.blueprint.integrated_tracks[0]} /></details>}
        <div className="sticky bottom-0 z-10 border-t border-[#d9cfbc] bg-[#fffdf7] py-3">
          {saving ? <p role="status" className="mb-2 text-sm">Saving your work…</p> : dirty ? <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <p>Save your work before changing pages.</p>
            {!hasLab && <button onClick={() => { setResponse(saved[scene.id]?.text ?? ''); setFeedback(saved[scene.id]?.feedback ?? null); setError(''); pending.current = null; }} className="min-h-11 underline">Discard unsaved changes</button>}
          </div> : attemptPending ? <p className="mb-2 text-sm">Save your first attempt above to unlock the next page.</p> : asking ? <p className="mb-2 text-sm">Waiting for Adeline’s reply…</p> : null}
          <nav aria-label="Exploration pages" className="flex justify-between gap-3">
            <button disabled={index === 0 || saving || asking || dirty} onClick={() => setIndex(i => i - 1)} className="min-h-11 rounded-xl border px-5 disabled:opacity-40">Previous</button>
            {index < classroom.scenes.length - 1 ? <button disabled={nextDisabled} onClick={() => setIndex(i => i + 1)} className="min-h-11 rounded-xl bg-[#183d32] px-5 text-white disabled:opacity-40">Next</button> : <Link href="/dashboard" className="inline-flex min-h-11 items-center rounded-xl border px-5">Back to Today</Link>}
          </nav>
        </div>
      </article>
      <aside className="space-y-4" aria-label="Talk with Adeline"><h2 className="text-lg font-semibold">Adeline</h2>{(pageMaterials.length > 0 || promisesMaterial) && <a href={`#scene-materials-${scene.id}`} className="block font-semibold underline">View this page’s materials ↓</a>}{discussionActions.map((action, i) => { const role = classroom.blueprint.roster.find(r => r.id === action.role_id); return <div key={`${scene.id}-${i}`} className="rounded-2xl border border-[#d9cfbc] bg-white p-5"><p className="font-semibold">{role?.name ?? 'Adeline'}</p><p className="mt-2 leading-7">{action.text}</p></div>; })}
        {(dialogue[scene.id] ?? []).map(turn => <div key={turn.key} className="space-y-3 rounded-2xl border border-[#d9cfbc] bg-white p-5"><p className="text-sm"><b>You:</b> {turn.question}</p><p className="leading-7"><b>Adeline:</b> {turn.answer}</p></div>)}
        <form onSubmit={e => { e.preventDefault(); void ask(); }} className="grid gap-3 rounded-2xl border border-[#d9cfbc] bg-white p-5"><label htmlFor="classroom-question" className="font-semibold">Talk it through with Adeline</label><textarea id="classroom-question" rows={3} maxLength={4000} value={question} disabled={asking} onChange={e => setQuestion(e.target.value)} className="rounded-xl border p-3" placeholder="Ask a question, or explain your thinking…" /><button type="button" disabled={asking} onClick={() => void ask("Give me one small hint using a different example, then let me try.")} className="min-h-11 rounded-xl border border-[#bba978] px-4 py-3 disabled:opacity-50">Give me a hint</button><button disabled={asking || !question.trim()} className="min-h-11 rounded-xl bg-[#183d32] px-4 py-3 text-white disabled:opacity-50">{asking ? 'Adeline is thinking…' : 'Send'}</button></form>
      </aside>
    </div>
  </main>;
}
