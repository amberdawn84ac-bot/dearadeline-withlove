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
  const [sharedWithSiblings, setSharedWithSiblings] = useState(false);
  const [individualLessons, setIndividualLessons] = useState<IndividualLesson[]>([]);
  const [finished, setFinished] = useState<TranscriptEntry[]>([]);
  const [isNextSchoolDay, setIsNextSchoolDay] = useState(false);
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
    setSharedWithSiblings(plan.family_context.shared_with_siblings);
    setIndividualLessons(plan.individual_lessons ?? []);
    setIsNextSchoolDay(false);
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

  return (
    <div className={styles.todayWorkspace}>
      <header className={styles.todayTitle}>
        <p>{isNextSchoolDay ? 'Your next school day' : 'Ready when you are'}</p>
        <h1>{isNextSchoolDay ? 'Coming up next' : 'Today'}</h1>
        <span>
          {sharedWithSiblings
            ? 'Two family investigations run side by side — science in the kitchen and field, history from real records. Each child keeps their own work and credits.'
            : 'Two family investigations run side by side — science in the kitchen and field, history from real records.'}
        </span>
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

      <section className={styles.kanban} aria-label="Today's learning board">
        <div className={`${styles.kanbanColumn} ${styles.kanbanToday}`}>
          <header><span>1</span><div><small>In the kitchen and the field</small><h2>Science together</h2></div></header>
          {scienceInvestigations.length
            ? scienceInvestigations.map((investigation) => <InvestigationCard key={investigation.id} investigation={investigation} />)
            : <EmptyCard text="No science investigation is open yet." />}
        </div>

        <div className={`${styles.kanbanColumn} ${styles.kanbanToday}`}>
          <header><span>2</span><div><small>A real case from the records</small><h2>History together</h2></div></header>
          {historyInvestigations.length
            ? historyInvestigations.map((investigation) => <InvestigationCard key={investigation.id} investigation={investigation} />)
            : <EmptyCard text="No history investigation is open yet." />}
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
      {individualLessons.length > 0 && (
        <section className={styles.practiceStrip} aria-label="This learner's lessons">
          <header>
            <p>After the family work</p>
            <h2>Your lessons</h2>
            <span>The same investigations, broken into the part this learner does.</span>
          </header>
          {groupedLessons(individualLessons).map((group) => (
            <div key={group.id}>
              <h3 className="mb-2 mt-4 text-sm font-black text-[#2F4731]">{group.title}</h3>
              <div className={styles.practiceCards}>
                {group.lessons.map((lesson) => (
                  <article key={lesson.id} className={styles.kanbanCard}>
                    <small>Lesson {lesson.index} of {lesson.count}</small>
                    <h3>{lesson.title}</h3>
                    <p>{lesson.assignment}</p>
                    <Link href={`/dashboard/lesson/${encodeURIComponent(lesson.investigation_id)}#lesson-${encodeURIComponent(lesson.lesson_id)}`}>Open this lesson →</Link>
                  </article>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}
      <p className={styles.planFootnote}>
        <Link href="/dashboard/spaces">Browse all your Spaces →</Link>
        {' · '}
        <Link href="/dashboard/portfolio">See what you have made and learned →</Link>
      </p>
    </div>
  );
}

function groupedLessons(lessons: IndividualLesson[]) {
  const groups: Array<{ id: string; title: string; lessons: IndividualLesson[] }> = [];
  for (const lesson of lessons) {
    const existing = groups.find((group) => group.id === lesson.investigation_id);
    if (existing) existing.lessons.push(lesson);
    else groups.push({ id: lesson.investigation_id, title: lesson.investigation_title, lessons: [lesson] });
  }
  return groups;
}

function InvestigationCard({ investigation }: { investigation: LessonSuggestion }) {
  const question = (investigation.driving_question || '').trim();
  const hook = (investigation.description || '').trim();
  const showHook = hook && hook.length <= 220 && hook !== question;
  return (
    <article className={styles.kanbanCard}>
      <small>{investigation.track.replace(/_/g, ' ')}</small>
      <h3>{investigation.title}</h3>
      {question ? <p><strong>The question:</strong> {question}</p> : null}
      {showHook ? <p>{hook}</p> : null}
      <Link href={`/dashboard/spaces/${encodeURIComponent(investigation.id)}`}>Start this investigation →</Link>
    </article>
  );
}

function EmptyCard({ text }: { text: string }) {
  return <div className={`${styles.kanbanCard} ${styles.emptyKanban}`}><p>{text}</p></div>;
}
