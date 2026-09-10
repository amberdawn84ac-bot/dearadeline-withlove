'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import FamilyCanonicalLesson from '@/components/lessons/FamilyCanonicalLesson';
import SpaceConversation from '@/components/spaces/SpaceConversation';
import {
  buildExperience, getLearningPlan, getSavedExperience, getSavedTodayPlan,
  lessonRequestFromSuggestion,
} from '@/lib/brain-client';
import type {
  LessonBlockResponse, LessonRequest, LessonResponse, LessonSuggestion, SavedExperience,
} from '@/lib/brain-client';
import { useStudent } from '@/lib/useStudent';
import { selectPlannedTask } from './select-planned-task';

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

function taskFromSavedExperience(record: SavedExperience, requestedId: string): LessonSuggestion {
  return {
    id: requestedId,
    title: record.title || 'Learning Space',
    track: record.track || 'CREATION_SCIENCE',
    description: record.title || 'Learning Space',
    emoji: '✦',
    priority: 1,
    source: 'family',
    canonical_ready: true,
    mission_kind: 'family_investigation',
    success_criteria: [],
    sequence_policy: 'OPEN',
    sequence_state: 'OPEN',
    prerequisite_readiness: 1,
    prerequisite_concept_ids: [],
    prerequisite_standard_ids: [],
    bridge_required: false,
    delivery_mode: 'FAMILY_INVESTIGATION',
    shared_investigation_id: requestedId,
    individual_skill_targets: [],
  };
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

    const waitForPersisted = async (
      planItemId: string, maxAttempts = 120,
    ): Promise<SavedExperience | null> => {
      for (let attempt = 0; attempt < maxAttempts && !cancelled; attempt += 1) {
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
        const requestedId = decodeURIComponent(Array.isArray(params.taskId) ? params.taskId[0] : params.taskId);
        let { selected, requiredStandardCodes } = selectPlannedTask(plan, requestedId);
        if (!selected && view === 'space') {
          const alreadySaved = await getSavedExperience(student.id, requestedId);
          if (alreadySaved?.status === 'ready') {
            selected = taskFromSavedExperience(alreadySaved, requestedId);
            requiredStandardCodes = alreadySaved.metadata?.required_standard_codes ?? [];
            if (cancelled) return;
            const experienceRequest = lessonRequestFromSuggestion(
              selected, student.id, plan.placement.working_grade, requiredStandardCodes,
            );
            setTask(selected);
            setLesson(lessonFromSaved(alreadySaved, selected, experienceRequest));
            setStatus('');
            return;
          }
        }
        if (!selected) throw new Error('That experience is no longer in the current learning plan.');
        if (
          selected.delivery_mode !== 'FAMILY_INVESTIGATION'
          && selected.sequence_policy === 'HARD'
          && selected.sequence_state !== 'READY'
        ) {
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
        // Once authoring has failed repeatedly, the backend stops retrying and
        // leaves the row terminal. Don't launch another build that will just
        // return the same escalation error — show it and stop.
        if (persisted?.status === 'failed' && (persisted.failure_count ?? 0) >= 3) {
          setError('Adeline could not build this investigation after several tries. It has been flagged for review — open another investigation from Today for now.');
          setCanRetry(false);
          setStatus('');
          return;
        }
        // The backend atomically reclaims failed records. Reopening a Space is
        // itself a safe retry; do not strand the learner behind a stale 503.
        if (persisted?.status === 'failed') {
          setStatus('The earlier draft did not pass Adeline’s quality checks. Rebuilding it safely…');
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
          // The streaming connection can be cut by an infrastructure proxy
          // limit well before authoring finishes server-side (it keeps
          // running as a detached backend task regardless). Don't treat a
          // dropped connection as a failure -- keep polling the saved copy
          // the same way we do for an experience that was already
          // generating when this page opened.
          let recovered = await getSavedExperience(student.id, selected.id);
          if (recovered?.status === 'generating') {
            setStatus('Still preparing this experience. This can take a few minutes for a thorough unit…');
            recovered = await waitForPersisted(selected.id, 240);
          }
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
  }, [params.taskId, retryVersion, student?.gradeLevel, student?.id, view]);

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
          <h1 className="mt-2 text-3xl text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{shortTitle(task.title)}</h1>
          {shortCopy(task.driving_question || task.description) && (
            <p className="mt-2 text-sm leading-6 text-[#2F4731]/65">{shortCopy(task.driving_question || task.description)}</p>
          )}
        </header>
      )}

      {status && <p className="rounded-2xl border border-[#E7DAC3] bg-[#FDF6E9] p-5 text-sm italic text-[#2F4731]/70" role="status">{status}</p>}
      {error && <div className="rounded-2xl bg-red-50 p-5 text-sm text-red-700" role="alert"><p>{error}</p><div className="mt-3 flex flex-wrap gap-4">{canRetry && <button type="button" onClick={() => setRetryVersion((value) => value + 1)} className="font-bold underline">Retry safely</button>}<Link href="/dashboard" className="font-bold underline">Return to today</Link></div></div>}
      {lesson && task && (view === 'space'
        ? (
          <div className="space-y-6">
            <SpaceHeader task={task} lesson={lesson} />
            <SpaceConversation studentId={student.id} gradeLevel={student.gradeLevel ?? '8'} planItemId={task.id} />
          </div>
        )
        : <FamilyCanonicalLesson lesson={lesson} studentId={student.id} />)}
    </div>
  );
}

function shortTitle(value: string | undefined) {
  const text = (value || '').trim();
  if (!text) return 'Family investigation';
  if (/^open harvey/i.test(text) || (text.length > 90 && text.includes('. '))) return 'Family investigation';
  return text;
}

function shortCopy(value: string | undefined) {
  const text = (value || '').trim();
  if (!text || text.length > 220 || /^open harvey/i.test(text)) return '';
  return text;
}

function SpaceHeader({ task, lesson }: { task: LessonSuggestion; lesson: LessonResponse }) {
  const design = (lesson.metadata?.experience_design || {}) as { central_question?: string };
  const question = shortCopy(
    task.driving_question || design.central_question || '',
  );
  const hook = shortCopy(task.description);
  const slotLabel = task.slot === 'history'
    ? 'History together'
    : task.slot === 'science'
      ? 'Science together'
      : 'Family investigation';
  return (
    <header className="overflow-hidden rounded-[24px] border border-[#E7DAC3] bg-white/80 p-6 md:p-8">
      <div className="grid gap-6 md:grid-cols-[1.15fr_.85fr]">
        <div>
          <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">{slotLabel}</p>
          <h1 className="mt-2 text-3xl text-[#2F4731] md:text-4xl" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
            {shortTitle(lesson.title || task.title)}
          </h1>
          {hook && hook !== question && (
            <p className="mt-3 text-sm leading-6 text-[#2F4731]/70">{hook}</p>
          )}
        </div>
        {question && (
          <div className="self-center border-l-4 border-[#BD6809] pl-5">
            <p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The question</p>
            <p className="mt-2 font-semibold leading-7 text-[#2F4731]">{question}</p>
          </div>
        )}
      </div>
    </header>
  );
}

export default function CanonicalLessonPage() {
  return <CanonicalExperiencePage />;
}
