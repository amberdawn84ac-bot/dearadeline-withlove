'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, BookOpen, Download, FileText, Loader2, Sparkles } from 'lucide-react';
import { downloadMasteryPortfolio, listActivities } from '@/lib/brain-client';
import type { ActivityEntry } from '@/lib/brain-client';
import { useStudent } from '@/lib/useStudent';
import { listDailyJournalNotes, type DailyJournalNote } from '@/lib/journal-client';

export default function PortfolioPage() {
  const { student, loading: studentLoading } = useStudent();
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [notes, setNotes] = useState<DailyJournalNote[]>([]);
  const [totalCredits, setTotalCredits] = useState(0);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!student) return;
    setLoading(true);
    Promise.allSettled([
      listActivities(student.id),
      listDailyJournalNotes(student.id, 12),
    ]).then(([activitiesResult, notesResult]) => {
      if (activitiesResult.status === 'fulfilled') {
        setActivities(activitiesResult.value.activities);
        setTotalCredits(activitiesResult.value.total_credits);
      }
      if (notesResult.status === 'fulfilled') setNotes(notesResult.value);
    }).finally(() => setLoading(false));
  }, [student]);

  async function download() {
    if (!student) return;
    setDownloading(true);
    try {
      const blob = await downloadMasteryPortfolio(student.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `dear-adeline-portfolio-${student.name || 'student'}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  if (studentLoading || loading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f4eddf] text-[#244a35]"><Loader2 className="h-5 w-5 animate-spin" /></div>;
  }

  return (
    <main className="min-h-screen bg-[#f4eddf] px-4 py-6 text-[#2d4333] sm:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-start justify-between gap-5">
          <div>
            <Link href="/dashboard" className="inline-flex items-center gap-1 text-xs text-[#746851] hover:text-[#244a35]"><ArrowLeft size={14} /> back to Adeline</Link>
            <p className="mt-5 text-[10px] uppercase tracking-[.22em] text-[#9a7b42]">proof of the work</p>
            <h1 className="mt-1 font-serif text-4xl text-[#244a35]">Portfolio</h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#706858]">Not a scrapbook of assignments. This is the record of what you actually made, repaired, investigated, read, grew, tested, wrote, and figured out.</p>
          </div>
          <button onClick={() => void download()} disabled={downloading || !student} className="mt-9 flex items-center gap-2 rounded-full border border-[#c9b99c] bg-[#fffaf0] px-4 py-2 text-xs font-semibold text-[#385440] shadow-sm disabled:opacity-40">{downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} portfolio PDF</button>
        </div>

        <section className="mt-8 grid gap-4 md:grid-cols-3">
          <Stat number={activities.length} label="real-world evidence pieces" jewel="#315f7b" />
          <Stat number={notes.length} label="saved thinking pages" jewel="#8f4868" />
          <Stat number={Number(totalCredits.toFixed(2))} label="credits quietly recognized" jewel="#9c7724" />
        </section>

        {activities.length === 0 && notes.length === 0 ? (
          <div className="mt-8 rounded-[28px_17px_30px_20px] border border-dashed border-[#bfae92] bg-[#fffaf0] p-12 text-center">
            <Sparkles className="mx-auto text-[#9c7724]" size={24} />
            <h2 className="mt-4 font-serif text-2xl">There is nothing to display yet.</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-[#756a58]">Tell Adeline what you&apos;ve been doing. The portfolio should grow out of your life, not from filling in portfolio boxes.</p>
          </div>
        ) : (
          <div className="mt-9 grid gap-8 lg:grid-cols-[1.4fr_.8fr]">
            <section>
              <div className="mb-4"><p className="text-[10px] uppercase tracking-[.18em] text-[#967742]">things that happened</p><h2 className="mt-1 font-serif text-2xl">Evidence</h2></div>
              <div className="space-y-4">
                {activities.map((activity, index) => (
                  <article key={activity.activity_id} className="relative overflow-hidden rounded-[22px_14px_25px_16px] border border-[#d0c2aa] bg-[#fffaf0] p-5 shadow-[0_5px_18px_rgba(74,57,35,.05)]">
                    <div className="absolute right-4 top-4 h-2.5 w-2.5 rounded-full" style={{ background: index % 3 === 0 ? '#315f7b' : index % 3 === 1 ? '#8f4868' : '#9c7724' }} />
                    <p className="text-[10px] uppercase tracking-[.15em] text-[#9a7a43]">{new Date(activity.activity_date || activity.sealed_at).toLocaleDateString()}</p>
                    <h3 className="mt-1 pr-8 font-serif text-xl text-[#294936]">{activity.course_title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#687064]">{activity.activity_description}</p>
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-dashed border-[#cdbfa8] pt-3 text-[10px] text-[#786c58]"><span>{activity.credit_hours} credit hrs recognized</span><span>·</span><span>{activity.credit_type.toLowerCase()}</span></div>
                  </article>
                ))}
              </div>
            </section>

            <aside>
              <div className="mb-4"><p className="text-[10px] uppercase tracking-[.18em] text-[#967742]">thoughts worth keeping</p><h2 className="mt-1 font-serif text-2xl">From the journal</h2></div>
              <div className="space-y-3">
                {notes.slice(0, 8).map((note) => (
                  <Link key={note.id} href="/dashboard/journal" className="block rotate-[-.25deg] rounded-[17px_10px_18px_12px] border border-[#d1c3aa] bg-[#fffdf5] p-4 transition hover:-translate-y-0.5">
                    <div className="flex items-start gap-3"><BookOpen size={15} className="mt-1 shrink-0 text-[#92506e]" /><div><p className="font-serif text-base text-[#2b4936]">{note.topic}</p><p className="mt-1 line-clamp-3 text-xs leading-relaxed text-[#756b59]">{note.note?.big_idea || note.learned}</p></div></div>
                  </Link>
                ))}
                {notes.length === 0 && <div className="rounded-[18px_12px_19px_13px] border border-dashed border-[#c7b89e] p-5 text-sm text-[#756b59]"><FileText size={17} className="mb-2" />Saved sketchnotes and field notes will appear here.</div>}
              </div>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}

function Stat({ number, label, jewel }: { number: number; label: string; jewel: string }) {
  return <div className="rounded-[22px_15px_24px_17px] border border-[#d1c4ad] bg-[#fffaf0] p-5"><span className="block h-2.5 w-2.5 rounded-full" style={{ background: jewel, boxShadow: `0 0 12px ${jewel}55` }} /><p className="mt-3 font-serif text-3xl text-[#2a4936]">{number}</p><p className="mt-1 text-xs text-[#7a6e5b]">{label}</p></div>;
}
