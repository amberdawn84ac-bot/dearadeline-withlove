'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { listClassrooms } from '@/lib/classroom-client';
import { AdelineConversationCard } from '@/components/AdelineConversationCard';
import styles from '@/components/nav/sites-dashboard.module.css';

export default function TodayPage() {
  const { student, loading } = useStudent();
  const [items, setItems] = useState<Array<{ item_id: string; title: string; phase: string }>>([]);
  const [error, setError] = useState('');
  const [newId, setNewId] = useState('');
  useEffect(() => { setNewId(`new-${crypto.randomUUID()}`); }, []);
  useEffect(() => {
    if (!student?.id) return;
    let active = true;
    setItems([]);
    setError('');
    listClassrooms(student.id).then((rows) => { if (active) setItems(rows); })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load classrooms.'); });
    return () => { active = false; };
  }, [student?.id]);

  if (loading) return <div className={styles.loading}>Opening your learning day…</div>;
  if (!student) return <div className={styles.loading}>Your session has ended. Please sign in again.</div>;

  return <div className={styles.todayWorkspace}>
    <header className={styles.todayTitle}><h1>Today</h1></header>
    <AdelineConversationCard studentId={student.id} gradeLevel={student.gradeLevel ?? '8'} heightClass="h-[440px]" label="Talk with Adeline" />
    <section className="mt-7 rounded-3xl bg-[#183d32] p-7 text-[#fff9ec]" aria-label="Start a classroom">
      <h2 className="text-3xl">What do you want to understand?</h2>
      <p className="mt-3">Choose a topic. Review Adeline’s plan, then explore it together through explanations, experiments, questions, and projects.</p>
      {newId && <Link href={`/dashboard/lesson/${newId}`} className="mt-5 inline-block rounded-xl bg-[#d8b976] px-5 py-3 font-semibold text-[#183d32]">Create a classroom →</Link>}
    </section>
    <section className="mt-7" aria-label="Your classrooms">
      <h2 className="text-2xl text-[#183d32]">Your classrooms</h2>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">{items.map((item) => <Link key={item.item_id} href={`/dashboard/lesson/${encodeURIComponent(item.item_id)}`} className="rounded-2xl border border-[#d9cfbc] bg-[#fffdf7] p-5 text-[#183d32]">
        <h3 className="text-xl">{item.title}</h3>
        <p className="mt-2 text-sm">{item.phase === 'ready' ? 'Open classroom' : item.phase === 'planned' ? 'Review your plan' : item.phase === 'failed' ? 'Resume building' : 'Building…'}</p>
      </Link>)}</div>
      {!items.length && !error && <p className="mt-4 text-[#183d32]">Create your first classroom above.</p>}
    </section>
    <p className={styles.planFootnote}><Link href="/dashboard/classrooms">Browse your classrooms →</Link>{' · '}<Link href="/dashboard/portfolio">Your portfolio →</Link></p>
  </div>;
}
