'use client';

import { useState } from 'react';

/** A structured alternative to typing a whole log entry as one chat paragraph.
 * Fields are generic (day/measurement/observation/notes) so this applies to any
 * observe-and-record activity, not just the sourdough starter it was built for. */
export function LogEntryForm({ onSubmit, disabled }: { onSubmit: (text: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [day, setDay] = useState('');
  const [rise, setRise] = useState('');
  const [bubbles, setBubbles] = useState('');
  const [smell, setSmell] = useState('');
  const [notes, setNotes] = useState('');

  function submit() {
    const lines = [
      day.trim() && `Day: ${day.trim()}`,
      rise.trim() && `Rise: ${rise.trim()}`,
      bubbles.trim() && `Bubbles: ${bubbles.trim()}`,
      smell.trim() && `Smell: ${smell.trim()}`,
      notes.trim() && `Notes: ${notes.trim()}`,
    ].filter(Boolean) as string[];
    if (!lines.length) return;
    onSubmit(lines.join('\n'));
    setDay(''); setRise(''); setBubbles(''); setSmell(''); setNotes(''); setOpen(false);
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
        <input
          value={day} onChange={(e) => setDay(e.target.value)} placeholder="Day #"
          className="rounded-lg border border-[#E7DAC3] px-2 py-1.5 text-sm text-[#2F4731]"
        />
        <input
          value={rise} onChange={(e) => setRise(e.target.value)} placeholder="Rise (e.g. doubled)"
          className="rounded-lg border border-[#E7DAC3] px-2 py-1.5 text-sm text-[#2F4731]"
        />
        <input
          value={bubbles} onChange={(e) => setBubbles(e.target.value)} placeholder="Bubbles"
          className="rounded-lg border border-[#E7DAC3] px-2 py-1.5 text-sm text-[#2F4731]"
        />
        <input
          value={smell} onChange={(e) => setSmell(e.target.value)} placeholder="Smell"
          className="rounded-lg border border-[#E7DAC3] px-2 py-1.5 text-sm text-[#2F4731]"
        />
      </div>
      <textarea
        value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Anything else you noticed…" rows={2}
        className="w-full resize-none rounded-lg border border-[#E7DAC3] px-2 py-1.5 text-sm text-[#2F4731]"
      />
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
