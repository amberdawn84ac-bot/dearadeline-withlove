'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan, getRecentTranscript } from '@/lib/brain-client';
import type { LessonSuggestion, TranscriptEntry } from '@/lib/brain-client';
import styles from '@/components/nav/sites-dashboard.module.css';

export default function TodayPage() {
  const { student, loading: studentLoading } = useStudent();
  const [today, setToday] = useState<LessonSuggestion | null>(null);
  const [weekTheme, setWeekTheme] = useState('');
  const [sharedWithSiblings, setSharedWithSiblings] = useState(false);
  const [comingUp, setComingUp] = useState<LessonSuggestion[]>([]);
  const [finished, setFinished] = useState<TranscriptEntry[]>([]);
  const [isNextSchoolDay, setIsNextSchoolDay] = useState(false);
  const [planLoading, setPlanLoading] = useState(true);
  const [error, setError] = useState('');

  const studentId = student?.id ?? '';

  const loadToday = useCallback(async () => {
    if (!studentId) return;
    setPlanLoading(true);
    try {
      const [plan, recent] = await Promise.all([
        getLearningPlan(studentId, 6),
        getRecentTranscript(studentId, 4).catch(() => []),
      ]);
      const lineup = plan.suggestions;
      setToday(lineup[0] ?? null);
      setWeekTheme(lineup[0]?.title ?? 'Family investigation');
      setSharedWithSiblings(plan.family_context.shared_with_siblings);
      setComingUp(lineup.slice(1, 4));
      setFinished(recent);
      setIsNextSchoolDay(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Adeline could not load today yet.');
    } finally {
      setPlanLoading(false);
    }
  }, [studentId]);

  useEffect(() => { void loadToday(); }, [loadToday]);

  if (studentLoading || planLoading) return <div className={styles.loading}>Adeline is arranging today&apos;s work…</div>;
  if (!student) return <div className={styles.loading}>Your session has ended. Please sign in again.</div>;

  return (
    <div className={styles.todayWorkspace}>
      <header className={styles.todayTitle}>
        <p>{isNextSchoolDay ? 'Your next school day' : 'Ready when you are'}</p>
        <h1>{isNextSchoolDay ? 'Coming up next' : 'Today'}</h1>
        <span>{weekTheme} · {sharedWithSiblings ? 'Shared living investigation; it takes as long as the question needs, while each learner’s work and credits remain individual.' : 'This view changes whenever the living learning plan changes.'}</span>
      </header>

      {error && <p className={styles.error} role="alert">{error}</p>}

      <section className={styles.kanban} aria-label="Today's learning board">
        <div className={`${styles.kanbanColumn} ${styles.kanbanToday}`}>
          <header><span>1</span><div><small>Right now</small><h2>Today</h2></div></header>
          {today ? <article className={styles.kanbanCard}>
            <small>{today.track.replace(/_/g, ' ')}</small>
            <h3>{today.emoji} {today.title}</h3>
            <p>{today.description}</p>
            <Link href={`/dashboard/lesson/${encodeURIComponent(today.id)}`}>Begin →</Link>
          </article> : <EmptyCard text="The next plan is being arranged." />}
        </div>

        <div className={styles.kanbanColumn}>
          <header><span>2</span><div><small>This investigation</small><h2>Coming Up</h2></div></header>
          {comingUp.map((mission) => <article key={mission.id} className={styles.kanbanCard}>
            <small>{mission.track.replace(/_/g, ' ')}</small><h3>{mission.emoji} {mission.title}</h3>
            <p>{mission.description}</p>
          </article>)}
          {!comingUp.length && <EmptyCard text="Nothing else is queued for this week." />}
        </div>

        <div className={styles.kanbanColumn}>
          <header><span>✓</span><div><small>Real recorded evidence</small><h2>Finished</h2></div></header>
          {finished.map((entry) => <article key={entry.id} className={`${styles.kanbanCard} ${styles.finishedCard}`}>
            <small>{entry.track.replace(/_/g, ' ')}</small><h3>✓ {entry.courseTitle}</h3>
            <p>{entry.completedAt ? new Date(entry.completedAt).toLocaleDateString() : 'Recorded in the learning journal'}</p>
          </article>)}
          {!finished.length && <EmptyCard text="Completed lessons appear here after evidence is recorded." />}
        </div>
      </section>
      <p className={styles.planFootnote}><Link href="/dashboard/portfolio">See what you have made and learned →</Link></p>
    </div>
  );
}

function EmptyCard({ text }: { text: string }) {
  return <div className={`${styles.kanbanCard} ${styles.emptyKanban}`}><p>{text}</p></div>;
}
