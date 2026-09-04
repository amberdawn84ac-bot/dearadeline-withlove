'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import FamilyCanonicalLesson from '@/components/lessons/FamilyCanonicalLesson';
import SpacePlayer from '@/components/spaces/SpacePlayer';
import {
  buildExperience, getLearningPlan, getSavedExperience, getSavedTodayPlan,
  lessonRequestFromSuggestion,
} from '@/lib/brain-client';
import type {
  LessonBlockResponse, LessonRequest, LessonResponse, LessonSuggestion, SavedExperience,
} from '@/lib/brain-client';
import { useStudent } from '@/lib/useStudent';

function lessonFromSaved(
  record: SavedExperience,
  selected: LessonSuggestion,
  request: LessonRequest,
): LessonResponse {
  const codes = record.metadata?.required_standard_codes ?? request.required_standard_codes ?? [];
  return {
    lesson_id: record.id,
    title: record.title || selected.title,
    track: record.track || selected.track,
    blocks: record.blocks,
    has_research_missions: record.blocks.some((block) => block.block_type === 'RESEARCH_MISSION'),
    researcher_activated: false,
    oas_standards: codes.map((code) => ({
      standard_id: code,
      text: 'Internal learning-plan target',
      grade: 0,
      lesson_hook: '',
      source_type: 'primary' as const,
    })),
    agent_name: 'Canonical Experience Author',
    xapi_statements: [],
    credits_awarded: [],
    metadata: { ...(record.metadata ?? {}), printable_request: request },
  };
}

function selectPlannedTask(plan: Awaited<ReturnType<typeof getLearningPlan>>, requestedId: string) {
  let selected = plan.suggestions.find((item) => item.id === requestedId);
  let requiredStandardCodes: string[] = selected?.standard_code ? [selected.standard_code] : [];
  if (!selected) {
    const roadmapDay = plan.roadmap.months
      .flatMap((month) => month.weeks)
      .flatMap((week) => week.days)
      .find((day) => day.lesson_id === requestedId);
    if (roadmapDay) {
      requiredStandardCodes = roadmapDay.standard_codes ?? [];
      selected = {
        id: roadmapDay.lesson_id, title: roadmapDay.title, track: roadmapDay.track,
        description: roadmapDay.description, emoji: roadmapDay.emoji,
        priority: 0.5, source: 'standard', canonical_ready: false,
        mission_kind: 'learning_mission', success_criteria: [],
        sequence_policy: roadmapDay.sequence_policy ?? 'SUPPORTED',
        sequence_state: roadmapDay.sequence_state ?? 'BRIDGE_REQUIRED',
        sequence_target_id: requiredStandardCodes[0],
        prerequisite_readiness: 0,
        prerequisite_concept_ids: [],
        prerequisite_standard_ids: roadmapDay.prerequisite_standard_ids ?? [],
        bridge_required: roadmapDay.bridge_required ?? true,
        delivery_mode: 'FAMILY_INVESTIGATION',
        shared_investigation_id: roadmapDay.lesson_id,
        individual_skill_targets: [],
      };
    }
  }
  return { selected, requiredStandardCodes };
}

