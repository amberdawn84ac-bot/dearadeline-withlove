'use client';

import type { LearnerContext } from '@/lib/classroom-client';

const grades = ['K', ...Array.from({ length: 12 }, (_, i) => String(i + 1))];
const control = 'min-h-11 rounded-xl border border-[#c9bfa9] bg-white p-3';

export default function LearnerPreferences({ value, onChange }: {
  value?: LearnerContext;
  onChange: (context: LearnerContext | undefined) => void;
}) {
  const context: LearnerContext = value ?? { version: 'learner-context-v1', mode: 'individual', declared_grades: [], supports: [], language: 'en' };
  function change(patch: Partial<LearnerContext>) { onChange({ ...context, ...patch }); }
  return <details className="rounded-xl border border-[#d9cfbc] p-4">
    <summary className="cursor-pointer font-semibold">Adjust learning preferences</summary>
    <div className="mt-4 grid gap-4">
      <p className="text-sm">Optional. Leave these unchanged to use the learner description above.</p>
      <label className="grid gap-2">Who is exploring?
        <select aria-label="Who is exploring?" className={control} value={value?.mode ?? ''} onChange={e => e.target.value ? change({ mode: e.target.value as 'individual' | 'family', declared_grades: [], working_grade: null }) : onChange(undefined)}>
          <option value="">Use learner description</option><option value="individual">One learner</option><option value="family">Family together</option>
        </select>
      </label>
      {value?.mode === 'individual' && <>
        <label className="grid gap-2">Declared grade
          <select className={control} value={value.declared_grades[0] ?? ''} onChange={e => change({ declared_grades: e.target.value ? [e.target.value] : [] })}>
            <option value="">Not specified</option>{grades.map(g => <option key={g} value={g}>{g === 'K' ? 'Kindergarten' : 'Grade ' + g}</option>)}
          </select>
        </label>
        <label className="grid gap-2">Working grade for this topic
          <select className={control} value={value.working_grade ?? ''} onChange={e => change({ working_grade: e.target.value || null })}>
            <option value="">Use declared grade</option>{grades.map(g => <option key={g} value={g}>{g === 'K' ? 'Kindergarten' : 'Grade ' + g}</option>)}
          </select>
        </label>
      </>}
      {value?.mode === 'family' && <fieldset className="space-y-3">
        <legend className="font-semibold">Grades exploring together</legend>
        <div className="flex flex-wrap gap-2">{grades.map(g => <label key={g} className="flex min-h-11 items-center gap-2 rounded-lg border p-3">
          <input type="checkbox" checked={value.declared_grades.includes(g)} disabled={!value.declared_grades.includes(g) && value.declared_grades.length >= 10} onChange={e => change({ declared_grades: e.target.checked ? [...value.declared_grades, g] : value.declared_grades.filter(current => current !== g) })} />{g}
        </label>)}</div>
        <p className="text-sm">Grades guide the entry point. Each learner still needs their own work and review.</p>
      </fieldset>}
      {value && <>
        <fieldset className="space-y-2"><legend className="font-semibold">Helpful supports</legend>
          {([['reading_support', 'More reading support'], ['extra_time', 'More time to respond'], ['keyboard_input', 'Keyboard-friendly input'], ['screen_reader', 'Screen-reader-friendly explanations']] as const).map(([id, label]) => <label key={id} className="flex min-h-11 items-center gap-3"><input type="checkbox" checked={value.supports.includes(id)} onChange={e => change({ supports: e.target.checked ? [...value.supports, id] : value.supports.filter(current => current !== id) })} />{label}</label>)}
        </fieldset>
        <label className="grid gap-2">Time available
          <select className={control} value={value.minutes ?? ''} onChange={e => change({ minutes: e.target.value ? Number(e.target.value) : null })}><option value="">Flexible</option>{[10, 20, 30, 45, 60].map(n => <option key={n} value={n}>{n} minutes</option>)}</select>
        </label>
        <p className="text-sm">These preferences guide planning; they do not determine mastery.</p>
      </>}
    </div>
  </details>;
}
