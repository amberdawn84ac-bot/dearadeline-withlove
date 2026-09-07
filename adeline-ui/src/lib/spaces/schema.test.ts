import { describe, expect, it } from 'vitest';
import { spaceEvaluationSchema, spaceTurnRequestSchema } from './schema';

describe('Space schemas', () => {
  it('accepts one server-paced learner turn', () => {
    expect(spaceTurnRequestSchema.parse({
      studentId: 'student-1', planItemId: 'unit-1', userMessage: 'The jar doubled.', expectedVersion: 0,
    }).userMessage).toBe('The jar doubled.');
  });

  it('rejects unsupported UI triggers', () => {
    expect(spaceEvaluationSchema.safeParse({
      adeline_message: 'Look closely.', evaluation: 'partial', recommended_action: 'stay',
      is_waiting_for_user: true, resource_triggers: ['award_credit'],
    }).success).toBe(false);
  });

  it('accepts a small set of tappable replies and defaults to none', () => {
    const base = {
      adeline_message: 'Are you ready to begin?', evaluation: 'not_answered',
      recommended_action: 'stay', is_waiting_for_user: true, resource_triggers: [],
    } as const;
    expect(spaceEvaluationSchema.parse(base).suggested_replies).toEqual([]);
    expect(spaceEvaluationSchema.parse({ ...base, suggested_replies: ['Yes', 'Not yet'] }).suggested_replies)
      .toEqual(['Yes', 'Not yet']);
  });
});
