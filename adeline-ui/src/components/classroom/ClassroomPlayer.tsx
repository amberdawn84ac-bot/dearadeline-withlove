'use client';

import { useEffect, useRef, useState } from 'react';
import { ClassroomScene, ClassroomState, Feedback, ClassroomTurn, talkToClassroom, submitClassroomResponse } from '@/lib/classroom-client';

function Simulation({ scene }: { scene: ClassroomScene }) {
  const spec = scene.simulation!;
  const [x, setX] = useState(spec.x.initial);
  const [y, setY] = useState(spec.y.initial);
  const [prediction, setPrediction] = useState('');
  const value = spec.model === 'mixture_fraction' ? x / (x + y) : x * y;
  return <div className="space-y-5 rounded-2xl bg-emerald-950 p-6 text-white">
    <p>{spec.prediction_prompt}</p>
    <label className="grid gap-2">Your prediction<input value={prediction} onChange={e => setPrediction(e.target.value)} className="rounded-lg bg-white p-3 text-emerald-950" /></label>
    {(['x', 'y'] as const).map(axis => {
      const variable = spec[axis]; const current = axis === 'x' ? x : y;
      return <label key={axis} className="grid gap-2">{variable.label}: {current} {variable.unit}<input type="range" min={variable.minimum} max={variable.maximum} step={variable.step} value={current} onChange={e => (axis === 'x' ? setX : setY)(Number(e.target.value))} /></label>;
    })}
    <output aria-live="polite" className="block text-4xl font-semibold tabular-nums">{value.toLocaleString(undefined, { maximumFractionDigits: 4 })} <span className="text-base">{spec.output_unit} · {spec.output_label}</span></output>
    {spec.model === 'rectangle_area' && <svg viewBox="0 0 300 160" role="img" aria-label={`Rectangle with sides ${x} and ${y}`} className="h-40 w-full"><rect x="20" y="10" width={Math.max(1, x / spec.x.maximum * 260)} height={Math.max(1, y / spec.y.maximum * 140)} fill="#c9a45c" /></svg>}
    <p className="text-sm text-emerald-100">{spec.explanation}</p><p>{spec.observation_prompt}</p>
    <p className="text-xs text-emerald-200">Prediction and slider changes are local. Include your observations in the saved response below.</p>
  </div>;
}

