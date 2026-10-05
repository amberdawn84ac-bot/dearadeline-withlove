'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan, getRecentTranscript, getSavedTodayPlan, peekLearningPlan } from '@/lib/brain-client';
import type { IndividualLesson, LearningPlanResponse, LessonSuggestion, TranscriptEntry } from '@/lib/brain-client';
import { AdelineConversationCard } from '@/components/AdelineConversationCard';
import styles from '@/components/nav/sites-dashboard.module.css';

export default function TodayPage() {
  const { student, loading: studentLoading } = useStudent();
  const [todayInvestigations, setTodayInvestigations] = useState<LessonSuggestion[]>([]);
  const [individualLessons, setIndividualLessons] = useState<IndividualLesson[]>([]);
  const [finished, setFinished] = useState<TranscriptEntry[]>([]);
  const [planLoading, setPlanLoading] = useState(true);
  const [error, setError] = useState('');

  const studentId = student?.id ?? '';

  const applyPlan = useCallback((plan: LearningPlanResponse) => {
    const lineup = plan.suggestions;
    const families = plan.family_investigations?.length
      ? plan.family_investigations
      : plan.family_investigation
        ? [plan.family_investigation]
        : lineup.filter((item) => item.delivery_mode === 'FAMILY_INVESTIGATION');
    setTodayInvestigations(families);
    setIndividualLessons(plan.individual_lessons ?? []);
  }, []);

  const loadToday = useCallback(async () => {
    if (!studentId) return;
    const knownPlan = peekLearningPlan(studentId);
    if (knownPlan) {
      applyPlan(knownPlan);
      setPlanLoading(false);
    } else {
      setPlanLoading(true);
    }
    setError('');
    try {
      // This endpoint is a pure durable read. Only a genuinely missing current-
      // day record is allowed to enter the planner/generation path.
      const saved = await getSavedTodayPlan(studentId);
      const plan = saved ?? await getLearningPlan(studentId, 6);
      applyPlan(plan);
      void getRecentTranscript(studentId, 4).then(setFinished).catch(() => undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Adeline could not load today yet.');
    } finally {
      setPlanLoading(false);
    }
  }, [applyPlan, studentId]);

  useEffect(() => { void loadToday(); }, [loadToday]);

  if (studentLoading || planLoading) return <div className={styles.loading}>Adeline is arranging today's work…</div>;
  if (!student) return <div className={styles.loading}>Your session has ended. Please sign in again.</div>;

  const scienceInvestigations = todayInvestigations.filter((item) => (item.slot || '').toLowerCase() === 'science'
    || (!item.slot && item.track !== 'TRUTH_HISTORY' && item.track !== 'JUSTICE_CHANGEMAKING'));
  const historyInvestigations = todayInvestigations.filter((item) => (item.slot || '').toLowerCase() === 'history'
    || (!item.slot && (item.track === 'TRUTH_HISTORY' || item.track === 'JUSTICE_CHANGEMAKING')));
  const day = campfireDay(individualLessons, scienceInvestigations, historyInvestigations);

  return (
    <div className={styles.todayWorkspace}>
      <header className={styles.todayTitle}>
        <h1>Today</h1>
      </header>

      {error && <p className={styles.error} role="alert">{error}</p>}

      <div className="mb-6">
        <AdelineConversationCard
          studentId={student.id}
          gradeLevel={student.gradeLevel ?? '8'}
          heightClass="h-[440px]"
          label="Talk with Adeline"
        />
      </div>

      <section className={styles.dayBoard} aria-label="Today's lesson">
        <div className={`${styles.kanbanColumn} ${styles.kanbanToday}`}>
          <header><div><h2>Today&rsquo;s lesson</h2></div></header>
          {day.current ? (
            <article className={styles.kanbanCard}>
              {day.current.count > 1 && <small>Lesson {day.current.index} of {day.current.count}</small>}
              {day.current.investigation_title !== day.current.title && <small>{day.current.investigation_title}</small>}
              <h3>{day.current.title}</h3>
              {day.current.assignment && <p>{day.current.assignment}</p>}
              <Link href={lessonHref(day.current)}>Open this lesson →</Link>
            </article>
          ) : day.unit ? (
            <InvestigationCard investigation={day.unit} />
          ) : <EmptyCard text="No unit is open yet." />}
          {day.cores.length > 0 && (
            <article className={styles.kanbanCard}>
              <h3>Your core work</h3>
              <ul>
                {day.cores.map(({ activity }) => <li key={activity.suggestion_id}>
                  <b>{activity.skill_title}.</b> {activity.activity}
                </li>)}
              </ul>
            </article>
          )}
          {day.toc.length > 1 && (
            <article className={styles.kanbanCard}>
              <h3>Table of contents</h3>
              <ul>
                {day.toc.map((lesson) => <li key={lesson.id}>
                  {lesson.index === day.current?.index ? <b>{lesson.index}. {lesson.title} — today</b> : `${lesson.index}. ${lesson.title}`}
                </li>)}
              </ul>
            </article>
          )}
          {day.inOrder.map((lesson) => (
            <article key={lesson.id} className={styles.kanbanCard}>
              <h3>{lesson.title}</h3>
              {studentTask(lesson) && <p>{studentTask(lesson)}</p>}
              <Link href={lessonHref(lesson)}>Open this lesson →</Link>
            </article>
          ))}
          {day.nextChapter && (
            <article className={styles.kanbanCard}>
              <h3>Next chapter</h3>
              <p>{day.nextChapter.title}</p>
            </article>
          )}
        </div>

        <div className={styles.kanbanColumn}>
          <header><div><h2>Finished</h2></div></header>
          {finished.map((entry) => <article key={entry.id} className={`${styles.kanbanCard} ${styles.finishedCard}`}>
            <h3>✓ {entry.courseTitle}</h3>
            <p>{entry.completedAt ? new Date(entry.completedAt).toLocaleDateString() : 'Saved in your portfolio'}</p>
          </article>)}
          {!finished.length && <EmptyCard text="Your finished lessons will appear here." />}
        </div>
      </section>
      <p className={styles.planFootnote}>
        <Link href="/dashboard/spaces">Browse all your Spaces →</Link>
        {' · '}
        <Link href="/dashboard/portfolio">See what you have made and learned →</Link>
      </p>
    </div>
  );
}

function campfireDay(
  lessons: IndividualLesson[],
  science: LessonSuggestion[],
  history: LessonSuggestion[],
) {
  const unitLessons = lessons.filter((lesson) => lesson.kind !== 'gap');
  const unitId = unitLessons[0]?.investigation_id;
  const toc = unitLessons.filter((lesson) => lesson.investigation_id === unitId);
  const current = toc[0];
  const inOrder = lessons.filter((lesson) => lesson.kind === 'gap');
  const cores = toc.flatMap((lesson) => (lesson.core_activities ?? []).map((activity) => ({ activity, lesson })));
  const unit = science.find((item) => item.id === unitId || item.title === current?.investigation_title) ?? science[0];
  const nextChapter = history.find((item) => item.title !== current?.investigation_title && item.id !== current?.investigation_id) ?? null;
  return { current, toc, inOrder, cores, unit, nextChapter };
}

function studentTask(lesson: IndividualLesson) {
  // Old durable Today records contain planner rationale in this field. Hide
  // only that known template; keep real assignments from saved lessons.
  if (lesson.kind === 'gap' && /^Today's .+ mini lesson[.,]/.test(lesson.assignment)) return '';
  return lesson.assignment;
}

function lessonHref(lesson: IndividualLesson) {
  if (lesson.kind === 'gap') return `/dashboard/lesson/${encodeURIComponent(lesson.investigation_id)}`;
  return `/dashboard/lesson/${encodeURIComponent(lesson.investigation_id)}#lesson-${encodeURIComponent(lesson.lesson_id)}`;
}

function InvestigationCard({ investigation }: { investigation: LessonSuggestion }) {
  const question = (investigation.driving_question || '').trim();
  const hook = (investigation.description || '').trim();
  const showHook = hook && hook.length <= 220 && hook !== question;
  return (
    <article className={styles.kanbanCard}>
      <h3>{investigation.title}</h3>
      {question ? <p>{question}</p> : null}
      {showHook ? <p>{hook}</p> : null}
      <Link href={`/dashboard/spaces/${encodeURIComponent(investigation.id)}`}>Start this investigation →</Link>
    </article>
  );
}

function EmptyCard({ text }: { text: string }) {
  return <div className={`${styles.kanbanCard} ${styles.emptyKanban}`}><p>{text}</p></div>;
}
