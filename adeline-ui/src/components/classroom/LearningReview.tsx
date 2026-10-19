'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Feedback, reviewClassroomResponse } from '@/lib/classroom-client';

export default function LearningReviewPanel({ feedback, studentId, itemId, track }: { feedback: Feedback; studentId: string; itemId: string; track: string }) {
  const [review, setReview] = useState(feedback.assessment);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function retry() {
    if (!feedback.submission_key) return;
    setBusy(true); setError('');
    try { setReview(await reviewClassroomResponse(studentId, itemId, feedback.submission_key)); }
    catch { setError('Your work is saved. The review is unavailable; try again later.'); }
    finally { setBusy(false); }
  }
  return <section aria-label="Learning review" className="mt-4 space-y-3 rounded-2xl border border-[#bba978] bg-[#fff9ec] p-5">
    <h3 className="font-semibold">What your work shows</h3>
    {review ? <><p>{review.message}</p>{review.findings.map(f => <article key={f.skill_id} className="space-y-2 border-t border-[#d9cfbc] pt-3">
      <p className="font-semibold">{f.result === 'demonstrated' ? 'Demonstrated in this attempt' : f.result === 'developing' ? 'Keep working on this' : 'Needs another look'}</p>
      <p>{f.reasoning}</p><blockquote className="border-l-2 border-[#bba978] pl-3">{f.evidence_quote}</blockquote>
      <p>{f.next_step}</p>
      {f.result !== 'demonstrated' && <Link className="inline-flex min-h-11 items-center rounded-xl border px-4" href={`/dashboard/lesson/new-gap-${encodeURIComponent(f.skill_id)}?${new URLSearchParams({ topic: f.next_step.slice(0, 500), target: f.skill_id, track })}`}>Practice this next</Link>}
    </article>)}</> : <p>Your work is saved. Its learning review is separate from saving and course credit.</p>}
    {!review && feedback.submission_key && <button onClick={() => void retry()} disabled={busy} className="min-h-11 rounded-xl border px-4 disabled:opacity-50">{busy ? 'Reviewing your work…' : 'Review my saved work'}</button>}
    {error && <p role="alert">{error}</p>}
    <Link className="inline-flex min-h-11 items-center font-semibold underline" href="/dashboard">Return to my plan</Link>
  </section>;
}