export default function ClassroomPlayer({ state, studentId, itemId, grade }: { state: ClassroomState; studentId: string; itemId: string; grade: string }) {
  const classroom = state.classroom!;
  const [index, setIndex] = useState(0);
  const scene = classroom.scenes[index];
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
  async function ask() {
    if (!question.trim() || asking) return;
    setAsking(true); setError('');
    if (questionKey.current?.text !== question) questionKey.current = { text: question, key: crypto.randomUUID() };
    try {
      const turn = await talkToClassroom(studentId, itemId, scene.id, question, questionKey.current.key);
      setDialogue(current => ({ ...current, [scene.id]: [...(current[scene.id] ?? []).filter(t => t.key !== turn.key), turn] }));
      setQuestion(''); questionKey.current = null;
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Adeline could not reply. Your message is still here.'); }
    finally { setAsking(false); }
  }
  const dirty = response !== (saved[scene.id]?.text ?? '');
  const numericGrade = grade.toUpperCase() === 'K' ? 0 : Number.parseInt(grade, 10);
  const band = numericGrade <= 5 ? 'elementary' : numericGrade <= 8 ? 'middle' : 'high_school';
  useEffect(() => { setSpeechAvailable('speechSynthesis' in window); return () => window.speechSynthesis?.cancel(); }, []);
  useEffect(() => {
    setQuestion(''); questionKey.current = null;
    setResponse(saved[scene.id]?.text ?? ''); setFeedback(saved[scene.id]?.feedback ?? null); setError(''); pending.current = null;
    window.speechSynthesis?.cancel();
  }, [scene.id, saved]);
  function listen() {
    window.speechSynthesis.cancel();
    for (const action of scene.actions) window.speechSynthesis.speak(new SpeechSynthesisUtterance(action.text));
  }
  async function save() {
    if (!response.trim() || saving) return;
    setSaving(true); setError('');
    if (pending.current?.text !== response) pending.current = { text: response, key: crypto.randomUUID() };
    try {
      const result = await submitClassroomResponse(studentId, itemId, scene.id, response, pending.current.key);
      setSaved(current => ({ ...current, [scene.id]: { text: response, feedback: result } })); setFeedback(result); pending.current = null;
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your response could not be saved.'); }
    finally { setSaving(false); }
  }
  return <main className="mx-auto max-w-6xl space-y-6 text-[#183d32]">
    <header className="rounded-3xl bg-[#183d32] p-7 text-[#fff9ec] md:p-10"><p className="text-xs uppercase tracking-[.25em] text-[#d8b976]">Dear Adeline · Classroom</p><h1 className="mt-3 text-3xl md:text-4xl">{classroom.blueprint.title}</h1><p className="mt-4 max-w-3xl text-lg">{classroom.blueprint.essential_question}</p></header>
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <article className="min-w-0 rounded-3xl border border-[#d9cfbc] bg-[#fffdf7] p-6 md:p-9">
        <div className="flex items-start justify-between gap-3"><p className="text-sm">{index + 1} / {classroom.scenes.length}</p>{speechAvailable && <button onClick={listen} className="rounded-lg border border-[#bba978] px-3 py-2 text-sm">Listen</button>}</div>
        <h2 className="mt-5 text-3xl">{scene.title}</h2><p className="mt-5 whitespace-pre-line text-lg leading-8">{scene.content}</p>
        {scene.key_points.length > 0 && <ul className="my-5 list-disc space-y-2 pl-5">{scene.key_points.map(point => <li key={point}>{point}</li>)}</ul>}
        {scene.simulation && <Simulation key={scene.id} scene={scene} />}
        {scene.materials.length > 0 && <p className="mt-5 text-sm"><b>Bring:</b> {scene.materials.join(', ')}</p>}
        {scene.steps.length > 0 && <ol className="mt-5 list-decimal space-y-3 pl-5">{scene.steps.map(step => <li key={step}>{step}</li>)}</ol>}
        <section className="mt-7 rounded-2xl bg-[#f2ead7] p-5"><h3 className="font-semibold">Your part</h3><p className="mt-2 leading-7">{scene.family_roles[band]}</p><p className="mt-3 leading-7">{scene.learner_task}</p></section>
        <fieldset className="mt-6 space-y-3" disabled={saving}><legend className="mb-3 font-semibold">{scene.question?.prompt ?? 'Keep your explanation, observations, or project notes'}</legend>
          {scene.question ? scene.question.choices.map(choice => <label key={choice.id} className="flex cursor-pointer gap-3 rounded-xl border border-[#c9bfa9] p-4"><input type="radio" name={`answer-${scene.id}`} value={choice.id} checked={response === choice.id} onChange={() => { setResponse(choice.id); setFeedback(null); }} />{choice.label}</label>) : <textarea aria-label="Your response" rows={5} value={response} onChange={e => { setResponse(e.target.value); setFeedback(null); }} className="w-full rounded-xl border border-[#c9bfa9] bg-white p-4" />}
          <button onClick={save} disabled={!response.trim() || saving} className="min-h-11 rounded-xl bg-[#183d32] px-5 py-3 text-white disabled:opacity-50">{saving ? 'Saving…' : scene.question ? 'Check and save' : 'Save my work'}</button>
        </fieldset>
        {feedback && <p role="status" className="mt-4 rounded-xl bg-[#e7efdf] p-4">{feedback.correct === undefined ? '' : feedback.correct ? 'That matches the evidence. ' : 'Try another explanation. '}{feedback.review}</p>}
        {error && <p role="alert" className="mt-4 text-red-800">{error}</p>}
        <details className="mt-6"><summary className="cursor-pointer font-semibold">What to show</summary><ul className="mt-3 list-disc space-y-2 pl-5">{scene.success_criteria.map(c => <li key={c}>{c}</li>)}</ul></details>
        {dirty && <p className="mt-4 text-sm">Save your response before changing pages.</p>}
        <nav aria-label="Classroom pages" className="mt-8 flex justify-between gap-3"><button disabled={index === 0 || saving || asking || dirty} onClick={() => setIndex(i => i - 1)} className="min-h-11 rounded-xl border px-5 disabled:opacity-40">Previous</button><button disabled={index === classroom.scenes.length - 1 || saving || asking || dirty} onClick={() => setIndex(i => i + 1)} className="min-h-11 rounded-xl border px-5 disabled:opacity-40">Next</button></nav>
      </article>
      <aside className="space-y-4" aria-label="Classroom conversation"><h2 className="text-lg font-semibold">At the table</h2>{scene.actions.map((action, i) => { const role = classroom.blueprint.roster.find(r => r.id === action.role_id); return <div key={`${scene.id}-${i}`} className="rounded-2xl border border-[#d9cfbc] bg-white p-5"><p className="font-semibold">{role?.name ?? 'Adeline'}</p><p className="mt-2 leading-7">{action.text}</p></div>; })}
        {(dialogue[scene.id] ?? []).map(turn => <div key={turn.key} className="space-y-3 rounded-2xl border border-[#d9cfbc] bg-white p-5"><p className="text-sm"><b>You:</b> {turn.question}</p><p className="leading-7"><b>Adeline:</b> {turn.answer}</p></div>)}
        <form onSubmit={e => { e.preventDefault(); void ask(); }} className="grid gap-3 rounded-2xl border border-[#d9cfbc] bg-white p-5"><label htmlFor="classroom-question" className="font-semibold">Talk it through with Adeline</label><textarea id="classroom-question" rows={3} maxLength={4000} value={question} disabled={asking} onChange={e => setQuestion(e.target.value)} className="rounded-xl border p-3" placeholder="Ask a question, or explain your thinking…" /><button disabled={asking || !question.trim()} className="min-h-11 rounded-xl bg-[#183d32] px-4 py-3 text-white disabled:opacity-50">{asking ? 'Adeline is thinking…' : 'Send'}</button></form>
      </aside>
    </div>
  </main>;
}
