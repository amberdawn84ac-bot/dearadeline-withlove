'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useStudent } from '@/lib/useStudent';
import { listClassrooms } from '@/lib/classroom-client';

export default function ClassroomsPage() {
  const { student, loading } = useStudent();
  const [items, setItems] = useState<Array<{item_id:string;title:string;phase:string}>>([]);
  const [error, setError] = useState('');
  const [newId, setNewId] = useState('');
  useEffect(() => { setNewId(`new-${crypto.randomUUID()}`); }, []);
  useEffect(() => {
    if (!student) return;
    let active = true;
    listClassrooms(student.id).then(rows => { if (active) setItems(rows); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load classrooms.'); });
    return () => { active = false; };
  }, [student]);
  if (loading) return <p>Opening your classrooms…</p>;
  if (!student) return <p>Please sign in to open your classrooms.</p>;
  return <main className="mx-auto max-w-5xl space-y-7 text-[#183d32]"><header className="rounded-3xl bg-[#183d32] p-8 text-[#fff9ec]"><p className="text-xs uppercase tracking-[.25em]">Dear Adeline</p><h1 className="mt-3 text-4xl">Your classrooms</h1><p className="mt-4">Explore, make, question, and learn with Adeline.</p>{newId && <Link href={`/dashboard/lesson/${newId}`} className="mt-6 inline-block rounded-xl bg-[#d8b976] px-5 py-3 font-semibold text-[#183d32]">Create a classroom</Link>}</header>{error && <p role="alert">{error}</p>}<div className="grid gap-5 sm:grid-cols-2">{items.map(item => <Link key={item.item_id} href={`/dashboard/lesson/${encodeURIComponent(item.item_id)}`} className="rounded-2xl border border-[#d9cfbc] bg-[#fffdf7] p-6"><h2 className="text-2xl">{item.title}</h2><p className="mt-3 text-sm">{item.phase === 'ready' ? 'Open classroom' : item.phase === 'planned' ? 'Review your plan' : item.phase === 'failed' ? 'Resume building' : 'Building…'}</p></Link>)}</div>{!items.length && !error && <p>Your new classrooms will appear here.</p>}</main>;
}
