'use client';

import { useState } from 'react';

const GENERIC_FIELDS = ['Day', 'Observation 1', 'Observation 2', 'Notes'];

/** A structured alternative to typing a whole log entry as one chat paragraph.
 * `fields` should be labels Adeline tailored to the current activity (e.g. a
 * sourdough log: Day/Rise/Bubbles/Smell). When Adeline hasn't supplied any yet
 * (the very first time this block is shown, before any turn has run), falls
 * back to generic, editable field labels so the family can name their own
 * columns rather than see fields that assume a specific kind of experiment. */
export function LogEntryForm({ onSubmit, disabled, fields }: {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  fields?: string[];
}) {
  const usingGenericFields = !fields?.length;
  const initialLabels = usingGenericFields ? GENERIC_FIELDS : fields;
  const [open, setOpen] = useState(false);
  const [labels, setLabels] = useState<string[]>(initialLabels);
  const [values, setValues] = useState<string[]>(initialLabels.map(() => ''));

  function submit() {
    const lines = labels
      .map((label, i) => (values[i]?.trim() ? `${label.trim() || `Field ${i + 1}`}: ${values[i].trim()}` : ''))
      .filter(Boolean);
    if (!lines.length) return;
    onSubmit(lines.join('\n'));
    setValues(initialLabels.map(() => ''));
    setOpen(false);
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        className="mt-2 rounded-full border border-[#2F4731]/25 bg-white px-3 py-2 text-xs font-bold text-[#2F4731] hover:bg-[#FDF6E9] disabled:opacity-50"
      >
        📓 Fill out today&apos;s log
      </button>
    );
  }

  return (
    <div className="mt-2 space-y-2 rounded-xl border border-[#E7DAC3] bg-white p-3">
      <p className="text-xs font-bold uppercase tracking-wide text-[#2F4731]/70">Today&apos;s log entry</p>
      <div className="grid grid-cols-2 gap-2">
        {labels.map((label, i) => (
          <div key={i} className="space-y-1">
            {usingGenericFields ? (
              <input
                value={label}
                onChange={(e) => setLabels((prev) => prev.map((l, idx) => (idx === i ? e.target.value : l)))}
                className="w-full rounded-lg border border-transparent bg-transparent px-1 text-[10px] font-bold uppercase tracking-wide text-[#2F4731]/60 focus:border-[#E7DAC3] focus:bg-white"
              />
            ) : (
              <p className="px-1 text-[10px] font-bold uppercase tracking-wide text-[#2F4731]/60">{label}</p>
            )}
            <input
              value={values[i] ?? ''}
              onChange={(e) => setValues((prev) => prev.map((v, idx) => (idx === i ? e.target.value : v)))}
              className="w-full rounded-lg border border-[#E7DAC3] px-2 py-1.5 text-sm text-[#2F4731]"
            />
          </div>
        ))}
      </div>
      <div className="flex gap-3">
        <button
          type="button" onClick={submit} disabled={disabled}
          className="rounded-full bg-[#2F4731] px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
        >
          Send to Adeline
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs font-bold text-[#2F4731]/60 underline">
          Cancel
        </button>
      </div>
    </div>
  );
}
