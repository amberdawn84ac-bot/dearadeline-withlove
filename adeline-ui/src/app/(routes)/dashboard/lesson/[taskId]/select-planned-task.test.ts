import { describe, expect, it } from 'vitest';
import { selectPlannedTask } from './select-planned-task';
import type { LessonSuggestion } from '@/lib/brain-client';

function family(id: string, title: string): LessonSuggestion {
  return {
    id,
    title,
    track: 'CREATION_SCIENCE',
    description: title,
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
    shared_investigation_id: id,
    individual_skill_targets: [],
  };
}

describe('selectPlannedTask', () => {
  it('finds a family investigation that is on Today but missing from suggestions', () => {
    const science = family('family-cd2add4145f7-science-0', 'Sourdough');
    const { selected } = selectPlannedTask({
      suggestions: [],
      family_investigations: [science],
    }, 'family-cd2add4145f7-science-0');

    expect(selected?.id).toBe(science.id);
    expect(selected?.title).toBe('Sourdough');
  });

  it('finds the back-compat singular family_investigation field', () => {
    const history = family('family-cd2add4145f7-history-0', 'Land Run');
    const { selected } = selectPlannedTask({
      suggestions: [],
      family_investigation: history,
    }, 'family-cd2add4145f7-history-0');

    expect(selected?.title).toBe('Land Run');
  });

  it('still finds ids that only live on suggestions', () => {
    const science = family('family-1-science-0', 'Yeast');
    const { selected } = selectPlannedTask({
      suggestions: [science],
    }, 'family-1-science-0');

    expect(selected?.id).toBe(science.id);
  });

  it('opens a sequenced skill that did not fit the unit as its own lesson', () => {
    const { selected } = selectPlannedTask({
      suggestions: [],
      individual_lessons: [{
        id: 'gap:ratios',
        investigation_id: 'ratios',
        investigation_title: 'Stays in order',
        lesson_id: 'gap',
        index: 1,
        count: 1,
        title: 'Compare ratios',
        assignment: "Today's math mini lesson, level 8.",
        track: 'APPLIED_MATHEMATICS',
        kind: 'gap',
      }],
    }, 'ratios');

    expect(selected?.title).toBe('Compare ratios');
    expect(selected?.delivery_mode).toBe('INDIVIDUAL_SKILL');
  });

  it('does not throw when roadmap months are missing', () => {
    const { selected } = selectPlannedTask({
      suggestions: [],
      roadmap: null,
    }, 'missing-id');

    expect(selected).toBeUndefined();
  });
});
