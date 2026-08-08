'use client';

import { useState } from 'react';
import { Bookmark, Check, Feather, Lightbulb, Sparkles } from 'lucide-react';

export type SketchnoteSection = {
  heading: string;
  text: string;
  symbol?: string;
};

export type SketchnoteData = {
  title: string;
  big_idea?: string;
  sections?: SketchnoteSection[];
  keywords?: string[];
  footer?: string;
  track?: string;
};

type Props = {
  note: SketchnoteData;
  onSave?: () => Promise<void> | void;
};

export default function SketchnoteCard({ note, onSave }: Props) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    if (!onSave || saving || saved) return;
    setSaving(true);
    try {
      await onSave();
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="relative my-3 overflow-hidden rounded-[18px_10px_21px_12px] border border-[#c9bda7] bg-[#fffdf4] p-5 text-[#29382d] shadow-[0_10px_30px_rgba(76,55,30,.09)]">
      <div className="pointer-events-none absolute inset-0 opacity-[.17]" style={{
        backgroundImage: 'linear-gradient(#7f8a7f 1px, transparent 1px), linear-gradient(90deg, #7f8a7f 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }} />
      <div className="pointer-events-none absolute -right-6 -top-7 h-24 w-24 rotate-12 rounded-[46%_54%_61%_39%] border-[3px] border-[#2f6782]/30" />
      <div className="pointer-events-none absolute bottom-5 left-3 h-7 w-20 rotate-[-4deg] border-b-2 border-[#9a4d71]/50" />

      <div className="relative">
        <div className="mb-3 flex items-start justify-between gap-4">
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[.18em] text-[#8e7448]"><Feather size={12} /> field note</p>
            <h3 className="font-serif text-2xl leading-tight text-[#254431] underline decoration-[#d5a834]/50 decoration-4 underline-offset-4">{note.title}</h3>
          </div>
          {onSave && (
            <button onClick={() => void save()} disabled={saving || saved} className="flex shrink-0 items-center gap-1.5 rounded-full border border-[#cdbd9f] bg-[#f8f0dc]/90 px-3 py-1.5 text-[11px] font-semibold text-[#6f5a39] hover:bg-[#f3e6c9] disabled:opacity-70">
              {saved ? <Check size={12} /> : <Bookmark size={12} />}{saved ? 'saved' : saving ? 'saving' : 'journal'}
            </button>
          )}
        </div>

        {note.big_idea && (
          <div className="mb-4 rotate-[-.4deg] rounded-[10px_16px_9px_14px] border-2 border-[#d3a331]/60 bg-[#fff4bf]/60 px-4 py-3">
            <p className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[.12em] text-[#8b6413]"><Lightbulb size={14} /> big idea</p>
            <p className="mt-1 font-serif text-[17px] leading-snug text-[#3c4637]">{note.big_idea}</p>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {(note.sections ?? []).map((section, index) => (
            <section key={`${section.heading}-${index}`} className={`relative rounded-[13px_9px_15px_10px] border px-3 py-3 ${index % 3 === 0 ? 'border-[#386d86]/35 bg-[#eaf4f5]/70' : index % 3 === 1 ? 'border-[#8f4f70]/30 bg-[#f8edf2]/70' : 'border-[#4e754f]/35 bg-[#edf4e9]/75'}`}>
              <div className="mb-1 flex items-center gap-2">
                <span className="text-lg leading-none">{section.symbol || (index % 3 === 0 ? '✦' : index % 3 === 1 ? '↗' : '◎')}</span>
                <h4 className="font-serif text-base font-bold text-[#294533]">{section.heading}</h4>
              </div>
              <p className="text-[13px] leading-relaxed text-[#4f5b50]">{section.text}</p>
            </section>
          ))}
        </div>

        {!!note.keywords?.length && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Sparkles size={13} className="text-[#936d21]" />
            {note.keywords.map((word, index) => (
              <span key={`${word}-${index}`} className={`rotate-[${index % 2 === 0 ? '-1deg' : '1deg'}] rounded-sm border-b-2 px-1 text-[11px] font-bold ${index % 3 === 0 ? 'border-[#2f6782]/45 text-[#315f76]' : index % 3 === 1 ? 'border-[#9a4d71]/45 text-[#87425f]' : 'border-[#b1872b]/50 text-[#81621e]'}`}>{word}</span>
            ))}
          </div>
        )}

        {note.footer && <p className="mt-4 border-t border-dashed border-[#b8aa91] pt-3 text-xs italic text-[#736956]">{note.footer}</p>}
      </div>
    </article>
  );
}
