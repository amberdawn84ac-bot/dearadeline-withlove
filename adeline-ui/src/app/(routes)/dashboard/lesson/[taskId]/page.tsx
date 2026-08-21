'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import FamilyCanonicalLesson from '@/components/lessons/FamilyCanonicalLesson';
import { buildLesson, getLearningPlan, lessonRequestFromSuggestion } from '@/lib/brain-client';
import type { LessonBlockResponse, LessonResponse, LessonSuggestion } from '@/lib/brain-client';
import { useStudent } from '@/lib/useStudent';

export default function CanonicalLessonPage() {
  const params = useParams<{ taskId: string }>();
  const { student, loading: studentLoading } = useStudent();
  const [task, setTask] = useState<LessonSuggestion | null>(null);
  const [lesson, setLesson] = useState<LessonResponse | null>(null);
  const [status, setStatus] = useState('Opening the approved family lesson…');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!student?.id || !params.taskId) return;
    let cancelled = false;

    void (async () => {
      try {
        const plan = await getLearningPlan(student.id, 12);
        const requestedId = decodeURIComponent(params.taskId);
        let selected = plan.suggestions.find((item) => item.id === requestedId);
        let requiredStandardCodes: string[] = selected?.standard_code ? [selected.standard_code] : [];
        if (!selected) {
          const roadmapDay = plan.roadmap.months.flatMap((month) => month.weeks).flatMap((week) => week.days).find((day) => day.lesson_id === requestedId);
          if (roadmapDay) {
            requiredStandardCodes = roadmapDay.standard_codes ?? [];
            selected = {
            id: roadmapDay.lesson_id, title: roadmapDay.title, track: roadmapDay.track,
            description: roadmapDay.description, emoji: roadmapDay.emoji,
            priority: 0.5, source: 'explore', canonical_ready: false,
            mission_kind: 'learning_mission', success_criteria: [],
            };
          }
        }
        if (!selected) throw new Error('That assignment is no longer in the current learning plan.');
        if (cancelled) return;
        setTask(selected);

        const blocks: LessonBlockResponse[] = [];
        for await (const event of buildLesson(lessonRequestFromSuggestion(selected, student.id, plan.placement.working_grade, requiredStandardCodes))) {
          if (cancelled) return;
          if (event.type === 'status') setStatus(event.message);
          if (event.type === 'block') blocks.push(event.block);
          if (event.type === 'error') throw new Error(event.message);
          if (event.type === 'done') {
            setLesson({
              lesson_id: event.lesson_id,
              title: event.title || selected.title,
              track: selected.track,
              blocks,
              has_research_missions: blocks.some((block) => block.block_type === 'RESEARCH_MISSION'),
              researcher_activated: event.researcher_activated ?? false,
              oas_standards: (event.oas_standards as LessonResponse['oas_standards']) ?? [],
              agent_name: event.agent_name ?? 'Adeline',
              xapi_statements: event.xapi_statements ?? [],
              credits_awarded: event.credits_awarded ?? [],
            });
            setStatus('');
          }
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Adeline could not open this family lesson.');
          setStatus('');
        }
      }
    })();

    return () => { cancelled = true; };
  }, [params.taskId, student?.id, student?.gradeLevel]);

  if (studentLoading) return <div className="p-10 text-center text-[#2F4731]/60">Opening the family lesson…</div>;
  if (!student) return <div className="p-10 text-center text-[#2F4731]/60">Your session has ended. Please sign in again.</div>;

  return (
    <div className="pb-16">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link href="/dashboard" className="text-sm font-bold text-[#2F4731]">← Back to today</Link>
      </div>

      {task && !lesson && (
        <header className="mb-5 rounded-[24px] border border-[#E7DAC3] bg-white/80 p-6">
          <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">One shared family lesson</p>
          <h1 className="mt-2 text-3xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{task.title}</h1>
          <p className="mt-2 text-sm leading-6 text-[#2F4731]/65">{task.description}</p>
        </header>
      )}

      {status && <p className="rounded-2xl border border-[#E7DAC3] bg-[#FDF6E9] p-5 text-sm italic text-[#2F4731]/70" role="status">{status}</p>}
      {error && <div className="rounded-2xl bg-red-50 p-5 text-sm text-red-700" role="alert"><p>{error}</p><Link href="/dashboard" className="mt-3 inline-flex font-bold underline">Return to today</Link></div>}
      {lesson && <FamilyCanonicalLesson lesson={lesson} studentId={student.id} gradeLevel={student.gradeLevel} />}
    </div>
  );
}
