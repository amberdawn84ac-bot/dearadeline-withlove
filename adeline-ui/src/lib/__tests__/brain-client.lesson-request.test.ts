import { describe, expect, it } from 'vitest';

import { lessonRequestFromSuggestion } from '@/lib/brain-client';

describe('lessonRequestFromSuggestion', () => {
  it('opens the stable canonical topic and carries the learner progression checklist', () => {
    const progression = [{
      suggestion_id: 'math-ratio',
      domain: 'math',
      title: 'Use ratios to compare a recipe',
      track: 'APPLIED_MATHEMATICS' as const,
      concept_id: 'ratio-concept',
      working_level: '7',
      sequence_state: 'READY' as const,
      integration_status: 'PENDING_FIT_CHECK' as const,
      integration_rule: 'Use only when the real work calls for it.',
      mastery_eligible: true,
    }];

    const request = lessonRequestFromSuggestion({
      id: 'family-1-v8',
      title: 'Operation Hooked',
      description: 'Open the evidence dossier.',
      track: 'JUSTICE_CHANGEMAKING',
      canonical_topic: 'The Opioid Crisis: Corporate Decisions, Regulation, and Unequal Consequences',
      sequence_policy: 'OPEN',
      sequence_state: 'OPEN',
      prerequisite_concept_ids: [],
      prerequisite_standard_ids: [],
      bridge_required: false,
      delivery_mode: 'FAMILY_INVESTIGATION',
      shared_investigation_id: 'family-1-v8',
      individual_skill_targets: progression,
      learner_progression_targets: progression,
      resource_packet: {
        topic: 'Use ratios to compare a recipe',
        track: 'APPLIED_MATHEMATICS',
        resources: [{ id: 'mathigon-polypad', resource_type: 'MANIPULATIVE' }],
        rules: ['Playing is practice, not mastery.'],
      },
    }, 'student-1', '7');

    expect(request.topic).toBe('The Opioid Crisis: Corporate Decisions, Regulation, and Unequal Consequences');
    expect(request.learner_progression_targets?.[0].concept_id).toBe('ratio-concept');
    expect(request.resource_packet?.resources?.[0].id).toBe('mathigon-polypad');
  });
});
