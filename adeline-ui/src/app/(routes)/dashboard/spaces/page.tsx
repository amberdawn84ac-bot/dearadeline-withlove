'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan, getSavedTodayPlan, listSpaces } from '@/lib/brain-client';
import type { SpaceListItem, UpcomingInvestigation } from '@/lib/brain-client';
import styles from '@/components/nav/sites-dashboard.module.css';

export default function SpacesListPage() {
  const { student, loading: studentLoading } = useStudent();
  const [spaces, setSpaces] = useState<SpaceListItem[]>([]);
  const [upcoming, setUpcoming] = useState<UpcomingInvestigation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const studentId = student?.id ?? '';

  const load = useCallback(async () => {
    if (!studentId) return;
    setLoading(true);
    setError('');
    try {
      const [spacesList, plan] = await Promise.all([
        listSpaces(studentId),
        getSavedTodayPlan(studentId).then((saved) => saved ?? getLearningPlan(studentId, 6)),
      ]);
      setSpaces(spacesList);
      setUpcoming(plan.upcoming_family_investigations ?? []);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Adeline could not load your Spaces yet.');
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => { void load(); }, [load]);

  if (studentLoading || loading) return <div className={styles.loading}>Adeline is gathering your Spaces…</div>;
  if (!student) return <div className={styles.loading}>Your session has ended. Please sign in again.</div>;

  const active = spaces.filter((item) => item.status === 'active');
  const completed = spaces.filter((item) => item.status === 'completed');

  return (
    <div className={styles.todayWorkspace}>
      <header className={styles.todayTitle}>
        <p>Every unit Space you&apos;ve opened</p>
        <h1>Your Spaces</h1>
        <span>Active Spaces are still in progress. Completed ones stay open — you can keep talking with Adeline in any of them.</span>
      </header>

      {error && <p className={styles.error} role="alert">{error}</p>}

      <section className={styles.kanban} aria-label="Your Spaces">
        <div className={`${styles.kanbanColumn} ${styles.kanbanToday}`}>
          <header><span>1</span><div><small>In progress</small><h2>Active</h2></div></header>
          {active.length ? active.map((space) => <SpaceCard key={space.plan_item_id} space={space} />)
            : <EmptyCard text="No active Spaces right now." />}
        </div>

        <div className={styles.kanbanColumn}>
          <header><span>✓</span><div><small>Still open for conversation</small><h2>Completed</h2></div></header>
          {completed.length ? completed.map((space) => <SpaceCard key={space.plan_item_id} space={space} />)
            : <EmptyCard text="Nothing completed yet." />}
        </div>

        <div className={styles.kanbanColumn}>
          <header><span>…</span><div><small>Not started yet</small><h2>Up Next</h2></div></header>
          {upcoming.length ? upcoming.map((item) => <article key={`${item.slot}-${item.position}`} className={`${styles.kanbanCard} ${styles.emptyKanban}`}>
            <small>{item.slot} · {item.track.replace(/_/g, ' ')}</small>
            <h3>{item.canonical_topic}</h3>
            <p>Queued — begins once the current {item.slot} investigation is finished.</p>
          </article>) : <EmptyCard text="Nothing queued beyond what's active now." />}
        </div>
      </section>
    </div>
  );
}

function SpaceCard({ space }: { space: SpaceListItem }) {
  const progress = space.total_blocks ? Math.round((space.completed_blocks / space.total_blocks) * 100) : 0;
  return <article className={styles.kanbanCard}>
    <small>{space.track.replace(/_/g, ' ')}</small>
    <h3>{space.title}</h3>
    <p>{progress}% explored{space.updated_at ? ` · last active ${new Date(space.updated_at).toLocaleDateString()}` : ''}</p>
    <Link href={`/dashboard/spaces/${encodeURIComponent(space.plan_item_id)}`}>{space.status === 'completed' ? 'Reopen this Space →' : 'Continue this Space →'}</Link>
  </article>;
}

function EmptyCard({ text }: { text: string }) {
  return <div className={`${styles.kanbanCard} ${styles.emptyKanban}`}><p>{text}</p></div>;
}