export function CanonicalExperiencePage({ view = 'lesson' }: { view?: 'lesson' | 'space' }) {
  const params = useParams<{ taskId: string }>();
  const { student, loading: studentLoading } = useStudent();
  const [task, setTask] = useState<LessonSuggestion | null>(null);
  const [lesson, setLesson] = useState<LessonResponse | null>(null);
  const [status, setStatus] = useState('Opening the saved learning experience…');
  const [error, setError] = useState('');
  const [canRetry, setCanRetry] = useState(false);
  const [retryVersion, setRetryVersion] = useState(0);

  useEffect(() => {
    if (!student?.id || !params.taskId) return;
    let cancelled = false;

    const waitForPersisted = async (planItemId: string): Promise<SavedExperience | null> => {
      for (let attempt = 0; attempt < 120 && !cancelled; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        const record = await getSavedExperience(student.id, planItemId);
        if (!record || record.status !== 'generating') return record;
      }
      return null;
    };

    void (async () => {
      setError('');
      setCanRetry(false);
      setStatus('Opening the saved learning experience…');
      try {
        const plan = await getSavedTodayPlan(student.id) ?? await getLearningPlan(student.id, 12);
        const requestedId = decodeURIComponent(params.taskId);
        const { selected, requiredStandardCodes } = selectPlannedTask(plan, requestedId);
        if (!selected) throw new Error('That experience is no longer in the current learning plan.');
        if (selected.sequence_policy === 'HARD' && selected.sequence_state !== 'READY') {
          throw new Error('This skill is waiting on a prerequisite. Open the prerequisite mission from Today first.');
        }
        if (cancelled) return;
        setTask(selected);

        const experienceRequest = lessonRequestFromSuggestion(
          selected, student.id, plan.placement.working_grade, requiredStandardCodes,
        );
        let persisted = await getSavedExperience(student.id, selected.id);

        if (persisted?.status === 'ready') {
          setLesson(lessonFromSaved(persisted, selected, experienceRequest));
          setStatus('');
          return;
        }
        if (persisted?.status === 'generating') {
          setStatus('This experience is already being prepared. Waiting for the saved copy…');
          persisted = await waitForPersisted(selected.id);
          if (persisted?.status === 'ready') {
            setLesson(lessonFromSaved(persisted, selected, experienceRequest));
            setStatus('');
            return;
          }
        }
        if (persisted?.status === 'failed' && retryVersion === 0) {
          throw new Error(persisted.error_message || 'That experience did not finish. Your Today plan is safe.');
        }

        const blocks: LessonBlockResponse[] = [];
        let completed = false;
        for await (const event of buildExperience(experienceRequest)) {
          if (cancelled) return;
          if (event.type === 'status') setStatus(event.message);
          if (event.type === 'block') blocks.push(event.block);
          if (event.type === 'error') throw new Error(event.message);
          if (event.type === 'done') {
            completed = true;
            setLesson({
              lesson_id: event.lesson_id,
              title: event.title || selected.title,
              track: selected.track,
              blocks,
              has_research_missions: blocks.some((block) => block.block_type === 'RESEARCH_MISSION'),
              researcher_activated: event.researcher_activated ?? false,
              oas_standards: (event.oas_standards as LessonResponse['oas_standards']) ?? [],
              agent_name: event.agent_name ?? 'Canonical Experience Author',
              xapi_statements: event.xapi_statements ?? [],
              credits_awarded: event.credits_awarded ?? [],
              metadata: { ...(event.metadata ?? {}), printable_request: experienceRequest },
            });
            setStatus('');
          }
        }

        if (!completed && !cancelled) {
          const recovered = await getSavedExperience(student.id, selected.id);
          if (recovered?.status === 'ready') {
            setLesson(lessonFromSaved(recovered, selected, experienceRequest));
            setStatus('');
            return;
          }
          throw new Error(recovered?.error_message || 'The connection ended before the saved experience could be opened.');
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Adeline could not open this learning experience.');
          setCanRetry(true);
          setStatus('');
        }
      }
    })();

    return () => { cancelled = true; };
  }, [params.taskId, retryVersion, student?.gradeLevel, student?.id]);

  if (studentLoading) return <div className="p-10 text-center text-[#2F4731]/60">Opening the learning experience…</div>;
  if (!student) return <div className="p-10 text-center text-[#2F4731]/60">Your session has ended. Please sign in again.</div>;

  return (
    <div className="pb-16">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link href="/dashboard" className="text-sm font-bold text-[#2F4731]">← Back to today</Link>
      </div>

      {task && !lesson && (
        <header className="mb-5 rounded-[24px] border border-[#E7DAC3] bg-white/80 p-6">
          <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">{task.delivery_mode === 'INDIVIDUAL_SKILL' ? 'This learner’s skill path' : 'One shared family experience'}</p>
          <h1 className="mt-2 text-3xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{task.title}</h1>
          <p className="mt-2 text-sm leading-6 text-[#2F4731]/65">{task.description}</p>
        </header>
      )}

      {status && <p className="rounded-2xl border border-[#E7DAC3] bg-[#FDF6E9] p-5 text-sm italic text-[#2F4731]/70" role="status">{status}</p>}
      {error && <div className="rounded-2xl bg-red-50 p-5 text-sm text-red-700" role="alert"><p>{error}</p><div className="mt-3 flex flex-wrap gap-4">{canRetry && <button type="button" onClick={() => setRetryVersion((value) => value + 1)} className="font-bold underline">Retry safely</button>}<Link href="/dashboard" className="font-bold underline">Return to today</Link></div></div>}
      {lesson && task && (view === 'space'
        ? <SpacePlayer lesson={lesson} studentId={student.id} planItemId={task.id} />
        : <FamilyCanonicalLesson lesson={lesson} studentId={student.id} />)}
    </div>
  );
}

export default function CanonicalLessonPage() {
  return <CanonicalExperiencePage />;
}
