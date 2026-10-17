import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TodayPage from '../page';
import CanonicalLessonPage from '../lesson/[taskId]/page';
import * as brain from '@/lib/brain-client';
import * as classroom from '@/lib/classroom-client';
vi.mock('@/lib/classroom-client', () => ({ getClassroom: vi.fn(), prepareClassroom: vi.fn(), listClassrooms: vi.fn() }));
vi.mock('@/components/classroom/ClassroomPlayer', () => ({ default: ({ state }: {state: {title:string}}) => <div>Saved classroom: {state.title}</div> }));

vi.mock('next/navigation', () => ({ useParams: () => ({ taskId: 'today-1' }) }));
vi.mock('@/lib/useStudent', () => ({
  useStudent: () => ({
    loading: false,
    student: { id: 'student-1', name: 'Test Learner', gradeLevel: '8' },
  }),
}));
vi.mock('@/components/lessons/FamilyCanonicalLesson', () => ({
  default: ({ lesson }: { lesson: { title: string } }) => <div>Saved lesson: {lesson.title}</div>,
}));
vi.mock('@/lib/brain-client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/brain-client')>('@/lib/brain-client');
  return {
    ...actual,
    peekLearningPlan: vi.fn(),
    getSavedTodayPlan: vi.fn(),
    getLearningPlan: vi.fn(),
    getRecentTranscript: vi.fn(),
    getSavedExperience: vi.fn(),
    buildExperience: vi.fn(),
  };
});

const plan = {
  plan_version: 10,
  student_id: 'student-1',
  suggestions: [{
    id: 'today-1', title: 'Creek evidence', track: 'CREATION_SCIENCE',
    description: 'Compare the records.', emoji: '🔬', priority: 1,
    source: 'zpd', mission_kind: 'learning_mission', success_criteria: [],
    sequence_policy: 'HARD', sequence_state: 'READY', prerequisite_readiness: 1,
    prerequisite_concept_ids: [], prerequisite_standard_ids: [], bridge_required: false,
    delivery_mode: 'FAMILY_INVESTIGATION', shared_investigation_id: 'family-1-week-1',
    individual_skill_targets: [], slot: 'science',
  }, {
    id: 'history-1', title: 'The Poison Squad: Who Was Allowed to Poison Your Food?', track: 'TRUTH_HISTORY',
    description: 'Volunteers ate food with hidden chemicals.', emoji: '📜', priority: 1,
    source: 'family', mission_kind: 'family_investigation', success_criteria: [],
    sequence_policy: 'OPEN', sequence_state: 'OPEN', prerequisite_readiness: 1,
    prerequisite_concept_ids: [], prerequisite_standard_ids: [], bridge_required: false,
    delivery_mode: 'FAMILY_INVESTIGATION', shared_investigation_id: 'family-1-history-0',
    individual_skill_targets: [], slot: 'history',
    driving_question: 'Who was allowed to put chemicals in food — and what evidence finally forced a federal law?',
  }, {
    id: 'math-1', title: 'Compare ratios', track: 'APPLIED_MATHEMATICS',
    description: 'Use ratios in a new example.', emoji: '📐', priority: 0.9,
    source: 'zpd', mission_kind: 'skill_mission', success_criteria: [],
    sequence_policy: 'HARD', sequence_state: 'READY', prerequisite_readiness: 1,
    prerequisite_concept_ids: [], prerequisite_standard_ids: [], bridge_required: false,
    delivery_mode: 'INDIVIDUAL_SKILL', individual_skill_targets: [],
  }],
  family_investigation: undefined,
  family_investigations: undefined,
  individual_skills: [],
  individual_lessons: [{
    id: 'family-1-week-1:scene',
    investigation_id: 'family-1-week-1',
    investigation_title: 'Creek evidence',
    slot: 'science',
    lesson_id: 'scene',
    index: 1,
    count: 2,
    title: 'The crime scene',
    assignment: 'Walk the boundary and sketch what you see.',
    track: 'CREATION_SCIENCE',
  }],
  family_context: { household_id: 'family-1', shared_with_siblings: false, sibling_count: 0 },
  placement: { declared_level: '8', working_grade: '8', placement_required: false, subject_levels: {} },
  roadmap: { months: [] },
} as unknown as brain.LearningPlanResponse;

const savedExperience = {
  id: 'experience-1', status: 'ready', title: 'Creek evidence',
  track: 'CREATION_SCIENCE', blocks: [], metadata: {}, error_message: null,
  canonical_slug: 'creek-evidence',
} as brain.SavedExperience;

describe('durable Today and experience reopening', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(classroom.listClassrooms).mockResolvedValue([{ item_id: 'fresh-1', title: 'Matter and measurement', phase: 'ready' }]);
    vi.mocked(brain.peekLearningPlan).mockReturnValue(plan);
    vi.mocked(brain.getSavedTodayPlan).mockResolvedValue(plan);
    vi.mocked(brain.getLearningPlan).mockResolvedValue(plan);
    vi.mocked(brain.getRecentTranscript).mockResolvedValue([]);
    vi.mocked(brain.getSavedExperience).mockResolvedValue(savedExperience);
    vi.mocked(classroom.getClassroom).mockResolvedValue({phase:'ready',title:'Creek evidence',classroom: {blueprint: {} as never, scenes: []}});
  });

  it('loads only fresh classrooms, never the retired lesson planner', async () => {
    render(<TodayPage />);
    expect(await screen.findByText('Matter and measurement')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Matter and measurement/ })).toHaveAttribute('href', '/dashboard/lesson/fresh-1');
    expect(screen.getByRole('link', { name: /Start exploring/ })).toBeInTheDocument();
    expect(screen.queryByText('Creek evidence')).not.toBeInTheDocument();
    expect(screen.queryByText('The crime scene')).not.toBeInTheDocument();
    expect(brain.peekLearningPlan).not.toHaveBeenCalled();
    expect(brain.getSavedTodayPlan).not.toHaveBeenCalled();
    expect(brain.getLearningPlan).not.toHaveBeenCalled();
  });

  it('reopens a ready experience with zero build/author requests', async () => {
    const first = render(<CanonicalLessonPage />);
    await screen.findByText('Saved classroom: Creek evidence');
    first.unmount();

    render(<CanonicalLessonPage />);
    await screen.findByText('Saved classroom: Creek evidence');

    await waitFor(() => expect(classroom.getClassroom).toHaveBeenCalledTimes(2));
    expect(brain.buildExperience).not.toHaveBeenCalled();
    expect(classroom.prepareClassroom).not.toHaveBeenCalled();
  });
});
