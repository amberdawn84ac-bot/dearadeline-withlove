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
});
