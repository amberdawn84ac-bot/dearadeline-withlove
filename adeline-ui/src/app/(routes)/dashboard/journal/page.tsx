'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, BookOpen, Loader2 } from 'lucide-react';
import { useStudent } from '@/lib/useStudent';
import { listDailyJournalNotes, type DailyJournalNote } from '@/lib/journal-client';
import SketchnoteCard from '@/components/SketchnoteCard';

function dayLabel(value: string | null) {
  if (!value) return 'Undated';
  const date = new Date(value);
  return new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(date);
}

export default function DailyJournalPage() {
  const { student, loading } = useStudent();
  const [notes, setNotes] = useState<DailyJournalNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(true);

  useEffect(() => {
    if (!student) return;
    setNotesLoading(true);
    listDailyJournalNotes(student.id)
      .then(setNotes)
      .finally(() => setNotesLoading(false));
  }, [student]);

  const grouped = useMemo(() => {
    const groups = new Map<string, DailyJournalNote[]>();
    for (const note of notes) {
      const key = note.created_at ? new Date(note.created_at).toISOString().slice(0, 10) : 'undated';
      groups.set(key, [...(groups.get(key) ?? []), note]);
    }
    return [...groups.entries()];
  }, [notes]);

  if (loading || notesLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f5f0e5] text-[#244a35]"><Loader2 className="h-5 w-5 animate-spin" /></div>;
  }

  return (
    <main className="min-h-screen bg-[#f2ebdc] px-4 py-6 text-[#294132] sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-7 flex items-start justify-between gap-4">
          <div>
            <Link href="/dashboard" className="mb-3 inline-flex items-center gap-1 text-xs text-[#76684f] hover:text-[#244a35]"><ArrowLeft size={14} /> back to Adeline</Link>
            <p className="text-[10px] uppercase tracking-[.2em] text-[#9a7a43]">the pages worth keeping</p>
            <h1 className="mt-1 font-serif text-4xl text-[#244a35]">Daily Journal</h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-[#746956]">Notes saved from conversations with Adeline live here by day. These are memory pages, not assignments.</p>
          </div>
          <BookOpen className="mt-8 text-[#92506e]" size={28} />
        </div>

        {grouped.length === 0 ? (
          <div className="rounded-[26px_17px_26px_20px] border border-dashed border-[#bfae92] bg-[#fffaf0] p-10 text-center">
            <p className="font-serif text-xl">The first page is still blank.</p>
            <p className="mt-2 text-sm text-[#766b58]">Ask Adeline a question, then save a sketchnote when one is worth keeping.</p>
          </div>
        ) : (
          <div className="space-y-10">
            {grouped.map(([day, dayNotes]) => (
              <section key={day}>
                <div className="mb-4 flex items-center gap-3">
                  <div className="h-px flex-1 bg-[#cdbfa9]" />
                  <h2 className="rotate-[-.5deg] font-serif text-lg text-[#5e543f]">{dayLabel(dayNotes[0]?.created_at ?? null)}</h2>
                  <div className="h-px flex-1 bg-[#cdbfa9]" />
                </div>
                <div className="grid gap-5 xl:grid-cols-2">
                  {dayNotes.map((entry) => entry.note ? (
                    <SketchnoteCard key={entry.id} note={entry.note} />
                  ) : (
                    <article key={entry.id} className="rounded-[18px_11px_20px_12px] border border-[#cdbfa9] bg-[#fffdf5] p-5 shadow-sm">
                      <p className="text-[10px] uppercase tracking-[.16em] text-[#9a7a43]">field note</p>
                      <h3 className="mt-1 font-serif text-xl text-[#2b4b36]">{entry.topic}</h3>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[#5c655c]">{entry.learned}</p>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
