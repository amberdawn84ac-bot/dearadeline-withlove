'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan } from '@/lib/brain-client';
import type { BookRecommendation, LessonSuggestion, ProjectSuggestion } from '@/lib/brain-client';
import styles from '@/components/nav/sites-dashboard.module.css';

export default function TodayPage() {
  const { student, loading: studentLoading } = useStudent();
  const [tasks, setTasks] = useState<LessonSuggestion[]>([]);
  const [projects, setProjects] = useState<ProjectSuggestion[]>([]);
  const [books, setBooks] = useState<BookRecommendation[]>([]);
  const [planLoading, setPlanLoading] = useState(true);
  const [error, setError] = useState('');

  const studentId = student?.id ?? '';

  const loadToday = useCallback(async () => {
    if (!studentId) return;
    setPlanLoading(true);
    try {
      const plan = await getLearningPlan(studentId, 6);
      setTasks((plan.suggestions ?? []).slice(0, 4));
      setProjects((plan.projects ?? []).slice(0, 1));
      setBooks((plan.recommended_books ?? []).slice(0, 1));
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
        <span>A balanced daily itinerary drawn from the larger learning plan. Open each task when you are ready to work.</span>
      </header>

      {error && <p className={styles.error} role="alert">{error}</p>}

      <section className={styles.dailyAgenda} aria-label="Today's complete learning agenda">
          {tasks.map((task, index) => (
            <article key={task.id} className={styles.agendaCard}>
              <div className={styles.agendaNumber}>{index + 1}</div>
              <div className={styles.agendaBody}>
                <small>{task.track.replace(/_/g, ' ')}</small>
                <h2>{task.emoji} {task.title}</h2>
                <p>{task.description}</p>
                {task.personalization_reason && <em>Why today: {task.personalization_reason}</em>}
                {task.success_criteria?.length > 0 && (
                  <ul>{task.success_criteria.slice(0, 3).map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
                )}
              </div>
              <Link href={`/dashboard/lesson/${encodeURIComponent(task.id)}`}>Open task →</Link>
            </article>
          ))}
          {projects.map((project) => (
            <article key={`project-${project.id}`} className={styles.agendaCard}>
              <div className={styles.agendaNumber}>⚒</div>
              <div className={styles.agendaBody}><small>Project workshop · {project.track.replace(/_/g, ' ')}</small><h2>{project.emoji} {project.title}</h2><p>{project.tagline}</p><em>Estimated project time: {project.estimated_hours} hours. Touch the next manageable step today.</em></div>
              <Link href={`/dashboard/projects/${project.id}`}>Open project →</Link>
            </article>
          ))}
          {books.map((book) => (
            <article key={`book-${book.id}`} className={styles.agendaCard}>
              <div className={styles.agendaNumber}>▤</div>
              <div className={styles.agendaBody}><small>Reading · {book.track.replace(/_/g, ' ')}</small><h2>{book.title}</h2><p>By {book.author}{book.grade_band ? ` · ${book.grade_band}` : ''}</p><em>Read or continue a meaningful section today.</em></div>
              <Link href={`/dashboard/reading-nook/${book.id}`}>Open book →</Link>
            </article>
          ))}
          {!tasks.length && !projects.length && !books.length && <div className={styles.agendaCard}><div className={styles.agendaBody}><h2>Today is open.</h2><p>Ask Adeline what you want to explore, or tell her about something real you completed.</p></div></div>}
      </section>
    </div>
  );
}
