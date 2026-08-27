import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TodayPage from '../page';
import CanonicalLessonPage from '../lesson/[taskId]/page';
import * as brain from '@/lib/brain-client';

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
  plan_version: 8,
  student_id: 'student-1',
  suggestions: [{
    id: 'today-1', title: 'Creek evidence', track: 'CREATION_SCIENCE',
    description: 'Compare the records.', emoji: '🔬', priority: 1,
    source: 'zpd', mission_kind: 'learning_mission', success_criteria: [],
    sequence_policy: 'HARD', sequence_state: 'READY', prerequisite_readiness: 1,
    prerequisite_concept_ids: [], prerequisite_standard_ids: [], bridge_required: false,
    delivery_mode: 'FAMILY_INVESTIGATION', shared_investigation_id: 'family-1-week-1',
    individual_skill_targets: [],
  }, {
    id: 'math-1', title: 'Compare ratios', track: 'APPLIED_MATHEMATICS',
    description: 'Use ratios in a new example.', emoji: '📐', priority: 0.9,
    source: 'zpd', mission_kind: 'skill_mission', success_criteria: [],
    sequence_policy: 'HARD', sequence_state: 'READY', prerequisite_readiness: 1,
    prerequisite_concept_ids: [], prerequisite_standard_ids: [], bridge_required: false,
    delivery_mode: 'INDIVIDUAL_SKILL', individual_skill_targets: [],
  }],
  family_investigation: undefined,
  individual_skills: [],
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
    vi.mocked(brain.peekLearningPlan).mockReturnValue(plan);
    vi.mocked(brain.getSavedTodayPlan).mockResolvedValue(plan);
    vi.mocked(brain.getLearningPlan).mockResolvedValue(plan);
    vi.mocked(brain.getRecentTranscript).mockResolvedValue([]);
    vi.mocked(brain.getSavedExperience).mockResolvedValue(savedExperience);
  });

  it('reopens Today from the saved plan with zero planner-generation calls', async () => {
    const first = render(<TodayPage />);
    await screen.findByText('🔬 Creek evidence');
    first.unmount();

    render(<TodayPage />);
    await screen.findByText('🔬 Creek evidence');

    expect(brain.getSavedTodayPlan).toHaveBeenCalledTimes(2);
    expect(brain.getLearningPlan).not.toHaveBeenCalled();
  });

  it('keeps the learner skill path separate and openable', async () => {
    render(<TodayPage />);

    await screen.findByText('🔬 Creek evidence');
    expect(screen.getByRole('heading', { name: 'Math & Literacy' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Practice →' })).toHaveAttribute(
      'href', '/dashboard/lesson/math-1',
    );
  });

  it('reopens a ready experience with zero build/author requests', async () => {
    const first = render(<CanonicalLessonPage />);
    await screen.findByText('Saved lesson: Creek evidence');
    first.unmount();

    render(<CanonicalLessonPage />);
    await screen.findByText('Saved lesson: Creek evidence');

    await waitFor(() => expect(brain.getSavedExperience).toHaveBeenCalledTimes(2));
    expect(brain.buildExperience).not.toHaveBeenCalled();
  });
});
