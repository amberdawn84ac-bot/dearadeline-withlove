'use client';
import { useEffect, useState } from 'react';
import { CourseTarget, defineCourseScope, getCourseTargets } from '@/lib/brain-client';
import { TRACKS, ClassroomTrack } from '@/lib/classroom-client';

export default function CourseScopeForm({ studentId, onSaved }: { studentId: string; onSaved: () => void }) {
  const [query,setQuery] = useState('');
  const [targets, setTargets] = useState<CourseTarget[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState(''); const [rationale, setRationale] = useState('');
  const [track, setTrack] = useState<ClassroomTrack>('CREATION_SCIENCE');
  const [bucket, setBucket] = useState('SCIENCE_CORE'); const [units, setUnits] = useState(.5);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  useEffect(() => { let active = true; getCourseTargets(studentId,query).then(rows => { if (active) setTargets(rows); }).catch(() => { if (active) setError('Could not load curriculum targets.'); }); return () => { active = false; }; }, [studentId,query]);
  async function save() {
    setBusy(true); setError('');
    try { await defineCourseScope(studentId, { title, track, bucket, credit_units: units, skill_ids: selected, rationale }); setTitle(''); setSelected([]); setRationale(''); onSaved(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save this course.'); }
    finally { setBusy(false); }
  }
  return <details className="rounded-2xl border border-[#DED1BD] p-5"><summary className="cursor-pointer font-semibold">Define a course for credit review</summary>
    <p className="mt-3 text-sm">Choose the full course scope and explain its credit equivalency. Adeline checks the evidence; a parent approves the final award. A short activity is not a full course.</p>
    <div className="mt-4 grid gap-4">
      <label className="grid gap-1">Course title<input className="rounded-lg border p-3" value={title} onChange={e => setTitle(e.target.value)} maxLength={200} /></label>
      <label className="grid gap-1">Primary track<select className="min-h-11 rounded-lg border p-3" value={track} onChange={e => setTrack(e.target.value as ClassroomTrack)}>{Object.entries(TRACKS).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <label className="grid gap-1">Credit allocation<select className="min-h-11 rounded-lg border p-3" value={bucket} onChange={e => setBucket(e.target.value)}>{['ENGLISH_CORE','MATH_CORE','SCIENCE_CORE','SOCIAL_STUDIES','WORLD_LANGUAGE','PERSONAL_FINANCE','FINE_ARTS','ELECTIVES'].map(b => <option key={b} value={b}>{b.replaceAll('_',' ')}</option>)}</select></label>
      <label className="grid gap-1">Proposed course credits<select className="min-h-11 rounded-lg border p-3" value={units} onChange={e => setUnits(Number(e.target.value))}><option value={.5}>0.5</option><option value={1}>1</option><option value={2}>2</option></select></label>
      <label className="grid gap-1">Find curriculum objectives<input className="rounded-lg border p-3" value={query} onChange={e => setQuery(e.target.value.slice(0,100))} placeholder="Search a concept or standard code" /></label>
      <p className="text-sm">{selected.length} objectives selected</p>
      <fieldset><legend className="font-semibold">Course objectives</legend>{targets.length === 0 && <p className="mt-2 text-sm">Review evidence against curriculum targets first. Those targets appear here.</p>}
        <div className="max-h-72 overflow-auto">{targets.map(t => <label key={t.id} className="flex min-h-11 items-start gap-3 py-3"><input type="checkbox" className="mt-1" checked={selected.includes(t.id)} onChange={e => setSelected(old => e.target.checked ? [...old,t.id] : old.filter(id => id !== t.id))} /><span>{t.title}<small className="block">{t.id} · {t.status}</small></span></label>)}</div>
      </fieldset>
      <label className="grid gap-1">Why does this scope warrant these credits?<textarea rows={3} className="rounded-lg border p-3" value={rationale} onChange={e => setRationale(e.target.value)} maxLength={4000} /></label>
      <button type="button" disabled={busy || title.trim().length < 3 || rationale.trim().length < 30 || selected.length === 0} onClick={() => void save()} className="min-h-11 rounded-xl bg-[#183d32] px-4 py-3 text-white disabled:opacity-40">{busy ? 'Saving…' : 'Save course scope'}</button>
      {error && <p role="alert">{error}</p>}
    </div>
  </details>;
}
